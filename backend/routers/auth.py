import base64
import datetime
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
import itsdangerous
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import create_access_token, get_current_user
from backend.config import get_settings
from backend.db import get_db
from backend.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_oauth_base_url(issuer: str) -> str:
    """Extract OAuth2 endpoint base URL from Authentik issuer.
    
    Authentik's issuer includes the app slug:
      https://auth.example.com/application/o/my-app/
    
    But OAuth2 endpoints are shared (no app slug):
      https://auth.example.com/application/o/
    
    This removes the last path segment to get the base URL.
    """
    return issuer.rstrip("/").rsplit("/", 1)[0] + "/"


def _require_sso() -> None:
    """Raise 503 with a clear message when SSO env vars are not configured."""
    if not get_settings().sso_enabled:
        raise HTTPException(
            status_code=503,
            detail="SSO is not configured on this server. Set AUTHENTIK_ISSUER, AUTHENTIK_CLIENT_ID, and AUTHENTIK_CLIENT_SECRET env vars to enable it.",
        )


def _get_signer() -> itsdangerous.URLSafeTimedSerializer:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("OAuth signing is unavailable when SSO is disabled")
    return itsdangerous.URLSafeTimedSerializer(settings.jwt_secret_key, salt="oauth-state")


@router.get("/config")
async def config():
    """Return whether SSO is available. Consumed by the frontend to show/hide the Sign in button."""
    return {"sso_enabled": get_settings().sso_enabled}


@router.get("/login")
async def login():
    _require_sso()
    settings = get_settings()

    # Generate PKCE challenge
    verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    state = secrets.token_urlsafe(32)

    # Sign state + verifier in a short-lived cookie (5 min TTL enforced by signer)
    signer = _get_signer()
    cookie_val = signer.dumps({"state": state, "verifier": verifier})

    params = urlencode(
        {
            "response_type": "code",
            "client_id": settings.authentik_client_id,
            "redirect_uri": f"{settings.app_base_url}/auth/callback",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )

    oauth_base = _get_oauth_base_url(settings.authentik_issuer)
    redirect = RedirectResponse(
        url=f"{oauth_base}authorize/?{params}",
        status_code=302,
    )
    redirect.set_cookie(
        "oauth_state",
        cookie_val,
        max_age=300,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return redirect


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _require_sso()
    settings = get_settings()

    # Verify OAuth state cookie
    oauth_state_cookie = request.cookies.get("oauth_state")
    if not oauth_state_cookie:
        raise HTTPException(status_code=400, detail="Missing OAuth state cookie")

    signer = _get_signer()
    try:
        state_data = signer.loads(oauth_state_cookie, max_age=300)
    except itsdangerous.SignatureExpired:
        raise HTTPException(status_code=400, detail="OAuth state expired, please try again")
    except itsdangerous.BadData:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    if state_data["state"] != state:
        raise HTTPException(status_code=400, detail="State mismatch")

    verifier = state_data["verifier"]

    oauth_base = _get_oauth_base_url(settings.authentik_issuer)

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            f"{oauth_base}token/",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.app_base_url}/auth/callback",
                "client_id": settings.authentik_client_id,
                "client_secret": settings.authentik_client_secret,
                "code_verifier": verifier,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Token exchange failed")
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            f"{oauth_base}userinfo/",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch user info")
        userinfo = userinfo_resp.json()

    sub: str = userinfo["sub"]

    # Upsert user record
    result = await db.execute(select(User).where(User.id == sub))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=sub,
            email=userinfo.get("email"),
            name=userinfo.get("name") or userinfo.get("preferred_username"),
        )
        db.add(user)
    else:
        user.email = userinfo.get("email")
        user.name = userinfo.get("name") or userinfo.get("preferred_username")
        user.updated_at = datetime.datetime.now(datetime.UTC)

    await db.commit()

    # Issue session JWT and redirect to app
    token = create_access_token(sub)
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.set_cookie(
        "session_token",
        token,
        max_age=60 * 60 * 24 * 30,  # 30 days
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    redirect.delete_cookie("oauth_state")
    return redirect


@router.get("/logout")
async def logout():
    settings = get_settings()
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_token", httponly=True, samesite="lax", secure=settings.cookie_secure)
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user.id, "email": user.email, "name": user.name}

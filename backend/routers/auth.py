import base64
import datetime
import hashlib
import secrets
from urllib.parse import urlparse

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


async def _get_oidc_metadata(client: httpx.AsyncClient, issuer: str) -> dict:
    response = await client.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="OIDC discovery failed")
    try:
        metadata = response.json()
    except ValueError as error:
        raise HTTPException(status_code=502, detail="OIDC discovery returned invalid JSON") from error

    if metadata.get("issuer", "").rstrip("/") != issuer.rstrip("/"):
        raise HTTPException(status_code=502, detail="OIDC discovery issuer mismatch")
    issuer_scheme = urlparse(issuer).scheme
    for field in ("authorization_endpoint", "token_endpoint", "userinfo_endpoint"):
        endpoint = urlparse(metadata.get(field, ""))
        if (
            endpoint.scheme not in {"http", "https"}
            or not endpoint.netloc
            or (issuer_scheme == "https" and endpoint.scheme != "https")
        ):
            raise HTTPException(status_code=502, detail=f"OIDC discovery is missing a valid {field}")
    return metadata


def _get_token_auth(metadata: dict, client_id: str, client_secret: str) -> tuple[tuple[str, str] | None, dict]:
    methods = metadata.get("token_endpoint_auth_methods_supported", ["client_secret_basic"])
    if "client_secret_basic" in methods:
        return (client_id, client_secret), {}
    if "client_secret_post" in methods:
        return None, {"client_id": client_id, "client_secret": client_secret}
    raise HTTPException(status_code=502, detail="OIDC provider does not support a compatible client authentication method")


def _require_sso() -> None:
    """Raise 503 with a clear message when SSO env vars are not configured."""
    if not get_settings().sso_enabled:
        raise HTTPException(
            status_code=503,
            detail="SSO is not configured on this server. Set OIDC_ISSUER, OIDC_CLIENT_ID, and OIDC_CLIENT_SECRET to enable it.",
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

    async with httpx.AsyncClient() as client:
        metadata = await _get_oidc_metadata(client, settings.oidc_issuer)

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

    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": f"{settings.app_base_url}/auth/callback",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    redirect = RedirectResponse(
        url=str(httpx.URL(metadata["authorization_endpoint"]).copy_merge_params(params)),
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

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        metadata = await _get_oidc_metadata(client, settings.oidc_issuer)
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{settings.app_base_url}/auth/callback",
            "code_verifier": verifier,
        }
        token_auth, token_credentials = _get_token_auth(
            metadata,
            settings.oidc_client_id,
            settings.oidc_client_secret,
        )
        token_data.update(token_credentials)

        token_resp = await client.post(metadata["token_endpoint"], data=token_data, auth=token_auth)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Token exchange failed")
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            metadata["userinfo_endpoint"],
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

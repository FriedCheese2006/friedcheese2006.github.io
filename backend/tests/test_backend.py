import asyncio
import datetime
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

TEST_DATA_DIR = tempfile.mkdtemp(prefix="icarus-calc-tests-")
os.environ["DATABASE_PATH"] = os.path.join(TEST_DATA_DIR, "icarus.db")
os.environ.pop("OIDC_ISSUER", None)
os.environ.pop("OIDC_CLIENT_ID", None)
os.environ.pop("OIDC_CLIENT_SECRET", None)

import itsdangerous
import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.auth import ALGORITHM, create_access_token, require_user
from backend.config import Settings, get_settings
from backend.db import AsyncSessionLocal, engine
from backend.main import app
from backend.models import User
from backend.routers.auth import _get_oidc_metadata, _get_token_auth

OIDC_ISSUER = "https://identity.example.com/tenant"
OIDC_METADATA = {
    "issuer": OIDC_ISSUER,
    "authorization_endpoint": "https://login.example.net/oauth2/authorize?audience=calculator",
    "token_endpoint": "https://login.example.net/oauth2/token",
    "userinfo_endpoint": "https://api.example.net/oidc/userinfo",
    "token_endpoint_auth_methods_supported": ["client_secret_basic"],
}


async def authenticated_user() -> User:
    return User(id="test-user", email="test@example.com", name="Test User")


async def create_user(user_id: str) -> None:
    async with AsyncSessionLocal() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.com", name="Session User"))
        await session.commit()


class BackendTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    def test_anonymous_mode_disables_sso_and_protects_state(self) -> None:
        with TestClient(app) as client:
            self.assertEqual(client.get("/auth/config").json(), {"sso_enabled": False})
            self.assertEqual(client.get("/api/state").status_code, 401)

    def test_static_files_cannot_escape_dist(self) -> None:
        with TestClient(app) as client:
            response = client.get("/%2e%2e/backend/config.py")
            self.assertEqual(response.status_code, 404)

            response = client.get("/index.html")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_sso_configuration_requires_complete_provider_and_strong_key(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(oidc_issuer=OIDC_ISSUER)

        with self.assertRaises(ValidationError):
            Settings(
                oidc_issuer=OIDC_ISSUER,
                oidc_client_id="client-id",
                oidc_client_secret="client-secret",
                jwt_secret_key="paste-the-generated-value-here",
            )

    def test_oidc_token_auth_supports_basic_and_post(self) -> None:
        self.assertEqual(
            _get_token_auth({}, "client-id", "client-secret"),
            (("client-id", "client-secret"), {}),
        )
        self.assertEqual(
            _get_token_auth(
                {"token_endpoint_auth_methods_supported": ["client_secret_post"]},
                "client-id",
                "client-secret",
            ),
            (None, {"client_id": "client-id", "client_secret": "client-secret"}),
        )

    def test_oidc_discovery_rejects_https_downgrade(self) -> None:
        oauth_client = AsyncMock()
        oauth_client.get.return_value = Mock(
            status_code=200,
            json=lambda: {**OIDC_METADATA, "token_endpoint": "http://login.example.net/oauth2/token"},
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(_get_oidc_metadata(oauth_client, OIDC_ISSUER))

        self.assertEqual(context.exception.status_code, 502)

    def test_login_uses_pkce_and_callback_rejects_missing_state_cookie(self) -> None:
        environment = {
            "OIDC_ISSUER": OIDC_ISSUER,
            "OIDC_CLIENT_ID": "client-id",
            "OIDC_CLIENT_SECRET": "client-secret",
            "JWT_SECRET_KEY": "a" * 32,
            "APP_BASE_URL": "https://icarus.example.com",
        }
        oauth_client = AsyncMock()
        oauth_client.__aenter__.return_value = oauth_client
        oauth_client.__aexit__.return_value = None
        oauth_client.get.return_value = Mock(status_code=200, json=lambda: OIDC_METADATA)

        with patch.dict(os.environ, environment, clear=False), patch(
            "backend.routers.auth.httpx.AsyncClient", return_value=oauth_client
        ):
            get_settings.cache_clear()
            with TestClient(app, base_url="https://icarus.example.com") as client:
                response = client.get("/auth/login", follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["location"].startswith(OIDC_METADATA["authorization_endpoint"]))
                self.assertIn("audience=calculator", response.headers["location"])
                self.assertIn("code_challenge=", response.headers["location"])
                self.assertIn("oauth_state=", response.headers["set-cookie"])
                self.assertIn("HttpOnly", response.headers["set-cookie"])
                self.assertIn("Secure", response.headers["set-cookie"])

                client.cookies.clear()
                response = client.get("/auth/callback?code=code&state=state")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["detail"], "Missing OAuth state cookie")

            oauth_client.get.assert_awaited_once_with(f"{OIDC_ISSUER}/.well-known/openid-configuration")

    def test_session_token_authenticates_me_and_expired_token_is_rejected(self) -> None:
        user_id = "session-user"
        secret = "b" * 32
        asyncio.run(create_user(user_id))

        with patch.dict(os.environ, {"JWT_SECRET_KEY": secret}, clear=False):
            get_settings.cache_clear()
            valid_token = create_access_token(user_id)
            expired_token = jwt.encode(
                {"sub": user_id, "exp": datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=1)},
                secret,
                algorithm=ALGORITHM,
            )
            with TestClient(app) as client:
                client.cookies.set("session_token", valid_token)
                response = client.get("/auth/me")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["id"], user_id)

                client.cookies.set("session_token", expired_token)
                response = client.get("/auth/me")
                self.assertEqual(response.status_code, 401)

    def test_callback_creates_user_and_authenticated_session(self) -> None:
        secret = "c" * 32
        environment = {
            "OIDC_ISSUER": OIDC_ISSUER,
            "OIDC_CLIENT_ID": "client-id",
            "OIDC_CLIENT_SECRET": "client-secret",
            "JWT_SECRET_KEY": secret,
            "APP_BASE_URL": "https://icarus.example.com",
        }
        oauth_client = AsyncMock()
        oauth_client.__aenter__.return_value = oauth_client
        oauth_client.__aexit__.return_value = None
        oauth_client.post.return_value = Mock(status_code=200, json=lambda: {"access_token": "provider-token"})
        oauth_client.get.side_effect = [
            Mock(status_code=200, json=lambda: OIDC_METADATA),
            Mock(status_code=200, json=lambda: {"sub": "oauth-user", "email": "oauth@example.com", "name": "OAuth User"}),
        ]

        with patch.dict(os.environ, environment, clear=False), patch(
            "backend.routers.auth.httpx.AsyncClient", return_value=oauth_client
        ):
            get_settings.cache_clear()
            oauth_cookie = itsdangerous.URLSafeTimedSerializer(secret, salt="oauth-state").dumps(
                {"state": "expected-state", "verifier": "pkce-verifier"}
            )
            with TestClient(app, base_url="https://icarus.example.com") as client:
                client.cookies.set("oauth_state", oauth_cookie)
                response = client.get(
                    "/auth/callback?code=authorization-code&state=expected-state",
                    follow_redirects=False,
                )
                self.assertEqual(response.status_code, 302)
                self.assertIn("session_token=", response.headers["set-cookie"])

                response = client.get("/auth/me")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json(),
                    {"id": "oauth-user", "email": "oauth@example.com", "name": "OAuth User"},
                )

        oauth_client.post.assert_awaited_once_with(
            OIDC_METADATA["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": "authorization-code",
                "redirect_uri": "https://icarus.example.com/auth/callback",
                "code_verifier": "pkce-verifier",
            },
            auth=("client-id", "client-secret"),
        )
        self.assertEqual(oauth_client.get.await_count, 2)

    def test_logout_expires_secure_session_cookie(self) -> None:
        with patch.dict(os.environ, {"APP_BASE_URL": "https://icarus.example.com"}, clear=False):
            get_settings.cache_clear()
            with TestClient(app, base_url="https://icarus.example.com") as client:
                response = client.get("/auth/logout", follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                self.assertIn("session_token=", response.headers["set-cookie"])
                self.assertIn("Max-Age=0", response.headers["set-cookie"])
                self.assertIn("Secure", response.headers["set-cookie"])

    def test_authenticated_state_persists(self) -> None:
        app.dependency_overrides[require_user] = authenticated_user
        payload = {
            "tabs": {"version": 1, "activeMode": "items", "workspaces": {}},
            "settings": {"splitRawComponents": True},
        }

        with TestClient(app) as client:
            response = client.put("/api/state", json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"ok": True})

        with TestClient(app) as client:
            response = client.get("/api/state")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), payload)


def tearDownModule() -> None:
    asyncio.run(engine.dispose())
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

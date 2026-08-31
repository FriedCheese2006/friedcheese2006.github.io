from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_path: Path = Path("data/icarus.db")

    # SSO — all optional.  When any of these are unset, SSO is disabled and
    # the app runs in anonymous-only mode (localStorage persistence only).
    # authentik_issuer should be the OpenID issuer URL, e.g.:
    # https://auth.example.com/application/o/my-app/
    authentik_issuer: Optional[str] = None
    authentik_client_id: Optional[str] = None
    authentik_client_secret: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    app_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_sso_configuration(self):
        provider_values = (
            self.authentik_issuer,
            self.authentik_client_id,
            self.authentik_client_secret,
        )
        if any(provider_values) and not all(provider_values):
            raise ValueError("Authentik configuration must include issuer, client ID, and client secret")
        if all(provider_values):
            issuer = urlparse(self.authentik_issuer)
            if issuer.scheme not in {"http", "https"} or not issuer.netloc:
                raise ValueError("AUTHENTIK_ISSUER must be an absolute HTTP(S) URL")
            if (
                not self.jwt_secret_key
                or len(self.jwt_secret_key) < 32
                or self.jwt_secret_key.startswith(("replace-", "paste-"))
            ):
                raise ValueError("JWT_SECRET_KEY must contain at least 32 non-placeholder characters when SSO is enabled")
        return self

    @property
    def sso_enabled(self) -> bool:
        """True only when every required Authentik setting is present."""
        return bool(
            self.authentik_issuer
            and self.authentik_client_id
            and self.authentik_client_secret
            and self.jwt_secret_key
        )

    @property
    def cookie_secure(self) -> bool:
        return self.app_base_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()

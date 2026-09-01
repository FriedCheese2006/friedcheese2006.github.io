from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_path: Path = Path("data/prospector.db")

    # SSO is enabled when the complete OIDC client configuration is present.
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    app_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_sso_configuration(self):
        provider_values = (
            self.oidc_issuer,
            self.oidc_client_id,
            self.oidc_client_secret,
        )
        if any(provider_values) and not all(provider_values):
            raise ValueError("OIDC configuration must include issuer, client ID, and client secret")
        if all(provider_values):
            issuer = urlparse(self.oidc_issuer)
            if issuer.scheme not in {"http", "https"} or not issuer.netloc or issuer.query or issuer.fragment:
                raise ValueError("OIDC_ISSUER must be an absolute HTTP(S) URL without a query or fragment")
            if (
                not self.jwt_secret_key
                or len(self.jwt_secret_key) < 32
                or self.jwt_secret_key.startswith(("replace-", "paste-"))
            ):
                raise ValueError("JWT_SECRET_KEY must contain at least 32 non-placeholder characters when SSO is enabled")
        return self

    @property
    def sso_enabled(self) -> bool:
        """True only when every required OIDC setting is present."""
        return bool(
            self.oidc_issuer
            and self.oidc_client_id
            and self.oidc_client_secret
            and self.jwt_secret_key
        )

    @property
    def cookie_secure(self) -> bool:
        return self.app_base_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()

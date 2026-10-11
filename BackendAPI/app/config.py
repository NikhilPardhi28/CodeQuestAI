from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CODEQUEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://codequest:change-me@localhost:5432/codequest"
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_jwks_url: str | None = None

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        configured = (self.auth_issuer, self.auth_audience, self.auth_jwks_url)
        if any(configured) and not all(configured):
            raise ValueError(
                "CODEQUEST_AUTH_ISSUER, CODEQUEST_AUTH_AUDIENCE, and "
                "CODEQUEST_AUTH_JWKS_URL must be configured together"
            )
        return self

    @property
    def authentication_configured(self) -> bool:
        return bool(self.auth_issuer and self.auth_audience and self.auth_jwks_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()

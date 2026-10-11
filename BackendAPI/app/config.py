from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
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
    evaluation_worker_url: str | None = None
    evaluation_worker_token: SecretStr | None = None
    evaluation_queue_limit: int = 500
    submission_source_retention_days: int = 30

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        configured = (self.auth_issuer, self.auth_audience, self.auth_jwks_url)
        if any(configured) and not all(configured):
            raise ValueError(
                "CODEQUEST_AUTH_ISSUER, CODEQUEST_AUTH_AUDIENCE, and "
                "CODEQUEST_AUTH_JWKS_URL must be configured together"
            )
        if all(configured):
            if not self.auth_audience or self.auth_audience != self.auth_audience.strip():
                raise ValueError("CODEQUEST_AUTH_AUDIENCE must be non-empty and trimmed")
            for name, value in (
                ("CODEQUEST_AUTH_ISSUER", self.auth_issuer),
                ("CODEQUEST_AUTH_JWKS_URL", self.auth_jwks_url),
            ):
                parsed = urlsplit(value or "")
                local_http = self.env.lower() in {
                    "local",
                    "development",
                    "test",
                } and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                if (
                    not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.fragment
                    or parsed.scheme != "https"
                    and not (parsed.scheme == "http" and local_http)
                ):
                    raise ValueError(
                        f"{name} must use HTTPS "
                        "(HTTP is allowed only for loopback in local/test environments)"
                    )
                if value != value.strip():
                    raise ValueError(f"{name} must be trimmed")
                if name == "CODEQUEST_AUTH_ISSUER" and parsed.query:
                    raise ValueError("CODEQUEST_AUTH_ISSUER cannot include a query")
        if (self.evaluation_worker_url is None) != (self.evaluation_worker_token is None):
            raise ValueError(
                "CODEQUEST_EVALUATION_WORKER_URL and CODEQUEST_EVALUATION_WORKER_TOKEN "
                "must be configured together"
            )
        if self.evaluation_worker_url is not None:
            parsed_worker_url = urlsplit(self.evaluation_worker_url)
            if parsed_worker_url.scheme not in {"http", "https"} or not parsed_worker_url.hostname:
                raise ValueError("CODEQUEST_EVALUATION_WORKER_URL must be an absolute HTTP(S) URL")
            if (
                parsed_worker_url.username
                or parsed_worker_url.password
                or parsed_worker_url.fragment
            ):
                raise ValueError(
                    "CODEQUEST_EVALUATION_WORKER_URL cannot contain credentials or fragments"
                )
            if parsed_worker_url.scheme == "http" and parsed_worker_url.hostname not in {
                "127.0.0.1",
                "localhost",
                "::1",
            }:
                raise ValueError("Non-local evaluation worker URLs must use HTTPS")
            if (
                not self.evaluation_worker_token
                or len(self.evaluation_worker_token.get_secret_value()) < 32
            ):
                raise ValueError(
                    "CODEQUEST_EVALUATION_WORKER_TOKEN must contain at least 32 characters"
                )
        if self.evaluation_queue_limit < 1 or self.evaluation_queue_limit > 5000:
            raise ValueError("CODEQUEST_EVALUATION_QUEUE_LIMIT must be between 1 and 5000")
        if (
            self.submission_source_retention_days < 1
            or self.submission_source_retention_days > 3650
        ):
            raise ValueError(
                "CODEQUEST_SUBMISSION_SOURCE_RETENTION_DAYS must be between 1 and 3650"
            )
        return self

    @property
    def authentication_configured(self) -> bool:
        return bool(self.auth_issuer and self.auth_audience and self.auth_jwks_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()

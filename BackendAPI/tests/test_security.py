from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from BackendAPI.app import security
from BackendAPI.app.config import Settings
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError


@pytest.fixture
def signing_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _claims(settings: Settings, **overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "sub": "oidc-subject-1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return claims


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
    )


def test_oidc_bearer_token_requires_signature_issuer_audience_and_lifetime(
    monkeypatch, signing_pair
) -> None:
    settings = _settings()
    private_key, public_key = signing_pair
    monkeypatch.setattr(
        security,
        "get_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key)
        ),
    )
    token = jwt.encode(_claims(settings), private_key, algorithm="RS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert security.get_current_subject(credentials, settings) == "oidc-subject-1"

    wrong_audience = jwt.encode(_claims(settings, aud="wrong-api"), private_key, algorithm="RS256")
    with pytest.raises(HTTPException) as error:
        security.get_current_subject(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=wrong_audience), settings
        )
    assert error.value.status_code == 401

    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    invalid_signature = jwt.encode(_claims(settings), other_private, algorithm="RS256")
    with pytest.raises(HTTPException) as error:
        security.get_current_subject(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=invalid_signature), settings
        )
    assert error.value.status_code == 401


def test_protected_route_fails_closed_when_auth_is_missing_or_unconfigured() -> None:
    with pytest.raises(HTTPException) as unconfigured:
        security.get_current_subject(None, Settings(_env_file=None))
    assert unconfigured.value.status_code == 503

    with pytest.raises(HTTPException) as missing:
        security.get_current_subject(None, _settings())
    assert missing.value.status_code == 401


def test_oidc_settings_require_complete_secure_endpoints() -> None:
    with pytest.raises(ValidationError, match="must be configured together"):
        Settings(
            _env_file=None,
            auth_issuer="https://issuer.test/",
            auth_audience="codequest-api",
        )

    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            _env_file=None,
            auth_issuer="http://identity.example/",
            auth_audience="codequest-api",
            auth_jwks_url="https://identity.example/jwks",
        )

    with pytest.raises(ValidationError, match="must be non-empty and trimmed"):
        Settings(
            _env_file=None,
            auth_issuer="https://identity.example/",
            auth_audience=" ",
            auth_jwks_url="https://identity.example/jwks",
        )

    with pytest.raises(ValidationError, match="cannot include a query"):
        Settings(
            _env_file=None,
            auth_issuer="https://identity.example/?tenant=unsafe",
            auth_audience="codequest-api",
            auth_jwks_url="https://identity.example/jwks",
        )

    with pytest.raises(ValidationError, match="must be trimmed"):
        Settings(
            _env_file=None,
            auth_issuer="https://identity.example/",
            auth_audience="codequest-api",
            auth_jwks_url=" https://identity.example/jwks",
        )

    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            _env_file=None,
            env="production",
            auth_issuer="http://127.0.0.1:8080/issuer",
            auth_audience="codequest-api",
            auth_jwks_url="http://127.0.0.1:8080/issuer/jwks",
        )


def test_loopback_http_oidc_is_allowed_only_for_local_test_issuer() -> None:
    local = Settings(
        _env_file=None,
        env="test",
        auth_issuer="http://127.0.0.1:8080/issuer",
        auth_audience="codequest-api",
        auth_jwks_url="http://localhost:8080/issuer/jwks",
    )
    assert local.authentication_configured


def test_local_keycloak_issuer_and_jwks_configuration_is_accepted() -> None:
    settings = Settings(
        env="local",
        auth_issuer="http://localhost:8080/realms/codequest-dev",
        auth_audience="codequest-api",
        auth_jwks_url=("http://localhost:8080/realms/codequest-dev/protocol/openid-connect/certs"),
    )
    assert settings.authentication_configured
    assert settings.auth_issuer == "http://localhost:8080/realms/codequest-dev"
    assert settings.auth_audience == "codequest-api"


def test_oidc_rejects_wrong_issuer_expired_or_missing_required_claims(
    monkeypatch, signing_pair
) -> None:
    settings = _settings()
    private_key, public_key = signing_pair
    monkeypatch.setattr(
        security,
        "get_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key)
        ),
    )

    invalid_claim_sets = [
        _claims(settings, iss="https://another-issuer.test/"),
        _claims(settings, exp=datetime.now(UTC) - timedelta(minutes=1)),
    ]
    missing_exp = _claims(settings)
    missing_exp.pop("exp")
    invalid_claim_sets.append(missing_exp)
    missing_issued_at = _claims(settings)
    missing_issued_at.pop("iat")
    invalid_claim_sets.append(missing_issued_at)
    missing_subject = _claims(settings)
    missing_subject.pop("sub")
    invalid_claim_sets.append(missing_subject)

    for claims in invalid_claim_sets:
        token = jwt.encode(claims, private_key, algorithm="RS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as error:
            security.get_current_subject(credentials, settings)
        assert error.value.status_code == 401

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from BackendAPI.app import security
from BackendAPI.app.config import Settings
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


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
        security.get_current_subject(None, Settings())
    assert unconfigured.value.status_code == 503

    with pytest.raises(HTTPException) as missing:
        security.get_current_subject(None, _settings())
    assert missing.value.status_code == 401

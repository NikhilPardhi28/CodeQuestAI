from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError
from sqlalchemy.orm import Session

from BackendAPI.app.config import Settings, get_settings
from BackendAPI.app.db.models import PlayerProfile
from BackendAPI.app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


@lru_cache(maxsize=8)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, timeout=5, cache_keys=True)


def get_current_subject(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    if not settings.authentication_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication_not_configured",
            headers={"Retry-After": "60"},
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if len(credentials.credentials) > 8192:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        signing_key = get_jwks_client(settings.auth_jwks_url).get_signing_key_from_jwt(
            credentials.credentials
        )
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identity_provider_unavailable",
            headers={"Retry-After": "5"},
        ) from exc
    except (PyJWKClientError, jwt.PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_bearer_subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


def get_current_profile(
    subject: str = Depends(get_current_subject),
    session: Session = Depends(get_db),
) -> PlayerProfile:
    profile = session.query(PlayerProfile).filter_by(identity_subject=subject).one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="player_profile_not_found")
    return profile

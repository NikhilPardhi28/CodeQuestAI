from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
from BackendAPI.app import security
from BackendAPI.app.config import Settings, get_settings
from BackendAPI.app.db.models import PlayerProfile, PlayerQuestProgress
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt import PyJWKClientConnectionError
from sqlalchemy.exc import OperationalError


def test_health_and_readiness(client: TestClient) -> None:
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert health.headers.get("x-request-id")

    readiness = client.get("/readyz")
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_readiness_returns_retryable_error_when_database_is_down(app, client: TestClient) -> None:
    from BackendAPI.app.db.session import get_db

    class OfflineSession:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

        def rollback(self):
            pass

    def offline_db():
        yield OfflineSession()

    app.dependency_overrides[get_db] = offline_db
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["code"] == "database_unavailable"
    assert response.json()["retryable"] is True


def test_public_curriculum_and_quest_retrieval(client: TestClient) -> None:
    regions = client.get("/api/v1/curriculum/regions?limit=2")
    assert regions.status_code == 200
    assert regions.json()["total"] == 4
    assert [item["slug"] for item in regions.json()["items"]] == [
        "variable-valley",
        "variable-vale",
    ]

    objectives = client.get("/api/v1/curriculum/objectives", params={"region_slug": "typeworks"})
    assert objectives.status_code == 200
    assert [item["slug"] for item in objectives.json()["items"]] == [
        "python-data-types",
        "numeric-operators",
    ]

    quest = client.get("/api/v1/quests/light-the-signal")
    assert quest.status_code == 200
    assert quest.json()["objectiveSlug"] == "variables-and-assignment"

    challenge = client.get("/api/v1/challenges/signal-coordinate")
    assert challenge.status_code == 200
    assert "sourceDigest" not in challenge.json()
    assert "hiddenTests" not in challenge.json()


def test_catalog_returns_only_latest_published_content(client: TestClient, db_session) -> None:
    from BackendAPI.app.db.models import CurriculumRegion

    db_session.add(
        CurriculumRegion(
            slug="variable-vale",
            version=2,
            name="Variable Vale Revised",
            summary="Revised published version.",
            sort_order=1,
            is_published=True,
        )
    )
    db_session.commit()
    result = client.get("/api/v1/curriculum/regions/variable-vale")
    assert result.status_code == 200
    assert result.json()["version"] == 2
    assert result.json()["name"] == "Variable Vale Revised"


def test_public_not_found_and_invalid_pagination_use_error_envelope(client: TestClient) -> None:
    missing = client.get("/api/v1/quests/not-a-quest")
    assert missing.status_code == 404
    assert missing.json()["code"] == "quest_not_found"
    assert missing.json()["correlationId"] == missing.headers["x-request-id"]

    invalid = client.get("/api/v1/curriculum/regions?limit=101")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "request_validation_error"


def test_player_routes_fail_closed_without_auth_configuration(client: TestClient) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == 503
    assert response.json()["code"] == "authentication_not_configured"
    assert client.get("/api/v1/me/quests").status_code == 503


def test_player_routes_require_a_valid_token(app, client: TestClient, monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    settings = Settings(
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
    )
    app.dependency_overrides[get_settings] = lambda: settings

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, _token: str):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(security, "get_jwks_client", lambda _url: FakeJwksClient())

    unauthorized = client.get("/api/v1/me")
    assert unauthorized.status_code == 401
    assert unauthorized.headers["www-authenticate"] == "Bearer"

    token = jwt.encode(
        {
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
            "sub": "issuer-subject-1",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "unit-test-key"},
    )
    headers = {"Authorization": f"Bearer {token}"}

    created = client.put(
        "/api/v1/me", json={"displayName": "  Ada   Learner ", "locale": "en-US"}, headers=headers
    )
    assert created.status_code == 200
    assert created.json()["displayName"] == "Ada Learner"
    assert created.json()["locale"] == "en-US"

    updated = client.get("/api/v1/me", headers=headers)
    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]
    assert client.get("/api/v1/me/progression", headers=headers).json()["level"] == 1
    assert client.get("/api/v1/me/quests", headers=headers).status_code == 200
    assert client.get("/api/v1/me/achievements", headers=headers).status_code == 200
    assert client.get("/api/v1/me/submissions", headers=headers).status_code == 200


def test_token_audience_and_signature_are_verified(app, client: TestClient, monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        security,
        "get_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )
    claims = {
        "iss": settings.auth_issuer,
        "aud": "wrong-audience",
        "sub": "issuer-subject-2",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(claims, private_key, algorithm="RS256")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_bearer_token"


def test_identity_provider_outage_is_retryable(app, client: TestClient, monkeypatch) -> None:
    settings = Settings(
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
    )
    app.dependency_overrides[get_settings] = lambda: settings

    class OfflineJwksClient:
        def get_signing_key_from_jwt(self, _token: str):
            raise PyJWKClientConnectionError("offline")

    monkeypatch.setattr(security, "get_jwks_client", lambda _url: OfflineJwksClient())
    # Key lookup fails before token decoding, so no signed token is needed here.
    token = "synthetic-token"
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert response.json()["retryable"] is True


def test_quest_progress_is_scoped_to_authenticated_profile(
    app, client: TestClient, db_session, monkeypatch
) -> None:
    from BackendAPI.app.config import get_settings

    app.dependency_overrides[get_settings] = lambda: Settings(
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
    )
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        security,
        "get_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )

    def headers_for(subject: str) -> dict[str, str]:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": "https://issuer.test/",
                "aud": "codequest-api",
                "sub": subject,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
        )
        return {"Authorization": f"Bearer {token}"}

    first = client.put(
        "/api/v1/me", json={"displayName": "Learner One"}, headers=headers_for("one")
    )
    second = client.put(
        "/api/v1/me", json={"displayName": "Learner Two"}, headers=headers_for("two")
    )
    first_profile = db_session.query(PlayerProfile).filter_by(identity_subject="one").one()
    db_session.add(
        PlayerQuestProgress(
            player_profile_id=first_profile.id,
            quest_slug="light-the-signal",
            quest_version=1,
            status="in_progress",
            state={"checkpoint": "signal-tower"},
        )
    )
    db_session.commit()

    first_quests = client.get("/api/v1/me/quests", headers=headers_for("one"))
    second_quests = client.get("/api/v1/me/quests", headers=headers_for("two"))
    assert first.status_code == second.status_code == 200
    assert first_quests.json()["total"] == 1
    assert first_quests.json()["items"][0]["questSlug"] == "light-the-signal"
    assert second_quests.json()["total"] == 0


def test_challenge_submission_and_polling_are_authenticated_and_owner_scoped(
    app, client: TestClient, db_session, monkeypatch
) -> None:
    from BackendAPI.app.config import get_settings
    from BackendAPI.app.db.models import CodingChallengeDefinition
    from BackendAPI.app.services import submissions

    settings = Settings(
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
        evaluation_worker_url="http://127.0.0.1:8100",
        evaluation_worker_token="local-test-worker-token-that-is-long-enough",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        security,
        "get_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )
    monkeypatch.setattr(submissions, "dispatch_to_worker", lambda *_args: None)

    def headers_for(subject: str) -> dict[str, str]:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": settings.auth_issuer,
                "aud": settings.auth_audience,
                "sub": subject,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
        )
        return {"Authorization": f"Bearer {token}"}

    path = "/api/v1/challenges/signal-coordinate/submissions"
    payload = {
        "clientSubmissionId": "0fedb4c5-58e0-49b7-8c91-3de94099db6b",
        "challengeVersion": 1,
        "source": "def signal_coordinate(x, y): return (x, y)",
    }
    assert client.post(path, json=payload).status_code == 401

    owner_headers = headers_for("submission-owner")
    other_headers = headers_for("submission-other")
    for headers, name in ((owner_headers, "Owner"), (other_headers, "Other")):
        assert (
            client.put("/api/v1/me", json={"displayName": name}, headers=headers).status_code == 200
        )

    challenge = db_session.get(CodingChallengeDefinition, ("signal-coordinate", 1))
    original_content = challenge.public_content
    challenge.public_content = {"kind": "legacy"}
    db_session.commit()
    not_evaluable = client.post(path, json=payload, headers=owner_headers)
    assert not_evaluable.status_code == 409
    assert not_evaluable.json()["code"] == "challenge_not_evaluable"
    challenge.public_content = original_content
    db_session.commit()

    forged = {**payload, "passed": True, "scorePercent": 100, "passedTests": 4}
    assert client.post(path, json=forged, headers=owner_headers).status_code == 422

    submitted = client.post(path, json=payload, headers=owner_headers)
    assert submitted.status_code == 202
    submission_id = submitted.json()["id"]
    assert submitted.json()["status"] == "queued"
    assert "source" not in submitted.json()

    replay = client.post(path, json=payload, headers=owner_headers)
    assert replay.status_code == 200
    assert replay.json()["id"] == submission_id

    owned = client.get(f"/api/v1/me/submissions/{submission_id}", headers=owner_headers)
    hidden = client.get(f"/api/v1/me/submissions/{submission_id}", headers=other_headers)
    assert owned.status_code == 200
    assert hidden.status_code == 404


def test_submission_routes_reject_unauthenticated_and_expired_tokens(
    app, client: TestClient, db_session, monkeypatch
) -> None:
    from BackendAPI.app.config import get_settings
    from BackendAPI.app.db.models import SubmissionRecord
    from BackendAPI.app.services import submissions

    app.dependency_overrides[get_settings] = lambda: Settings(
        auth_issuer="https://issuer.test/",
        auth_audience="codequest-api",
        auth_jwks_url="https://issuer.test/jwks",
    )
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        security,
        "get_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )
    monkeypatch.setattr(submissions, "dispatch_to_worker", lambda *_args: None)
    headers = {
        "Authorization": "Bearer "
        + jwt.encode(
            {
                "iss": "https://issuer.test/",
                "aud": "codequest-api",
                "sub": "submission-api-player",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) - timedelta(minutes=1),
            },
            private_key,
            algorithm="RS256",
        )
    }
    path = "/api/v1/challenges/signal-coordinate/submissions"
    body = {
        "clientSubmissionId": "3e45c88b-a3f8-4d65-9a37-6999aa59179d",
        "challengeVersion": 1,
        "source": "def signal_coordinate(x, y): return (x, y)",
    }

    unauthenticated = client.post(path, json=body)
    expired = client.post(path, json=body, headers=headers)
    assert unauthenticated.status_code == 401
    assert expired.status_code == 401
    assert db_session.query(SubmissionRecord).count() == 0

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
from BackendAPI.app import security
from BackendAPI.app.config import Settings, get_settings
from BackendAPI.app.db.models import (
    PlayerProfile,
    PlayerProgression,
    PlayerQuestEvent,
    PlayerQuestProgress,
    PlayerQuestRewardLedger,
    SubmissionRecord,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient


class SyncASGIClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        async def send():
            async with AsyncClient(
                transport=ASGITransport(app=self.app), base_url="http://test"
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)


def _auth(app, monkeypatch, client: SyncASGIClient):
    settings = Settings(
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
    app.dependency_overrides[get_settings] = lambda: settings

    def headers(subject: str):
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
        result = {"Authorization": f"Bearer {token}"}
        client.put(
            "/api/v1/me",
            json={"displayName": subject},
            headers=result,
        ).raise_for_status()
        return result

    return headers


def _event(event_type: str, target_id: str, revision: int, **extra):
    return {
        "eventId": str(uuid4()),
        "questVersion": 1,
        "expectedRevision": revision,
        "eventType": event_type,
        "targetId": target_id,
        "targetVersion": 1,
        **extra,
    }


def test_quest_events_enforce_registered_targets_prerequisites_and_ownership(
    app, db_session, monkeypatch
) -> None:
    client = SyncASGIClient(app)
    headers = _auth(app, monkeypatch, client)
    first = headers("learner-one")
    second = headers("learner-two")

    assert (
        client.post(
            "/api/v2/me/quests/light-the-signal/events",
            json=_event("checkpoint", "signal-platform", 0),
            headers=first,
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v2/me/quests/light-the-signal/events",
            json=_event("interact", "not-registered", 0),
            headers=first,
        ).status_code
        == 409
    )

    interaction = _event("interact", "relay-switch", 0)
    accepted = client.post(
        "/api/v2/me/quests/light-the-signal/events", json=interaction, headers=first
    )
    assert accepted.status_code == 200
    assert accepted.json()["revision"] == 1
    retry = client.post(
        "/api/v2/me/quests/light-the-signal/events", json=interaction, headers=first
    )
    assert retry.status_code == 200
    assert retry.json()["replayed"] is True
    changed = {**interaction, "targetId": "signal-platform"}
    conflict = client.post("/api/v2/me/quests/light-the-signal/events", json=changed, headers=first)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_key_reused"

    stale = client.post(
        "/api/v2/me/quests/light-the-signal/events",
        json=_event("checkpoint", "signal-platform", 0),
        headers=first,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "quest_revision_conflict"
    assert stale.json()["currentState"]["revision"] == 1

    foreign_view = client.get("/api/v2/me/quests", headers=second)
    assert foreign_view.status_code == 200
    assert foreign_view.json()["total"] == 0
    assert (
        db_session.query(PlayerQuestProgress)
        .filter_by(
            player_profile_id=db_session.query(PlayerProfile)
            .filter_by(identity_subject="learner-two")
            .one()
            .id
        )
        .count()
        == 0
    )


def test_challenge_evidence_is_owned_passed_versioned_and_reward_is_idempotent(
    app, db_session, monkeypatch
) -> None:
    client = SyncASGIClient(app)
    headers = _auth(app, monkeypatch, client)("learner")
    player = db_session.query(PlayerProfile).filter_by(identity_subject="learner").one()
    progression = db_session.get(PlayerProgression, player.id)
    assert progression.experience == 0

    for expected, event_type, target in [
        (0, "interact", "relay-switch"),
        (1, "checkpoint", "signal-platform"),
    ]:
        response = client.post(
            "/api/v2/me/quests/light-the-signal/events",
            json=_event(event_type, target, expected),
            headers=headers,
        )
        assert response.status_code == 200

    foreign = PlayerProfile(identity_subject="other", display_name="Other")
    db_session.add(foreign)
    db_session.flush()
    foreign_submission = SubmissionRecord(
        player_profile_id=foreign.id,
        challenge_slug="signal-coordinate",
        challenge_version=1,
        client_submission_id=uuid4(),
        status="passed",
    )
    db_session.add(foreign_submission)
    db_session.commit()
    forged = _event(
        "challenge_passed",
        "signal-coordinate",
        2,
        challengeSubmissionId=str(foreign_submission.id),
    )
    rejected = client.post(
        "/api/v2/me/quests/light-the-signal/events", json=forged, headers=headers
    )
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "challenge_evidence_invalid"

    passed = SubmissionRecord(
        player_profile_id=player.id,
        challenge_slug="signal-coordinate",
        challenge_version=1,
        client_submission_id=uuid4(),
        status="passed",
    )
    db_session.add(passed)
    db_session.commit()
    challenge_event = _event(
        "challenge_passed",
        "signal-coordinate",
        2,
        challengeSubmissionId=str(passed.id),
    )
    completed = client.post(
        "/api/v2/me/quests/light-the-signal/events", json=challenge_event, headers=headers
    )
    assert completed.status_code == 200
    result = completed.json()
    assert result["status"] == "completed"
    assert result["newlyGrantedRewards"] == [
        {"rewardId": "signal-experience", "rewardType": "experience", "experiencePoints": 25}
    ]
    assert result["progression"]["experience"] == 25
    replay = client.post(
        "/api/v2/me/quests/light-the-signal/events", json=challenge_event, headers=headers
    )
    assert replay.status_code == 200
    assert replay.json()["newlyGrantedRewards"] == result["newlyGrantedRewards"]
    assert (
        db_session.query(PlayerQuestRewardLedger).filter_by(player_profile_id=player.id).count()
        == 1
    )
    assert db_session.query(PlayerQuestEvent).filter_by(player_profile_id=player.id).count() == 3


def test_invalid_versions_shapes_and_definition_rules_are_rejected(
    app, monkeypatch, db_session
) -> None:
    client = SyncASGIClient(app)
    headers = _auth(app, monkeypatch, client)("learner")
    missing = client.get("/api/v2/quests/light-the-signal?version=99")
    assert missing.status_code == 404
    unsupported = client.post(
        "/api/v2/me/quests/light-the-signal/events",
        json={**_event("interact", "relay-switch", 0), "questVersion": 99},
        headers=headers,
    )
    assert unsupported.status_code == 404
    unknown_field = client.post(
        "/api/v2/me/quests/light-the-signal/events",
        json={**_event("interact", "relay-switch", 0), "experiencePoints": 100},
        headers=headers,
    )
    assert unknown_field.status_code == 422
    missing_evidence = client.post(
        "/api/v2/me/quests/light-the-signal/events",
        json=_event("challenge_passed", "signal-coordinate", 0),
        headers=headers,
    )
    assert missing_evidence.status_code == 422


def test_cross_quest_prerequisite_requires_completed_server_progress(
    app, monkeypatch, db_session
) -> None:
    client = SyncASGIClient(app)
    headers = _auth(app, monkeypatch, client)("learner")
    blocked = client.post(
        "/api/v2/me/quests/balance-the-foundry/events",
        json=_event("prerequisite_completed", "light-the-signal", 0),
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "quest_prerequisite_not_met"

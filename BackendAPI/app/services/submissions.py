from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import (
    ChallengeHiddenTestCase,
    ChallengeHint,
    CodingChallengeDefinition,
    EvaluationAttempt,
    PlayerChallengeHintUnlock,
    PlayerProfile,
    PlayerQuestProgress,
    QuestDefinition,
    QuestObjectiveRule,
    SubmissionRecord,
)
from BackendAPI.app.schemas import (
    ChallengeSubmissionRequest,
    QuestEventRequest,
    WorkerEvaluationResponse,
)
from BackendAPI.app.services.quest_events import (
    QuestEventError,
    _ensure_quest_progress,
    submit_quest_event,
)


class SubmissionError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _request_hash(challenge_slug: str, payload: ChallengeSubmissionRequest) -> tuple[str, str]:
    source_digest = hashlib.sha256(payload.source.encode("utf-8")).hexdigest()
    canonical = {
        "challengeSlug": challenge_slug,
        "challengeVersion": payload.challengeVersion,
        "sourceDigest": source_digest,
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return digest, source_digest


def create_submission(
    session: Session,
    profile: PlayerProfile,
    challenge_slug: str,
    payload: ChallengeSubmissionRequest,
    *,
    queue_limit: int = 500,
) -> tuple[SubmissionRecord, bool]:
    challenge = session.get(CodingChallengeDefinition, (challenge_slug, payload.challengeVersion))
    if challenge is None or not challenge.is_published:
        raise SubmissionError(
            404, "challenge_version_not_found", "The published challenge version was not found."
        )
    content = challenge.public_content
    hidden_count = (
        session.scalar(
            select(func.count())
            .select_from(ChallengeHiddenTestCase)
            .where(
                ChallengeHiddenTestCase.challenge_slug == challenge.slug,
                ChallengeHiddenTestCase.challenge_version == challenge.version,
            )
        )
        or 0
    )
    if (
        not isinstance(content, dict)
        or content.get("mode") != "function"
        or not isinstance(content.get("functionName"), str)
        or not content.get("functionName")
        or not isinstance(content.get("visibleTests"), list)
        or not content["visibleTests"]
        or hidden_count < 1
    ):
        raise SubmissionError(
            409,
            "challenge_not_evaluable",
            "This challenge version does not have a complete approved evaluator definition.",
        )
    if len(payload.source.encode("utf-8")) > challenge.max_source_bytes:
        raise SubmissionError(
            413, "source_too_large", "The submitted source exceeds this challenge's size limit."
        )

    request_hash, source_digest = _request_hash(challenge_slug, payload)
    existing = session.scalar(
        select(SubmissionRecord).where(
            SubmissionRecord.player_profile_id == profile.id,
            SubmissionRecord.client_submission_id == payload.clientSubmissionId,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise SubmissionError(
                409,
                "idempotency_key_reused",
                "This submission key was already used with a different payload.",
            )
        return existing, True

    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": 728194003})
    session.scalar(select(PlayerProfile.id).where(PlayerProfile.id == profile.id).with_for_update())

    now = datetime.now(UTC)
    minute_count = (
        session.scalar(
            select(func.count())
            .select_from(SubmissionRecord)
            .where(
                SubmissionRecord.player_profile_id == profile.id,
                SubmissionRecord.created_at >= now - timedelta(minutes=1),
            )
        )
        or 0
    )
    day_count = (
        session.scalar(
            select(func.count())
            .select_from(SubmissionRecord)
            .where(
                SubmissionRecord.player_profile_id == profile.id,
                SubmissionRecord.created_at >= now - timedelta(days=1),
            )
        )
        or 0
    )
    queued_count = (
        session.scalar(
            select(func.count())
            .select_from(SubmissionRecord)
            .where(SubmissionRecord.status.in_(["queued", "running"]))
        )
        or 0
    )
    if minute_count >= 5 or day_count >= 30:
        raise SubmissionError(
            429, "submission_rate_limited", "Too many submissions. Please wait before trying again."
        )
    if queued_count >= queue_limit:
        raise SubmissionError(
            503, "evaluation_queue_full", "The evaluation queue is temporarily full."
        )

    record = SubmissionRecord(
        player_profile_id=profile.id,
        challenge_slug=challenge_slug,
        challenge_version=challenge.version,
        client_submission_id=payload.clientSubmissionId,
        status="queued",
        source_digest=source_digest,
        source_code=payload.source,
        request_hash=request_hash,
    )
    session.add(record)
    try:
        session.flush()
        session.add(EvaluationAttempt(submission_id=record.id, attempt_number=1, status="queued"))
        session.commit()
        session.refresh(record)
        return record, False
    except IntegrityError as exc:
        session.rollback()
        duplicate = session.scalar(
            select(SubmissionRecord).where(
                SubmissionRecord.player_profile_id == profile.id,
                SubmissionRecord.client_submission_id == payload.clientSubmissionId,
            )
        )
        if duplicate is not None and duplicate.request_hash == request_hash:
            return duplicate, True
        raise SubmissionError(
            409, "submission_conflict", "The submission could not be created safely."
        ) from exc


def get_owned_submission(
    session: Session, profile_id: UUID, submission_id: UUID
) -> SubmissionRecord | None:
    return session.scalar(
        select(SubmissionRecord).where(
            SubmissionRecord.id == submission_id,
            SubmissionRecord.player_profile_id == profile_id,
        )
    )


def expire_submission_sources(
    session: Session, *, retention_days: int = 30, now: datetime | None = None
) -> int:
    """Remove old source from terminal submissions while retaining idempotency metadata."""
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    result = session.execute(
        update(SubmissionRecord)
        .where(
            SubmissionRecord.created_at < cutoff,
            SubmissionRecord.status.in_(("passed", "failed", "timed_out", "internal_error")),
            SubmissionRecord.source_code.is_not(None),
        )
        .values(source_code=None)
    )
    session.commit()
    return int(result.rowcount or 0)


def get_progressive_hint(
    session: Session, profile_id: UUID, challenge_slug: str, version: int, level: int
) -> dict[str, object]:
    challenge = session.get(CodingChallengeDefinition, (challenge_slug, version))
    if challenge is None or not challenge.is_published:
        raise SubmissionError(
            404, "challenge_version_not_found", "The published challenge version was not found."
        )
    hint = session.scalar(
        select(ChallengeHint).where(
            ChallengeHint.challenge_slug == challenge_slug,
            ChallengeHint.challenge_version == version,
            ChallengeHint.level == level,
        )
    )
    if hint is None:
        raise SubmissionError(404, "challenge_hint_not_found", "That hint is not available.")
    if level > 1:
        previous = session.get(
            PlayerChallengeHintUnlock, (profile_id, challenge_slug, version, level - 1)
        )
        if previous is None:
            raise SubmissionError(409, "challenge_hint_locked", "Request the previous hint first.")
    session.merge(
        PlayerChallengeHintUnlock(
            player_profile_id=profile_id,
            challenge_slug=challenge_slug,
            challenge_version=version,
            level=level,
        )
    )
    session.commit()
    return {
        "challengeSlug": challenge_slug,
        "challengeVersion": version,
        "level": hint.level,
        "content": hint.content,
    }


def build_worker_job(session: Session, submission: SubmissionRecord) -> dict[str, object]:
    challenge = session.get(
        CodingChallengeDefinition, (submission.challenge_slug, submission.challenge_version)
    )
    if challenge is None or not challenge.is_published or submission.source_code is None:
        raise SubmissionError(
            409, "evaluation_input_invalid", "The stored evaluation input is unavailable."
        )
    hidden = session.scalars(
        select(ChallengeHiddenTestCase)
        .where(
            ChallengeHiddenTestCase.challenge_slug == challenge.slug,
            ChallengeHiddenTestCase.challenge_version == challenge.version,
        )
        .order_by(ChallengeHiddenTestCase.position)
    ).all()
    public = challenge.public_content
    visible_tests = public.get("visibleTests", []) if isinstance(public, dict) else []
    return {
        "submissionId": str(submission.id),
        "challengeSlug": challenge.slug,
        "challengeVersion": challenge.version,
        "evaluatorVersion": challenge.evaluator_version,
        "source": submission.source_code,
        "sourceDigest": submission.source_digest,
        "definition": {
            "mode": public.get("mode", "function"),
            "functionName": public.get("functionName"),
            "visibleTests": visible_tests,
            "hiddenTests": [row.test_definition for row in hidden],
            "timeLimitMs": challenge.time_limit_ms,
            "outputLimitBytes": challenge.output_limit_bytes,
        },
    }


def fail_submission(session: Session, submission_id: UUID, error_code: str) -> None:
    submission = session.scalar(
        select(SubmissionRecord).where(SubmissionRecord.id == submission_id).with_for_update()
    )
    if submission is None or submission.status not in {"queued", "running"}:
        return
    attempt = session.scalar(
        select(EvaluationAttempt)
        .where(EvaluationAttempt.submission_id == submission.id)
        .with_for_update()
    )
    now = datetime.now(UTC)
    submission.status = "internal_error"
    submission.result_summary = {
        "scorePercent": None,
        "passedTests": None,
        "totalTests": None,
        "visibleResults": [],
        "diagnostics": [],
    }
    submission.completed_at = now
    if attempt is not None:
        attempt.status = "internal_error"
        attempt.error_code = error_code
        attempt.completed_at = now
    session.commit()


def defer_submission(session_factory, submission_id: UUID) -> None:
    with session_factory() as session:
        submission = session.scalar(
            select(SubmissionRecord).where(SubmissionRecord.id == submission_id).with_for_update()
        )
        attempt = session.scalar(
            select(EvaluationAttempt)
            .where(EvaluationAttempt.submission_id == submission_id)
            .with_for_update()
        )
        if submission is not None and attempt is not None and submission.status == "running":
            submission.status = "queued"
            attempt.status = "queued"
            session.commit()


def dispatch_to_worker(
    session_factory, submission_id: UUID, worker_url: str, worker_token: str
) -> None:
    """Call only the separate worker service; this API process never executes submitted source."""
    from BackendAPI.app.db.models import SubmissionRecord

    with session_factory() as session:
        submission = session.scalar(
            select(SubmissionRecord).where(SubmissionRecord.id == submission_id).with_for_update()
        )
        if submission is None or submission.status != "queued":
            return
        attempt = session.scalar(
            select(EvaluationAttempt)
            .where(EvaluationAttempt.submission_id == submission_id)
            .with_for_update()
        )
        if attempt is None or attempt.status != "queued":
            return
        submission.status = "running"
        attempt.status = "running"
        session.commit()
        try:
            job = build_worker_job(session, submission)
        except SubmissionError:
            fail_submission(session, submission_id, "evaluation_input_invalid")
            return

    request = urllib.request.Request(
        worker_url.rstrip("/") + "/internal/evaluate",
        data=json.dumps(job, separators=(",", ":")).encode("utf-8"),
        headers={"Authorization": f"Bearer {worker_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            content_length = response.headers.get("Content-Length", "0")
            if response.status != 200 or (content_length.isdigit() and int(content_length) > 32768):
                with session_factory() as session:
                    fail_submission(session, submission_id, "worker_unavailable")
                return
            body = response.read(32769)
            if len(body) > 32768:
                with session_factory() as session:
                    fail_submission(session, submission_id, "worker_response_too_large")
                return
        result = WorkerEvaluationResponse.model_validate_json(body)
    except urllib.error.HTTPError as exc:
        if exc.code in {429, 503}:
            defer_submission(session_factory, submission_id)
        else:
            with session_factory() as session:
                fail_submission(session, submission_id, "worker_unavailable")
        return
    except (OSError, TimeoutError, ValueError):
        with session_factory() as session:
            fail_submission(session, submission_id, "worker_unavailable")
        return
    with session_factory() as session:
        try:
            owner = session.scalar(
                select(SubmissionRecord.player_profile_id).where(
                    SubmissionRecord.id == submission_id
                )
            )
            if owner is None:
                return
            apply_worker_result(session, owner, submission_id, result)
        except Exception:
            session.rollback()
            fail_submission(session, submission_id, "worker_result_invalid")


def validate_worker_result(
    session: Session, submission: SubmissionRecord, result: WorkerEvaluationResponse
) -> dict[str, object]:
    challenge = session.get(
        CodingChallengeDefinition, (submission.challenge_slug, submission.challenge_version)
    )
    if challenge is None:
        raise SubmissionError(
            409, "evaluation_challenge_missing", "The evaluated challenge version is unavailable."
        )
    if (
        result.submissionId != submission.id
        or result.challengeSlug != submission.challenge_slug
        or result.challengeVersion != submission.challenge_version
        or result.evaluatorVersion != challenge.evaluator_version
    ):
        raise SubmissionError(
            502, "worker_result_mismatch", "The evaluator returned an invalid result."
        )

    hidden_total = (
        session.scalar(
            select(func.count())
            .select_from(ChallengeHiddenTestCase)
            .where(
                ChallengeHiddenTestCase.challenge_slug == challenge.slug,
                ChallengeHiddenTestCase.challenge_version == challenge.version,
            )
        )
        or 0
    )
    if result.hiddenTotal != hidden_total:
        raise SubmissionError(
            502, "worker_result_malformed", "The evaluator returned an invalid result."
        )
    if result.hiddenPassed > result.hiddenTotal:
        raise SubmissionError(
            502, "worker_result_malformed", "The evaluator returned an invalid result."
        )

    if result.infrastructureError:
        return {"status": "internal_error", "errorCode": "evaluation_infrastructure_error"}
    if result.timedOut:
        return {"status": "timed_out", "errorCode": "evaluation_timed_out"}

    visible = challenge.public_content.get("visibleTests", [])
    visible_total = len(visible) if isinstance(visible, list) else -1
    if len(result.visibleResults) != visible_total:
        raise SubmissionError(
            502, "worker_result_malformed", "The evaluator returned an invalid result."
        )

    visible_passed = sum(item.passed for item in result.visibleResults)
    total = visible_total + hidden_total
    passed = visible_passed + result.hiddenPassed
    score = int(passed * 100 / total) if total else 0
    safe_diagnostics = []
    safe_visible = []
    explanations = {
        "syntax_error": "Check the Python syntax near the reported line.",
        "runtime_error": "Your code raised an error while running.",
        "wrong_answer": "The returned value did not match this example.",
        "timeout": "Your code took too long to finish.",
        "output_limit": "Your program produced more output than allowed.",
    }
    for item in result.visibleResults:
        code = item.diagnosticCode
        message = explanations.get(code, "") if code else ""
        safe_visible.append(
            {"passed": item.passed, "diagnosticCode": code or "", "message": message}
        )
        if not item.passed and code and not any(d["code"] == code for d in safe_diagnostics):
            safe_diagnostics.append({"code": code, "message": message})
    status = "passed" if score >= challenge.passing_score else "failed"
    return {
        "status": status,
        "hasResult": True,
        "scorePercent": score,
        "passedTests": passed,
        "totalTests": total,
        "visibleResults": safe_visible,
        "diagnostics": safe_diagnostics,
        "workerVersion": result.evaluatorVersion,
    }


def apply_worker_result(
    session: Session, profile_id: UUID, submission_id: UUID, result: WorkerEvaluationResponse
) -> SubmissionRecord:
    submission = session.scalar(
        select(SubmissionRecord)
        .where(
            SubmissionRecord.id == submission_id,
            SubmissionRecord.player_profile_id == profile_id,
        )
        .with_for_update()
    )
    if submission is None:
        raise SubmissionError(404, "submission_not_found", "The submission was not found.")
    if submission.status in {"passed", "failed", "timed_out", "internal_error"}:
        return submission
    if submission.status not in {"queued", "running"}:
        raise SubmissionError(
            409,
            "submission_transition_invalid",
            "The submission cannot accept an evaluation result.",
        )
    attempt = session.scalar(
        select(EvaluationAttempt)
        .where(EvaluationAttempt.submission_id == submission.id)
        .order_by(EvaluationAttempt.attempt_number.desc())
        .with_for_update()
    )
    if attempt is None or attempt.status in {"passed", "failed", "timed_out", "internal_error"}:
        return submission
    try:
        normalized = validate_worker_result(session, submission, result)
    except SubmissionError:
        normalized = {"status": "internal_error", "errorCode": "worker_result_invalid"}
    now = datetime.now(UTC)
    submission.status = str(normalized["status"])
    submission.completed_at = now
    if submission.status in {"passed", "failed"}:
        submission.result_summary = {
            key: value
            for key, value in normalized.items()
            if key not in {"status", "workerVersion"}
        }
    else:
        submission.result_summary = {
            "hasResult": False,
            "scorePercent": None,
            "passedTests": None,
            "totalTests": None,
            "visibleResults": [],
            "diagnostics": [],
        }
    attempt.status = submission.status
    attempt.worker_version = normalized.get("workerVersion")
    attempt.result = submission.result_summary
    attempt.error_code = str(normalized.get("errorCode", "")) or None
    attempt.completed_at = now
    if submission.status == "passed":
        rules = session.scalars(
            select(QuestObjectiveRule).where(
                QuestObjectiveRule.event_type == "challenge_passed",
                QuestObjectiveRule.target_id == submission.challenge_slug,
                QuestObjectiveRule.target_version == submission.challenge_version,
            )
        ).all()
        for rule in rules:
            quest = session.get(QuestDefinition, (rule.quest_slug, rule.quest_version))
            if quest is None or not quest.is_published:
                continue
            _ensure_quest_progress(session, profile_id, quest)
            progress = session.get(
                PlayerQuestProgress, (profile_id, rule.quest_slug, rule.quest_version)
            )
            try:
                submit_quest_event(
                    session,
                    session.get(PlayerProfile, profile_id),
                    rule.quest_slug,
                    QuestEventRequest(
                        eventId=UUID(
                            bytes=hashlib.sha256(
                                f"{submission.id}:{rule.quest_slug}:{rule.objective_id}".encode()
                            ).digest()[:16]
                        ),
                        questVersion=rule.quest_version,
                        expectedRevision=progress.revision,
                        eventType="challenge_passed",
                        targetId=submission.challenge_slug,
                        targetVersion=submission.challenge_version,
                        challengeSubmissionId=submission.id,
                    ),
                    commit=False,
                )
            except QuestEventError as exc:
                if exc.code not in {
                    "quest_prerequisite_not_met",
                    "quest_objective_already_completed",
                }:
                    session.rollback()
                    raise
    session.commit()
    session.refresh(submission)
    return submission

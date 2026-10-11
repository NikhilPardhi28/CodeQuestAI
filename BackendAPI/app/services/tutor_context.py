"""Permission-limited context boundary for a future optional AI tutor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import CodingChallengeDefinition, SubmissionRecord


@dataclass(frozen=True)
class TutorDiagnostic:
    code: str
    message: str


@dataclass(frozen=True)
class TutorContext:
    challenge_slug: str
    challenge_version: int
    learning_objective_slug: str
    instructions: str
    diagnostics: tuple[TutorDiagnostic, ...]
    prior_submission_count: int
    prior_best_score: int | None


class TutorProvider(Protocol):
    def respond(self, context: TutorContext) -> str: ...


def build_tutor_context(
    session: Session, profile_id: UUID, challenge_slug: str, version: int
) -> TutorContext | None:
    challenge = session.get(CodingChallengeDefinition, (challenge_slug, version))
    if challenge is None or not challenge.is_published:
        return None
    submissions = session.scalars(
        select(SubmissionRecord)
        .where(
            SubmissionRecord.player_profile_id == profile_id,
            SubmissionRecord.challenge_slug == challenge_slug,
            SubmissionRecord.challenge_version == version,
        )
        .order_by(SubmissionRecord.created_at.desc())
        .limit(20)
    ).all()
    diagnostics: list[TutorDiagnostic] = []
    scores: list[int] = []
    for record in submissions:
        result = record.result_summary or {}
        for item in result.get("diagnostics", []):
            if (
                isinstance(item, dict)
                and isinstance(item.get("code"), str)
                and isinstance(item.get("message"), str)
            ):
                diagnostics.append(TutorDiagnostic(item["code"], item["message"][:240]))
        if isinstance(result.get("scorePercent"), int):
            scores.append(result["scorePercent"])
    return TutorContext(
        challenge_slug=challenge.slug,
        challenge_version=challenge.version,
        learning_objective_slug=challenge.objective_slug,
        instructions=challenge.statement,
        diagnostics=tuple(diagnostics[-20:]),
        prior_submission_count=len(submissions),
        prior_best_score=max(scores) if scores else None,
    )

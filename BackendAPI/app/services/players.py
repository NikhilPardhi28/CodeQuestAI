from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import (
    PlayerAchievementAward,
    PlayerProfile,
    PlayerProgression,
    PlayerQuestProgress,
    SubmissionRecord,
)


def get_profile(session: Session, subject: str) -> PlayerProfile | None:
    return session.scalar(select(PlayerProfile).where(PlayerProfile.identity_subject == subject))


def upsert_profile(
    session: Session, subject: str, *, display_name: str, locale: str
) -> PlayerProfile:
    profile = get_profile(session, subject)
    if profile is None:
        profile = PlayerProfile(identity_subject=subject, display_name=display_name, locale=locale)
        session.add(profile)
        session.flush()
        session.add(PlayerProgression(player_profile_id=profile.id))
    else:
        profile.display_name = display_name
        profile.locale = locale
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise
    session.refresh(profile)
    return profile


def list_quest_progress(session: Session, profile_id: UUID, *, limit: int, offset: int):
    query = select(PlayerQuestProgress).where(PlayerQuestProgress.player_profile_id == profile_id)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.order_by(PlayerQuestProgress.updated_at.desc(), PlayerQuestProgress.quest_slug)
        .limit(limit)
        .offset(offset)
    ).all()
    return items, total


def get_progression(session: Session, profile_id: UUID) -> PlayerProgression | None:
    return session.get(PlayerProgression, profile_id)


def list_achievement_awards(session: Session, profile_id: UUID, *, limit: int, offset: int):
    query = select(PlayerAchievementAward).where(
        PlayerAchievementAward.player_profile_id == profile_id
    )
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.order_by(
            PlayerAchievementAward.awarded_at.desc(), PlayerAchievementAward.achievement_slug
        )
        .limit(limit)
        .offset(offset)
    ).all()
    return items, total


def list_submissions(session: Session, profile_id: UUID, *, limit: int, offset: int):
    query = select(SubmissionRecord).where(SubmissionRecord.player_profile_id == profile_id)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.order_by(SubmissionRecord.created_at.desc(), SubmissionRecord.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return items, total

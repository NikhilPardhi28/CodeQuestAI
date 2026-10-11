from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from BackendAPI.app.db.models import (
    AchievementDefinition,
    CodingChallengeDefinition,
    CurriculumRegion,
    LearningObjective,
    QuestDefinition,
)

ContentModel = TypeVar(
    "ContentModel",
    CurriculumRegion,
    LearningObjective,
    QuestDefinition,
    CodingChallengeDefinition,
    AchievementDefinition,
)


def latest_published_query(model: type[ContentModel]):
    versioned = aliased(model)
    latest_version = (
        select(func.max(versioned.version))
        .where(versioned.slug == model.slug)
        .where(versioned.is_published.is_(True))
        .correlate(model)
        .scalar_subquery()
    )
    return select(model).where(model.is_published.is_(True), model.version == latest_version)


def page_query(session: Session, query, *, limit: int, offset: int, order_by):
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    items = session.scalars(query.order_by(*order_by).limit(limit).offset(offset)).all()
    return items, total


def list_regions(session: Session, *, limit: int, offset: int):
    query = latest_published_query(CurriculumRegion)
    return page_query(
        session,
        query,
        limit=limit,
        offset=offset,
        order_by=(CurriculumRegion.sort_order, CurriculumRegion.slug),
    )


def get_region(session: Session, slug: str) -> CurriculumRegion | None:
    return session.scalar(
        latest_published_query(CurriculumRegion).where(CurriculumRegion.slug == slug)
    )


def list_objectives(session: Session, *, limit: int, offset: int, region_slug: str | None = None):
    query = latest_published_query(LearningObjective)
    if region_slug is not None:
        query = query.where(LearningObjective.region_slug == region_slug)
    return page_query(
        session,
        query,
        limit=limit,
        offset=offset,
        order_by=(
            LearningObjective.region_slug,
            LearningObjective.sort_order,
            LearningObjective.slug,
        ),
    )


def get_objective(session: Session, slug: str) -> LearningObjective | None:
    return session.scalar(
        latest_published_query(LearningObjective).where(LearningObjective.slug == slug)
    )


def list_quests(session: Session, *, limit: int, offset: int, region_slug: str | None = None):
    query = latest_published_query(QuestDefinition)
    if region_slug is not None:
        query = query.where(QuestDefinition.region_slug == region_slug)
    return page_query(
        session,
        query,
        limit=limit,
        offset=offset,
        order_by=(QuestDefinition.region_slug, QuestDefinition.slug),
    )


def get_quest(session: Session, slug: str) -> QuestDefinition | None:
    return session.scalar(
        latest_published_query(QuestDefinition).where(QuestDefinition.slug == slug)
    )


def list_challenges(
    session: Session, *, limit: int, offset: int, objective_slug: str | None = None
):
    query = latest_published_query(CodingChallengeDefinition)
    if objective_slug is not None:
        query = query.where(CodingChallengeDefinition.objective_slug == objective_slug)
    return page_query(
        session,
        query,
        limit=limit,
        offset=offset,
        order_by=(CodingChallengeDefinition.objective_slug, CodingChallengeDefinition.slug),
    )


def get_challenge(session: Session, slug: str) -> CodingChallengeDefinition | None:
    return session.scalar(
        latest_published_query(CodingChallengeDefinition).where(
            CodingChallengeDefinition.slug == slug
        )
    )

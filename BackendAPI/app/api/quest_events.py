from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import PlayerProfile
from BackendAPI.app.db.session import get_db
from BackendAPI.app.schemas import (
    Page,
    ProgressionOut,
    QuestDefinitionV2Out,
    QuestEventRequest,
    QuestEventResult,
    QuestProgressV2Out,
)
from BackendAPI.app.security import get_current_profile
from BackendAPI.app.services import players
from BackendAPI.app.services.quest_events import (
    get_quest_definition,
    list_profile_quest_progress,
    submit_quest_event,
)

router = APIRouter(prefix="/api/v2", tags=["quest-events-v2"])


@router.get("/quests/{quest_slug}", response_model=QuestDefinitionV2Out)
def read_quest_definition(
    quest_slug: str,
    version: int = Query(ge=1),
    session: Session = Depends(get_db),
) -> QuestDefinitionV2Out:
    definition = get_quest_definition(session, quest_slug, version)
    if definition is None:
        raise HTTPException(status_code=404, detail="quest_version_not_found")
    return QuestDefinitionV2Out(**definition)


@router.post(
    "/me/quests/{quest_slug}/events",
    response_model=QuestEventResult,
    summary="Submit a server-validated quest event",
    responses={409: {"description": "Invalid transition or stale quest revision"}},
)
def post_quest_event(
    quest_slug: str,
    payload: QuestEventRequest,
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> QuestEventResult:
    return QuestEventResult(**submit_quest_event(session, profile, quest_slug, payload))


@router.get("/me/quests", response_model=Page[QuestProgressV2Out])
def read_my_quests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> Page[QuestProgressV2Out]:
    items, total = list_profile_quest_progress(session, profile.id, limit, offset)
    return Page[QuestProgressV2Out](items=items, limit=limit, offset=offset, total=total)


@router.get("/me/progression", response_model=ProgressionOut)
def read_my_progression(
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> ProgressionOut:
    progression = players.get_progression(session, profile.id)
    if progression is None:
        raise HTTPException(status_code=404, detail="player_progression_not_found")
    return ProgressionOut.model_validate(progression)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import PlayerProfile
from BackendAPI.app.db.session import get_db
from BackendAPI.app.schemas import Page, QuestOut, QuestProgressOut
from BackendAPI.app.security import get_current_profile
from BackendAPI.app.services import catalog, players

router = APIRouter(tags=["quests"])


@router.get("/quests", response_model=Page[QuestOut], summary="List published quest definitions")
def list_quests(
    region_slug: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> Page[QuestOut]:
    items, total = catalog.list_quests(session, limit=limit, offset=offset, region_slug=region_slug)
    return Page[QuestOut](items=items, limit=limit, offset=offset, total=total)


@router.get("/quests/{slug}", response_model=QuestOut, summary="Get a published quest definition")
def get_quest(slug: str, session: Session = Depends(get_db)) -> QuestOut:
    quest = catalog.get_quest(session, slug)
    if quest is None:
        raise HTTPException(status_code=404, detail="quest_not_found")
    return quest


@router.get(
    "/me/quests", response_model=Page[QuestProgressOut], summary="List the caller's quest progress"
)
def list_my_quest_progress(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> Page[QuestProgressOut]:
    items, total = players.list_quest_progress(session, profile.id, limit=limit, offset=offset)
    return Page[QuestProgressOut](items=items, limit=limit, offset=offset, total=total)

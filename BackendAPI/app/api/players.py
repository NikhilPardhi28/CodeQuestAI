from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import PlayerProfile
from BackendAPI.app.db.session import get_db
from BackendAPI.app.schemas import (
    AchievementAwardOut,
    Page,
    PlayerProfileOut,
    PlayerProfileUpsert,
    ProgressionOut,
)
from BackendAPI.app.security import get_current_profile, get_current_subject
from BackendAPI.app.services import players

router = APIRouter(prefix="/me", tags=["player"])


@router.get("", response_model=PlayerProfileOut, summary="Get the caller's player profile")
def get_my_profile(profile: PlayerProfile = Depends(get_current_profile)) -> PlayerProfileOut:
    return profile


@router.put("", response_model=PlayerProfileOut, summary="Create or update the caller's profile")
def put_my_profile(
    payload: PlayerProfileUpsert,
    subject: str = Depends(get_current_subject),
    session: Session = Depends(get_db),
) -> PlayerProfileOut:
    profile = players.upsert_profile(
        session,
        subject,
        display_name=payload.displayName,
        locale=payload.locale,
    )
    return profile


@router.get("/progression", response_model=ProgressionOut, summary="Get the caller's progression")
def get_my_progression(
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> ProgressionOut:
    progression = players.get_progression(session, profile.id)
    if progression is None:
        raise HTTPException(status_code=404, detail="player_progression_not_found")
    return progression


@router.get(
    "/achievements",
    response_model=Page[AchievementAwardOut],
    summary="List the caller's achievement awards",
)
def list_my_achievements(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> Page[AchievementAwardOut]:
    items, total = players.list_achievement_awards(session, profile.id, limit=limit, offset=offset)
    return Page[AchievementAwardOut](items=items, limit=limit, offset=offset, total=total)

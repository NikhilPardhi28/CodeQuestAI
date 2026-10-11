from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import PlayerProfile
from BackendAPI.app.db.session import get_db
from BackendAPI.app.schemas import ChallengeOut, Page, SubmissionMetadataOut
from BackendAPI.app.security import get_current_profile
from BackendAPI.app.services import catalog, players

router = APIRouter(tags=["challenges"])


@router.get(
    "/challenges",
    response_model=Page[ChallengeOut],
    summary="List published coding challenge definitions",
)
def list_challenges(
    objective_slug: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> Page[ChallengeOut]:
    items, total = catalog.list_challenges(
        session, limit=limit, offset=offset, objective_slug=objective_slug
    )
    return Page[ChallengeOut](items=items, limit=limit, offset=offset, total=total)


@router.get(
    "/challenges/{slug}",
    response_model=ChallengeOut,
    summary="Get a published coding challenge definition",
)
def get_challenge(slug: str, session: Session = Depends(get_db)) -> ChallengeOut:
    challenge = catalog.get_challenge(session, slug)
    if challenge is None:
        raise HTTPException(status_code=404, detail="challenge_not_found")
    return challenge


@router.get(
    "/me/submissions",
    response_model=Page[SubmissionMetadataOut],
    summary="List the caller's submission metadata",
)
def list_my_submissions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> Page[SubmissionMetadataOut]:
    items, total = players.list_submissions(session, profile.id, limit=limit, offset=offset)
    return Page[SubmissionMetadataOut](items=items, limit=limit, offset=offset, total=total)

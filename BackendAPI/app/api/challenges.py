from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from BackendAPI.app.config import get_settings
from BackendAPI.app.db.models import PlayerProfile
from BackendAPI.app.db.session import SessionLocal, get_db
from BackendAPI.app.schemas import (
    ChallengeHintOut,
    ChallengeOut,
    ChallengeSubmissionRequest,
    Page,
    SubmissionMetadataOut,
    SubmissionOut,
)
from BackendAPI.app.security import get_current_profile
from BackendAPI.app.services import catalog, players, submissions

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
    "/challenges/{slug}/versions/{version}",
    response_model=ChallengeOut,
    summary="Get an exact published challenge version",
)
def get_challenge_version(
    slug: str, version: int = Path(ge=1), session: Session = Depends(get_db)
) -> ChallengeOut:
    from BackendAPI.app.db.models import CodingChallengeDefinition

    challenge = session.get(CodingChallengeDefinition, (slug, version))
    if challenge is None or not challenge.is_published:
        raise HTTPException(status_code=404, detail="challenge_version_not_found")
    return challenge


@router.get(
    "/challenges/{slug}/hints",
    response_model=ChallengeHintOut,
    summary="Unlock the next progressive challenge hint",
)
def get_challenge_hint(
    slug: str,
    version: int = Query(ge=1),
    level: int = Query(ge=1, le=10),
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> ChallengeHintOut:
    return ChallengeHintOut(
        **submissions.get_progressive_hint(session, profile.id, slug, version, level)
    )


@router.post(
    "/challenges/{slug}/submissions",
    response_model=SubmissionOut,
    status_code=202,
    summary="Queue an authenticated Python challenge submission",
)
def post_submission(
    slug: str,
    payload: ChallengeSubmissionRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> SubmissionOut:
    settings = get_settings()
    if not settings.evaluation_worker_url or not settings.evaluation_worker_token:
        from BackendAPI.app.services.submissions import SubmissionError

        raise SubmissionError(
            503,
            "evaluation_worker_unavailable",
            "Challenge evaluation is not available in this environment.",
        )
    record, replayed = submissions.create_submission(
        session, profile, slug, payload, queue_limit=settings.evaluation_queue_limit
    )
    if replayed:
        response.status_code = 200
    if (
        settings.evaluation_worker_url
        and settings.evaluation_worker_token
        and record.status == "queued"
    ):
        background_tasks.add_task(
            submissions.dispatch_to_worker,
            SessionLocal,
            record.id,
            settings.evaluation_worker_url,
            settings.evaluation_worker_token.get_secret_value(),
        )
    return SubmissionOut.model_validate(record)


@router.get(
    "/me/submissions/{submission_id}",
    response_model=SubmissionOut,
    summary="Get the caller's permitted challenge evaluation result",
)
def get_my_submission(
    submission_id: UUID,
    profile: PlayerProfile = Depends(get_current_profile),
    session: Session = Depends(get_db),
) -> SubmissionOut:
    record = submissions.get_owned_submission(session, profile.id, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="submission_not_found")
    return SubmissionOut.model_validate(record)


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

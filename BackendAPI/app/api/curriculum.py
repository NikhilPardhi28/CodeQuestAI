from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from BackendAPI.app.db.session import get_db
from BackendAPI.app.schemas import ObjectiveOut, Page, RegionOut
from BackendAPI.app.services import catalog

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/regions", response_model=Page[RegionOut], summary="List published curriculum regions")
def list_regions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> Page[RegionOut]:
    items, total = catalog.list_regions(session, limit=limit, offset=offset)
    return Page[RegionOut](items=items, limit=limit, offset=offset, total=total)


@router.get(
    "/regions/{slug}", response_model=RegionOut, summary="Get a published curriculum region"
)
def get_region(slug: str, session: Session = Depends(get_db)) -> RegionOut:
    region = catalog.get_region(session, slug)
    if region is None:
        raise HTTPException(status_code=404, detail="region_not_found")
    return region


@router.get(
    "/objectives", response_model=Page[ObjectiveOut], summary="List published learning objectives"
)
def list_objectives(
    region_slug: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> Page[ObjectiveOut]:
    items, total = catalog.list_objectives(
        session, limit=limit, offset=offset, region_slug=region_slug
    )
    return Page[ObjectiveOut](items=items, limit=limit, offset=offset, total=total)


@router.get(
    "/objectives/{slug}", response_model=ObjectiveOut, summary="Get a published learning objective"
)
def get_objective(slug: str, session: Session = Depends(get_db)) -> ObjectiveOut:
    objective = catalog.get_objective(session, slug)
    if objective is None:
        raise HTTPException(status_code=404, detail="learning_objective_not_found")
    return objective

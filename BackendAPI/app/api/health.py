import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from BackendAPI.app.db.session import get_db
from BackendAPI.app.schemas import HealthOut, ReadinessOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthOut, summary="Process liveness")
def health() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/readyz", response_model=ReadinessOut, summary="Dependency readiness")
def readiness(session: Session = Depends(get_db)) -> ReadinessOut:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        session.rollback()
        logger.warning("database readiness check failed")
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return ReadinessOut(status="ready", checks={"database": "ok"})

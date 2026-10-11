from __future__ import annotations

import json
import logging
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from BackendAPI.app.api.health import router as health_router
from BackendAPI.app.api.router import api_v1, api_v2
from BackendAPI.app.schemas import ApiError
from BackendAPI.app.services.quest_events import QuestEventError

logger = logging.getLogger("codequest.api")
ERROR_RESPONSES = {
    400: {"model": ApiError, "description": "Invalid request"},
    401: {"model": ApiError, "description": "Authentication required or invalid"},
    404: {"model": ApiError, "description": "Resource not found"},
    409: {"model": ApiError, "description": "State conflict"},
    422: {"model": ApiError, "description": "Request validation failed"},
    500: {"model": ApiError, "description": "Unexpected server error"},
    503: {"model": ApiError, "description": "A required dependency is unavailable"},
}


def create_app() -> FastAPI:
    app = FastAPI(
        title="CodeQuest AI Backend API",
        version="0.1.0",
        description=(
            "Versioned CodeQuest AI backend contracts. Learner-owned routes require a valid "
            "OIDC bearer token; challenge execution is not provided by this API yet."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        responses=ERROR_RESPONSES,
    )
    app.include_router(health_router)
    app.include_router(api_v1)
    app.include_router(api_v2)

    @app.middleware("http")
    async def correlate_request(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        try:
            correlation_id = str(uuid4()) if not supplied else str(UUID(supplied))
        except ValueError:
            correlation_id = str(uuid4())
        request.state.correlation_id = correlation_id
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        logger.info(
            json.dumps(
                {
                    "event": "request_complete",
                    "correlationId": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "statusCode": response.status_code,
                    "durationMs": round((perf_counter() - started) * 1000, 2),
                },
                separators=(",", ":"),
            )
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "request_failed"
        mapped = {
            "authentication_required": ("authentication_required", "Authentication is required."),
            "authentication_not_configured": (
                "authentication_not_configured",
                "Authentication is not configured for this deployment.",
            ),
            "invalid_bearer_token": ("invalid_bearer_token", "The bearer token is invalid."),
            "invalid_bearer_subject": ("invalid_bearer_token", "The bearer token is invalid."),
            "identity_provider_unavailable": (
                "identity_provider_unavailable",
                "The identity provider is temporarily unavailable.",
            ),
            "database_unavailable": (
                "database_unavailable",
                "The database is temporarily unavailable.",
            ),
            "region_not_found": ("region_not_found", "The requested region was not found."),
            "learning_objective_not_found": (
                "learning_objective_not_found",
                "The requested learning objective was not found.",
            ),
            "quest_not_found": ("quest_not_found", "The requested quest was not found."),
            "quest_version_not_found": (
                "quest_version_not_found",
                "The requested published quest version was not found.",
            ),
            "challenge_not_found": (
                "challenge_not_found",
                "The requested challenge was not found.",
            ),
            "player_profile_not_found": (
                "player_profile_not_found",
                "The player profile was not found.",
            ),
            "player_progression_not_found": (
                "player_progression_not_found",
                "Player progression was not found.",
            ),
        }
        code, message = mapped.get(
            detail, ("request_failed", "The request could not be completed.")
        )
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content=error_payload(request, code, message, retryable=exc.status_code == 503),
        )

    @app.exception_handler(QuestEventError)
    async def quest_event_error(request: Request, exc: QuestEventError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                **error_payload(request, exc.code, exc.message, retryable=exc.status_code >= 500),
                "currentState": exc.current_state,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = [
            ".".join(str(part) for part in error.get("loc", ()) if part != "body")
            for error in exc.errors()
        ]
        message = "Request validation failed."
        if fields:
            message += " Invalid fields: " + ", ".join(sorted(set(fields))) + "."
        return JSONResponse(
            status_code=422,
            content=error_payload(request, "request_validation_error", message),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, _exc: IntegrityError):
        return JSONResponse(
            status_code=409,
            content=error_payload(
                request, "persistence_conflict", "The requested change conflicts with stored data."
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error(
            json.dumps(
                {
                    "event": "database_operation_failed",
                    "correlationId": correlation_id(request),
                    "errorType": type(exc).__name__,
                },
                separators=(",", ":"),
            )
        )
        return JSONResponse(
            status_code=503,
            content=error_payload(
                request, "database_unavailable", "The database is temporarily unavailable.", True
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error(
            json.dumps(
                {
                    "event": "unexpected_request_failure",
                    "correlationId": correlation_id(request),
                    "errorType": type(exc).__name__,
                },
                separators=(",", ":"),
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(request, "internal_error", "An unexpected error occurred."),
        )

    return app


def correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def error_payload(
    request: Request, code: str, message: str, retryable: bool = False
) -> dict[str, object]:
    return {
        "code": code,
        "message": message,
        "retryable": retryable,
        "correlationId": correlation_id(request),
    }


app = create_app()

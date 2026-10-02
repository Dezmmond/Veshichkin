from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from veshichkin.core.errors import ApplicationError, ErrorResponse
from veshichkin.db.session import get_session
from veshichkin.health.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
def ready(session: Annotated[Session, Depends(get_session)]) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ApplicationError(
            code="database_unavailable",
            message="Database is unavailable",
            status_code=503,
        ) from exc
    return HealthResponse()

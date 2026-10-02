import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.core.errors import ApplicationError, ErrorResponse
from veshichkin.db.session import get_session
from veshichkin.profile import operations
from veshichkin.profile.schemas import MeasurementProfilePatch, MeasurementProfileResponse

router = APIRouter(prefix="/profile/measurements", tags=["profile"])
DatabaseSession = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)


@router.get("", response_model=MeasurementProfileResponse | None)
def get_measurements(session: DatabaseSession) -> MeasurementProfileResponse | None:
    profile = operations.get_measurements(session)
    return MeasurementProfileResponse.model_validate(profile) if profile is not None else None


@router.patch(
    "", response_model=MeasurementProfileResponse, responses={500: {"model": ErrorResponse}}
)
def patch_measurements(
    payload: MeasurementProfilePatch, session: DatabaseSession
) -> MeasurementProfileResponse:
    try:
        profile = operations.patch_measurements(session, payload)
        result = MeasurementProfileResponse.model_validate(profile)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        logger.exception("Unexpected integrity error writing measurement profile")
        raise ApplicationError(
            "profile_write_failed", "Unable to save measurement profile", 500
        ) from exc
    return result

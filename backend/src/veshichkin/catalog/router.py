import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.catalog import operations
from veshichkin.catalog.schemas import ItemCreate, ItemPatch, ItemResponse, TrackingMode
from veshichkin.core.errors import ApplicationError, ErrorResponse
from veshichkin.db.session import get_session

router = APIRouter(prefix="/items", tags=["items"])
DatabaseSession = Annotated[Session, Depends(get_session)]
FilterId = Annotated[int | None, Query(gt=0)]
logger = logging.getLogger(__name__)
ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get("", response_model=list[ItemResponse])
def list_items(
    session: DatabaseSession,
    category_id: FilterId = None,
    condition_id: FilterId = None,
    purpose_id: FilterId = None,
    climate_id: FilterId = None,
    tracking_mode: TrackingMode | None = None,
) -> list[ItemResponse]:
    items = operations.list_items(
        session, category_id, condition_id, purpose_id, climate_id, tracking_mode
    )
    return operations.item_responses(session, items)


@router.get("/{item_id}", response_model=ItemResponse, responses={404: {"model": ErrorResponse}})
def get_item(item_id: int, session: DatabaseSession) -> ItemResponse:
    return operations.item_responses(session, [operations.get_item(session, item_id)])[0]


@router.post("", response_model=ItemResponse, status_code=201, responses=ERRORS)
def create_item(payload: ItemCreate, session: DatabaseSession) -> ItemResponse:
    try:
        item = operations.create_item(session, payload)
        result = operations.item_responses(session, [item])[0]
        session.commit()
    except ApplicationError:
        session.rollback()
        raise
    except IntegrityError as exc:
        session.rollback()
        logger.exception("Unexpected integrity error creating item")
        raise ApplicationError("item_write_failed", "Unable to save item", 500) from exc
    return result


@router.patch("/{item_id}", response_model=ItemResponse, responses=ERRORS)
def patch_item(item_id: int, payload: ItemPatch, session: DatabaseSession) -> ItemResponse:
    try:
        item = operations.patch_item(session, item_id, payload)
        result = operations.item_responses(session, [item])[0]
        session.commit()
    except (ApplicationError, RequestValidationError):
        session.rollback()
        raise
    except IntegrityError as exc:
        session.rollback()
        logger.exception("Unexpected integrity error updating item")
        raise ApplicationError("item_write_failed", "Unable to save item", 500) from exc
    return result


@router.delete("/{item_id}", status_code=204, responses=ERRORS)
def remove_item(item_id: int, session: DatabaseSession) -> Response:
    try:
        operations.remove_item(session, item_id)
        session.commit()
    except ApplicationError:
        session.rollback()
        raise
    except IntegrityError as exc:
        session.rollback()
        logger.exception("Unexpected integrity error removing item")
        raise ApplicationError("item_write_failed", "Unable to save item", 500) from exc
    return Response(status_code=204)

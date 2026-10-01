import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.catalog import operations
from veshichkin.catalog.schemas import ItemCreate, ItemPatch, ItemResponse
from veshichkin.core.errors import ApplicationError, ErrorResponse
from veshichkin.db.session import get_session

router = APIRouter(prefix="/items", tags=["items"])
DatabaseSession = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)
ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.get("", response_model=list[ItemResponse])
def list_items(session: DatabaseSession) -> list[ItemResponse]:
    return [ItemResponse.model_validate(item) for item in operations.list_items(session)]


@router.get("/{item_id}", response_model=ItemResponse, responses={404: {"model": ErrorResponse}})
def get_item(item_id: int, session: DatabaseSession) -> ItemResponse:
    return ItemResponse.model_validate(operations.get_item(session, item_id))


@router.post("", response_model=ItemResponse, status_code=201, responses=ERRORS)
def create_item(payload: ItemCreate, session: DatabaseSession) -> ItemResponse:
    try:
        item = operations.create_item(session, payload)
        result = ItemResponse.model_validate(item)
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
        result = ItemResponse.model_validate(item)
        session.commit()
    except (ApplicationError, RequestValidationError):
        session.rollback()
        raise
    except IntegrityError as exc:
        session.rollback()
        logger.exception("Unexpected integrity error updating item")
        raise ApplicationError("item_write_failed", "Unable to save item", 500) from exc
    return result

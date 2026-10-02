from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.categories import operations
from veshichkin.categories.schemas import (
    CategoryCreate,
    CategoryPatch,
    CategoryResponse,
    CategoryTree,
)
from veshichkin.core.errors import ApplicationError, ErrorResponse
from veshichkin.db.session import get_session

router = APIRouter(prefix="/categories", tags=["categories"])
DatabaseSession = Annotated[Session, Depends(get_session)]
ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get("", response_model=list[CategoryTree])
def list_categories(session: DatabaseSession) -> list[CategoryTree]:
    return operations.list_categories(session)


@router.post("", response_model=CategoryResponse, status_code=201, responses=ERRORS)
def create_category(payload: CategoryCreate, session: DatabaseSession) -> CategoryResponse:
    try:
        category = operations.create_category(session, payload)
        result = CategoryResponse.model_validate(category)
        session.commit()
    except ApplicationError:
        session.rollback()
        raise
    return result


@router.patch("/{category_id}", response_model=CategoryResponse, responses=ERRORS)
def patch_category(
    category_id: int, payload: CategoryPatch, session: DatabaseSession
) -> CategoryResponse:
    try:
        category = operations.patch_category(session, category_id, payload)
        result = CategoryResponse.model_validate(category)
        session.commit()
    except ApplicationError:
        session.rollback()
        raise
    return result


@router.delete("/{category_id}", status_code=204, responses=ERRORS)
def delete_category(category_id: int, session: DatabaseSession) -> Response:
    try:
        operations.delete_category(session, category_id)
        session.commit()
    except ApplicationError:
        session.rollback()
        raise
    except IntegrityError as exc:
        session.rollback()
        raise ApplicationError("category_in_use", "Category is in use", 409) from exc
    return Response(status_code=204)

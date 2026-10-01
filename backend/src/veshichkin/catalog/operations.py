from collections.abc import Sequence

from fastapi.exceptions import RequestValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from veshichkin.catalog.schemas import ItemCreate, ItemPatch
from veshichkin.core.errors import ApplicationError
from veshichkin.db.models import Category, Condition, Item


def list_items(session: Session) -> Sequence[Item]:
    return session.scalars(
        select(Item).where(Item.is_active.is_(True)).order_by(Item.name, Item.id)
    ).all()


def get_item(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id) if -(2**63) <= item_id < 2**63 else None
    if item is None:
        raise ApplicationError("item_not_found", "Item not found", 404)
    return item


def check_references(session: Session, category_id: int | None, condition_id: int | None) -> None:
    if category_id is not None and (
        not -(2**63) <= category_id < 2**63 or session.get(Category, category_id) is None
    ):
        raise ApplicationError("category_not_found", "Category not found", 404)
    if condition_id is not None and (
        not -(2**15) <= condition_id < 2**15 or session.get(Condition, condition_id) is None
    ):
        raise ApplicationError("condition_not_found", "Condition not found", 404)


def create_item(session: Session, payload: ItemCreate) -> Item:
    check_references(session, payload.category_id, payload.condition_id)
    item = Item(**payload.model_dump(), is_active=True)
    session.add(item)
    session.flush()
    return item


def patch_item(session: Session, item_id: int, payload: ItemPatch) -> Item:
    item = get_item(session, item_id)
    if (
        "quantity" in payload.model_fields_set
        and item.tracking_mode == "individual"
        and payload.quantity != 1
    ):
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "quantity"),
                    "msg": "individual quantity must be 1",
                    "input": payload.quantity,
                }
            ]
        )
    check_references(session, payload.category_id, payload.condition_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.flush()
    return item

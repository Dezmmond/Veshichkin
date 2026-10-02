from collections.abc import Sequence

from fastapi.exceptions import RequestValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from veshichkin.catalog.schemas import ItemCreate, ItemPatch, ItemResponse, TrackingMode
from veshichkin.core.errors import ApplicationError
from veshichkin.db.models import (
    Category,
    Climate,
    Condition,
    Item,
    ItemClimate,
    ItemPurpose,
    Purpose,
)


def list_items(
    session: Session,
    category_id: int | None = None,
    condition_id: int | None = None,
    purpose_id: int | None = None,
    climate_id: int | None = None,
    tracking_mode: TrackingMode | None = None,
) -> Sequence[Item]:
    # Positive IDs outside their existing DB types cannot match any rows.
    if category_id is not None and category_id >= 2**63:
        return []
    if any(
        value is not None and value >= 2**15 for value in (condition_id, purpose_id, climate_id)
    ):
        return []
    query = select(Item).where(Item.is_active.is_(True))
    if category_id is not None:
        query = query.where(Item.category_id == category_id)
    if condition_id is not None:
        query = query.where(Item.condition_id == condition_id)
    if tracking_mode is not None:
        query = query.where(Item.tracking_mode == tracking_mode)
    if purpose_id is not None:
        query = query.where(
            select(ItemPurpose.item_id)
            .where(ItemPurpose.item_id == Item.id, ItemPurpose.purpose_id == purpose_id)
            .exists()
        )
    if climate_id is not None:
        query = query.where(
            select(ItemClimate.item_id)
            .where(ItemClimate.item_id == Item.id, ItemClimate.climate_id == climate_id)
            .exists()
        )
    return session.scalars(query.order_by(Item.name, Item.id)).all()


def item_responses(session: Session, items: Sequence[Item]) -> list[ItemResponse]:
    if not items:
        return []
    ids = [item.id for item in items]
    purposes: dict[int, list[int]] = {}
    climates: dict[int, list[int]] = {}
    for item_id, purpose_id in session.execute(
        select(ItemPurpose.item_id, ItemPurpose.purpose_id)
        .where(ItemPurpose.item_id.in_(ids))
        .order_by(ItemPurpose.purpose_id)
    ):
        purposes.setdefault(item_id, []).append(purpose_id)
    for item_id, climate_id in session.execute(
        select(ItemClimate.item_id, ItemClimate.climate_id)
        .where(ItemClimate.item_id.in_(ids))
        .order_by(ItemClimate.climate_id)
    ):
        climates.setdefault(item_id, []).append(climate_id)
    return [
        ItemResponse.model_validate(item).model_copy(
            update={
                "purpose_ids": purposes.get(item.id, []),
                "climate_ids": climates.get(item.id, []),
            }
        )
        for item in items
    ]


def check_relation_references(
    session: Session, purpose_ids: list[int], climate_ids: list[int]
) -> None:
    for model, ids, code, message in (
        (Purpose, purpose_ids, "purpose_not_found", "Purpose not found"),
        (Climate, climate_ids, "climate_not_found", "Climate not found"),
    ):
        if not ids:
            continue
        if any(value >= 2**15 for value in ids):
            raise ApplicationError(code, message, 404)
        found = set(session.scalars(select(model.id).where(model.id.in_(ids))))
        if found != set(ids):
            raise ApplicationError(code, message, 404)


def replace_relations(
    session: Session,
    item_id: int,
    purpose_ids: list[int] | None,
    climate_ids: list[int] | None,
) -> None:
    if purpose_ids is not None:
        session.execute(delete(ItemPurpose).where(ItemPurpose.item_id == item_id))
        session.add_all(ItemPurpose(item_id=item_id, purpose_id=value) for value in purpose_ids)
    if climate_ids is not None:
        session.execute(delete(ItemClimate).where(ItemClimate.item_id == item_id))
        session.add_all(ItemClimate(item_id=item_id, climate_id=value) for value in climate_ids)


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
    check_relation_references(session, payload.purpose_ids, payload.climate_ids)
    item = Item(**payload.model_dump(exclude={"purpose_ids", "climate_ids"}), is_active=True)
    session.add(item)
    session.flush()
    replace_relations(session, item.id, payload.purpose_ids, payload.climate_ids)
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
    check_relation_references(session, payload.purpose_ids, payload.climate_ids)
    for field, value in payload.model_dump(
        exclude_unset=True, exclude={"purpose_ids", "climate_ids"}
    ).items():
        setattr(item, field, value)
    replace_relations(
        session,
        item.id,
        payload.purpose_ids if "purpose_ids" in payload.model_fields_set else None,
        payload.climate_ids if "climate_ids" in payload.model_fields_set else None,
    )
    session.flush()
    return item


def remove_item(session: Session, item_id: int) -> None:
    item = get_item(session, item_id)
    if item.is_active:
        # Suppress the model's onupdate default: removal preserves both timestamps.
        session.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(is_active=False, updated_at=Item.updated_at)
        )
    session.flush()

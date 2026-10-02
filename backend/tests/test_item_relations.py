import pytest
from pydantic import ValidationError

from veshichkin.catalog.schemas import ItemCreate, ItemPatch


@pytest.mark.parametrize("schema", [ItemCreate, ItemPatch])
@pytest.mark.parametrize("field", ["purpose_ids", "climate_ids"])
@pytest.mark.parametrize("value", [None, [0], [-1], [1, 1], [True], [1.0], ["1"], "1", {}])
def test_relation_dto_validation(schema: type, field: str, value: object) -> None:
    payload = {field: value}
    if schema is ItemCreate:
        payload.update(name="Item", category_id=1, condition_id=1, tracking_mode="individual")
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_relation_defaults_presence_and_input_order() -> None:
    created = ItemCreate(name="Item", category_id=1, condition_id=1, tracking_mode="individual")
    assert created.purpose_ids == [] and created.climate_ids == []
    assert ItemPatch().model_dump(exclude_unset=True) == {}
    assert ItemPatch(purpose_ids=[]).model_dump(exclude_unset=True) == {"purpose_ids": []}
    patched = ItemPatch(purpose_ids=[3, 1], climate_ids=[2])
    assert patched.purpose_ids == [3, 1] and patched.climate_ids == [2]

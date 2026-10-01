from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.catalog.schemas import ItemCreate, ItemPatch
from veshichkin.db.models import Item
from veshichkin.db.session import get_session
from veshichkin.main import create_app

BASE = {"name": "  Item  ", "category_id": 1, "condition_id": 1}


@pytest.mark.parametrize(
    "mode,quantity",
    [("individual", None), ("individual", 1), ("grouped", 0), ("grouped", 1), ("grouped", 12)],
)
def test_create_quantity_defaults(mode: str, quantity: int | None) -> None:
    payload = {**BASE, "tracking_mode": mode}
    if quantity is not None:
        payload["quantity"] = quantity
    result = ItemCreate.model_validate(payload)
    assert result.quantity == (1 if quantity is None else quantity)
    assert result.name == "Item"
    assert result.extra_attributes == {}
    assert result.brand is None


INVALID = [
    {"tracking_mode": "individual", "quantity": 0},
    {"tracking_mode": "individual", "quantity": 2},
    {"tracking_mode": "grouped"},
    {"tracking_mode": "grouped", "quantity": -1},
    {"tracking_mode": "grouped", "quantity": 1.0},
    {"tracking_mode": "grouped", "quantity": True},
    {"tracking_mode": "grouped", "quantity": "2"},
    {"tracking_mode": "grouped", "quantity": 2147483648},
    {"tracking_mode": "individual", "quantity": None},
    {"name": " \t "},
    {"tracking_mode": "unknown"},
    {"extra_attributes": None},
    {"extra_attributes": []},
    {"category_id": None},
    {"condition_id": None},
    {"is_active": False},
]


@pytest.mark.parametrize("changes", INVALID)
def test_create_invalid_dto(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ItemCreate.model_validate({**BASE, "tracking_mode": "individual", **changes})


@pytest.mark.parametrize(
    "field", ["name", "category_id", "condition_id", "quantity", "extra_attributes"]
)
def test_patch_rejects_null(field: str) -> None:
    with pytest.raises(ValidationError):
        ItemPatch.model_validate({field: None})


@pytest.mark.parametrize("field", ["tracking_mode", "is_active", "purposes", "climates"])
def test_patch_rejects_unsupported_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        ItemPatch.model_validate({field: "individual"})


def test_optional_scalars_and_json_object() -> None:
    attributes = {"waterproof": True, "volume_l": 35, "nested": {"values": [None, 2]}}
    result = ItemCreate.model_validate(
        {
            **BASE,
            "tracking_mode": "individual",
            "brand": "  Brand ",
            "notes": "  ",
            "extra_attributes": attributes,
        }
    )
    assert result.brand == "Brand" and result.notes is None
    assert result.extra_attributes == attributes
    assert ItemPatch().model_dump(exclude_unset=True) == {}
    assert ItemPatch(brand=None).model_dump(exclude_unset=True) == {"brand": None}


@pytest.fixture
def mock_client() -> Iterator[tuple[TestClient, Mock]]:
    session = Mock(spec=Session)
    now = datetime.now(UTC)
    row = Item(
        id=1,
        name="Item",
        category_id=1,
        condition_id=1,
        tracking_mode="individual",
        quantity=1,
        extra_attributes={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.get.return_value = row
    session.execute.return_value = []
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client, session


@pytest.mark.parametrize("changes", INVALID)
def test_create_invalid_payload_is_422(
    mock_client: tuple[TestClient, Mock], changes: dict[str, object]
) -> None:
    client, session = mock_client
    response = client.post("/api/items", json={**BASE, "tracking_mode": "individual", **changes})
    assert response.status_code == 422
    session.flush.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "method,phase", [("post", "flush"), ("post", "commit"), ("patch", "flush"), ("patch", "commit")]
)
def test_unexpected_integrity_error_is_safe(
    mock_client: tuple[TestClient, Mock], monkeypatch: pytest.MonkeyPatch, method: str, phase: str
) -> None:
    client, session = mock_client
    # Return a complete DTO even when mocking the insert/flush path.
    if method == "post":
        monkeypatch.setattr(
            "veshichkin.catalog.operations.create_item",
            lambda session, payload: session.get(Item, 1),
        )
        if phase == "flush":

            def fail_create(session: Session, payload: ItemCreate) -> Item:
                session.flush()
                return session.get(Item, 1)

            monkeypatch.setattr("veshichkin.catalog.operations.create_item", fail_create)
    getattr(session, phase).side_effect = IntegrityError("secret SQL", {}, Exception("constraint"))
    response = client.request(
        method,
        "/api/items" if method == "post" else "/api/items/1",
        json={**BASE, "tracking_mode": "individual"} if method == "post" else {"name": "Updated"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "item_write_failed"
    assert "secret" not in response.text and "constraint" not in response.text
    session.rollback.assert_called_once()


def test_openapi_item_contract() -> None:
    schema = create_app().openapi()
    assert set(schema["paths"]["/api/items"]) == {"get", "post"}
    assert set(schema["paths"]["/api/items/{item_id}"]) == {"get", "patch", "delete"}
    patch = schema["components"]["schemas"]["ItemPatch"]["properties"]
    assert not {"tracking_mode", "is_active", "purposes", "climates"} & patch.keys()
    parameters = schema["paths"]["/api/items"]["get"]["parameters"]
    assert {parameter["name"] for parameter in parameters} == {
        "category_id",
        "condition_id",
        "purpose_id",
        "climate_id",
        "tracking_mode",
    }
    for name in ("ItemCreate", "ItemPatch", "ItemResponse"):
        assert {"purpose_ids", "climate_ids"} <= schema["components"]["schemas"][name][
            "properties"
        ].keys()

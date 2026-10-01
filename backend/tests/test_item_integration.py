from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from tests.test_category_reference_integration import test_engine as test_engine
from veshichkin.db.models import Category, Condition, Item
from veshichkin.db.session import get_session
from veshichkin.main import create_app

SCALARS = ("brand", "model", "color", "size", "material", "notes")
MISSING = 9223372036854775807


@pytest.fixture
def catalog_client(test_engine: Engine) -> Iterator[tuple[TestClient, Engine, dict[str, int]]]:
    with Session(test_engine) as session:
        categories = [Category(name="Item test category"), Category(name="Other item category")]
        session.add_all(categories)
        session.commit()
        category_ids = [row.id for row in categories]
        conditions = list(session.scalars(select(Condition.id).order_by(Condition.rank).limit(2)))
        refs = {
            "category_id": category_ids[0],
            "other_category": category_ids[1],
            "condition_id": conditions[0],
            "other_condition": conditions[1],
        }
    app = create_app()

    def request_session() -> Iterator[Session]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = request_session
    try:
        with TestClient(app) as client:
            yield client, test_engine, refs
    finally:
        with Session(test_engine) as session:
            session.execute(delete(Item).where(Item.category_id.in_(category_ids)))
            session.execute(delete(Category).where(Category.id.in_(category_ids)))
            session.commit()


def create(client: TestClient, refs: dict[str, int], **changes: object) -> dict:
    payload = {
        "name": "  Item  ",
        "category_id": refs["category_id"],
        "condition_id": refs["condition_id"],
        "tracking_mode": "individual",
        **changes,
    }
    response = client.post("/api/items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    "mode,quantity",
    [("individual", None), ("individual", 1), ("grouped", 0), ("grouped", 1), ("grouped", 8)],
)
def test_create_commits_and_persists(
    catalog_client: tuple, mode: str, quantity: int | None
) -> None:
    client, engine, refs = catalog_client
    fields = {field: f"  {field} value  " for field in SCALARS}
    attributes = {"waterproof": True, "volume_l": 35, "nested": {"values": [None, 2]}}
    payload = {**fields, "tracking_mode": mode, "extra_attributes": attributes}
    if quantity is not None:
        payload["quantity"] = quantity
    data = create(client, refs, **payload)
    assert data["name"] == "Item" and data["is_active"] is True
    assert data["quantity"] == (1 if quantity is None else quantity)
    assert set(data) == {
        "id",
        "category_id",
        "condition_id",
        "name",
        "tracking_mode",
        "quantity",
        *SCALARS,
        "extra_attributes",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert data["created_at"] and data["updated_at"]
    with Session(engine) as fresh:
        row = fresh.get(Item, data["id"])
        assert row is not None and row.quantity == data["quantity"]
        assert row.is_active and row.extra_attributes == attributes
        for field in SCALARS:
            assert getattr(row, field) == f"{field} value"


def test_defaults_and_duplicate_names(catalog_client: tuple) -> None:
    client, engine, refs = catalog_client
    first = create(client, refs)
    second = create(client, refs)
    assert first["id"] != second["id"]
    assert first["extra_attributes"] == {}
    assert all(first[field] is None for field in SCALARS)
    with Session(engine) as fresh:
        assert fresh.get(Item, first["id"]).extra_attributes == {}


@pytest.mark.parametrize("missing_id", [32767, MISSING, 2**63])
@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize(
    "field,code", [("category_id", "category_not_found"), ("condition_id", "condition_not_found")]
)
def test_missing_references(
    catalog_client: tuple, method: str, field: str, code: str, missing_id: int
) -> None:
    client, engine, refs = catalog_client
    original = create(client, refs)
    path = "/api/items" if method == "post" else f"/api/items/{original['id']}"
    payload = {field: missing_id, "name": "Must not persist"}
    if method == "post":
        payload = {
            "tracking_mode": "individual",
            "category_id": refs["category_id"],
            "condition_id": refs["condition_id"],
            **payload,
        }
    response = client.request(method, path, json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == code
    with Session(engine) as fresh:
        assert fresh.get(Item, original["id"]).name == "Item"
        assert (
            len(fresh.scalars(select(Item).where(Item.category_id == refs["category_id"])).all())
            == 1
        )


def test_list_active_only_order_and_get_inactive(catalog_client: tuple) -> None:
    client, engine, refs = catalog_client
    b = create(client, refs, name="B")
    a1 = create(client, refs, name="A")
    a2 = create(client, refs, name="A")
    with Session(engine) as session:
        inactive = Item(
            name="Hidden",
            category_id=refs["category_id"],
            condition_id=refs["condition_id"],
            tracking_mode="individual",
            quantity=1,
            is_active=False,
        )
        session.add(inactive)
        session.commit()
        inactive_id = inactive.id
    response = client.get("/api/items")
    assert response.status_code == 200
    data = response.json()
    assert data == sorted(data, key=lambda row: (row["name"], row["id"]))
    assert [row["id"] for row in data] == [a1["id"], a2["id"], b["id"]]
    assert client.get(f"/api/items/{a1['id']}").json() == a1
    hidden = client.get(f"/api/items/{inactive_id}")
    assert hidden.status_code == 200 and hidden.json()["is_active"] is False


@pytest.mark.parametrize("missing_id", [MISSING, 2**63])
@pytest.mark.parametrize("method", ["get", "patch"])
def test_missing_item(catalog_client: tuple, method: str, missing_id: int) -> None:
    client, _, _ = catalog_client
    response = client.request(
        method, f"/api/items/{missing_id}", json={} if method == "patch" else None
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "item_not_found"


def test_patch_fields_omission_and_json_replacement(catalog_client: tuple) -> None:
    client, engine, refs = catalog_client
    row = create(
        client,
        refs,
        tracking_mode="grouped",
        quantity=3,
        **{field: "original" for field in SCALARS},
        extra_attributes={"old": {"x": 1}},
    )
    path = f"/api/items/{row['id']}"
    renamed = client.patch(path, json={"name": "  Renamed  "})
    assert renamed.status_code == 200
    assert renamed.json() == {**row, "name": "Renamed", "updated_at": renamed.json()["updated_at"]}
    assert client.patch(path, json={}).json() == renamed.json()
    attributes = {"new": True}
    payload = {
        "category_id": refs["other_category"],
        "condition_id": refs["other_condition"],
        "quantity": 0,
        "extra_attributes": attributes,
        **{field: None for field in SCALARS},
    }
    response = client.patch(path, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert all(data[field] is None for field in SCALARS)
    assert data["extra_attributes"] == attributes
    with Session(engine) as fresh:
        stored = fresh.get(Item, row["id"])
        assert stored.name == "Renamed" and stored.tracking_mode == "grouped"
        assert stored.category_id == refs["other_category"]
        assert stored.condition_id == refs["other_condition"]
        assert stored.quantity == 0 and stored.extra_attributes == attributes
        assert all(getattr(stored, field) is None for field in SCALARS)
    assert client.patch(path, json={"extra_attributes": {}}).json()["extra_attributes"] == {}


@pytest.mark.parametrize(
    "quantity,status",
    [(1, 200), (0, 422), (2, 422), (-1, 422), (None, 422), (True, 422), (1.0, 422)],
)
def test_patch_individual_quantity(catalog_client: tuple, quantity: object, status: int) -> None:
    client, engine, refs = catalog_client
    row = create(client, refs)
    response = client.patch(f"/api/items/{row['id']}", json={"quantity": quantity, "brand": "new"})
    assert response.status_code == status
    with Session(engine) as fresh:
        stored = fresh.get(Item, row["id"])
        assert stored.quantity == 1
        assert stored.brand == ("new" if status == 200 else None)


@pytest.mark.parametrize(
    "quantity,status", [(0, 200), (1, 200), (9, 200), (-1, 422), (None, 422), (2.1, 422)]
)
def test_patch_grouped_quantity(catalog_client: tuple, quantity: object, status: int) -> None:
    client, engine, refs = catalog_client
    row = create(client, refs, tracking_mode="grouped", quantity=3)
    response = client.patch(f"/api/items/{row['id']}", json={"quantity": quantity})
    assert response.status_code == status
    with Session(engine) as fresh:
        assert fresh.get(Item, row["id"]).quantity == (quantity if status == 200 else 3)


@pytest.mark.parametrize(
    "payload",
    [
        {"tracking_mode": "grouped"},
        {"is_active": False},
        {"extra_attributes": None},
        {"name": "  "},
    ],
)
def test_patch_invalid_preserves_item(catalog_client: tuple, payload: dict) -> None:
    client, _, refs = catalog_client
    row = create(client, refs)
    path = f"/api/items/{row['id']}"
    assert client.patch(path, json=payload).status_code == 422
    assert client.get(path).json() == row


def test_patch_normalizes_scalar_strings(catalog_client: tuple) -> None:
    client, _, refs = catalog_client
    row = create(client, refs)
    response = client.patch(f"/api/items/{row['id']}", json={"brand": "  Brand  ", "notes": " \t "})
    assert response.status_code == 200
    assert response.json()["brand"] == "Brand" and response.json()["notes"] is None

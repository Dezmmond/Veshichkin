from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.test_category_reference_integration import test_engine as test_engine
from tests.test_item_integration import SCALARS, create
from tests.test_item_integration import catalog_client as catalog_client
from veshichkin.catalog import operations
from veshichkin.db.models import Category, Climate, Item, ItemClimate, ItemPurpose, Purpose


@pytest.fixture
def relations(catalog_client: tuple) -> tuple[TestClient, Engine, dict[str, int]]:
    client, engine, refs = catalog_client
    with Session(engine) as session:
        purposes = list(session.scalars(select(Purpose.id).order_by(Purpose.id).limit(3)))
        climates = list(session.scalars(select(Climate.id).order_by(Climate.id).limit(3)))
        for index in range(3):
            refs[f"p{index + 1}"] = purposes[index]
            refs[f"c{index + 1}"] = climates[index]
    return client, engine, refs


def stored_relations(session: Session, item_id: int) -> tuple[list[int], list[int]]:
    return (
        list(
            session.scalars(
                select(ItemPurpose.purpose_id)
                .where(ItemPurpose.item_id == item_id)
                .order_by(ItemPurpose.purpose_id)
            )
        ),
        list(
            session.scalars(
                select(ItemClimate.climate_id)
                .where(ItemClimate.item_id == item_id)
                .order_by(ItemClimate.climate_id)
            )
        ),
    )


@pytest.mark.parametrize(
    "purposes,climates",
    [([], []), ([1], []), ([2, 1], []), ([], [1]), ([], [2, 1]), ([2, 1], [2, 1])],
)
def test_create_relations_response_and_persistence(
    relations: tuple, purposes: list[int], climates: list[int]
) -> None:
    client, engine, refs = relations
    pids = [refs[f"p{value}"] for value in purposes]
    cids = [refs[f"c{value}"] for value in climates]
    row = create(client, refs, purpose_ids=pids, climate_ids=cids)
    assert row["purpose_ids"] == sorted(pids) and row["climate_ids"] == sorted(cids)
    assert client.get(f"/api/items/{row['id']}").json() == row
    assert client.get("/api/items").json() == [row]
    with Session(engine) as fresh:
        assert stored_relations(fresh, row["id"]) == (sorted(pids), sorted(cids))


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize("field", ["purpose_ids", "climate_ids"])
@pytest.mark.parametrize("value", [None, [0], [-1], [1, 1], [True], [1.0], ["1"]])
def test_invalid_relation_payload_is_422(
    relations: tuple, method: str, field: str, value: object
) -> None:
    client, _, refs = relations
    if method == "post":
        path = "/api/items"
        payload = {
            "name": "Item",
            "category_id": refs["category_id"],
            "condition_id": refs["condition_id"],
            "tracking_mode": "individual",
        }
    else:
        row = create(client, refs)
        path = f"/api/items/{row['id']}"
        payload = {}
    response = client.request(method, path, json={**payload, field: value})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize(
    "field,code", [("purpose_ids", "purpose_not_found"), ("climate_ids", "climate_not_found")]
)
@pytest.mark.parametrize("missing", [32767, 2**63])
def test_missing_relation_rolls_back_scalar_and_relations(
    relations: tuple, method: str, field: str, code: str, missing: int
) -> None:
    client, engine, refs = relations
    original = create(client, refs, purpose_ids=[refs["p3"]], climate_ids=[refs["c3"]])
    payload = {
        "name": "Must not persist",
        "brand": "New",
        "purpose_ids": [refs["p1"]],
        "climate_ids": [refs["c1"]],
    }
    # Mix valid and missing IDs so partial validation never permits a partial write.
    payload[field] = [refs["p2"] if field == "purpose_ids" else refs["c2"], missing]
    path = f"/api/items/{original['id']}"
    if method == "post":
        path = "/api/items"
        payload.update(
            category_id=refs["category_id"],
            condition_id=refs["condition_id"],
            tracking_mode="individual",
        )
    response = client.request(method, path, json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == code
    assert client.get(f"/api/items/{original['id']}").json() == original
    with Session(engine) as fresh:
        items = fresh.scalars(select(Item).where(Item.category_id == refs["category_id"])).all()
        assert len(items) == 1 and items[0].name == "Item" and items[0].brand is None
        assert stored_relations(fresh, original["id"]) == ([refs["p3"]], [refs["c3"]])
        assert list(fresh.scalars(select(ItemPurpose.item_id))) == [original["id"]]
        assert list(fresh.scalars(select(ItemClimate.item_id))) == [original["id"]]


@pytest.mark.parametrize(
    "changes", ["purposes", "climates", "both", "clear_p", "clear_c", "clear_both", "omitted"]
)
def test_patch_replace_clear_omission(relations: tuple, changes: str) -> None:
    client, engine, refs = relations
    original = create(
        client, refs, purpose_ids=[refs["p2"], refs["p1"]], climate_ids=[refs["c2"], refs["c1"]]
    )
    expected_p, expected_c = original["purpose_ids"], original["climate_ids"]
    payload = {"name": "Renamed"}
    if changes in ("purposes", "both", "clear_p", "clear_both"):
        expected_p = [] if changes.startswith("clear") else [refs["p3"]]
        payload["purpose_ids"] = expected_p
    if changes in ("climates", "both", "clear_c", "clear_both"):
        expected_c = [] if changes.startswith("clear") else [refs["c3"]]
        payload["climate_ids"] = expected_c
    response = client.patch(f"/api/items/{original['id']}", json=payload)
    assert response.status_code == 200
    assert response.json()["purpose_ids"] == expected_p
    assert response.json()["climate_ids"] == expected_c
    with Session(engine) as fresh:
        assert fresh.get(Item, original["id"]).name == "Renamed"
        assert stored_relations(fresh, original["id"]) == (expected_p, expected_c)


@pytest.mark.parametrize("method", ["post", "patch"])
def test_integrity_error_after_relation_flush_rolls_back_everything(
    relations: tuple, method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, engine, refs = relations
    original = create(client, refs, purpose_ids=[refs["p3"]], climate_ids=[refs["c3"]])
    replace = operations.replace_relations

    def fail_after_replace(session: Session, item_id: int, pids: list | None, cids: list | None):
        replace(session, item_id, pids, cids)
        session.flush()
        raise IntegrityError("secret SQL", {}, Exception("secret constraint"))

    monkeypatch.setattr(operations, "replace_relations", fail_after_replace)
    payload = {"name": "Changed", "purpose_ids": [refs["p1"]], "climate_ids": [refs["c1"]]}
    path = f"/api/items/{original['id']}"
    if method == "post":
        path = "/api/items"
        payload.update(
            category_id=refs["category_id"],
            condition_id=refs["condition_id"],
            tracking_mode="individual",
        )
    response = client.request(method, path, json=payload)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "item_write_failed"
    assert "secret" not in response.text
    with Session(engine) as fresh:
        rows = fresh.scalars(select(Item).where(Item.category_id == refs["category_id"])).all()
        assert len(rows) == 1 and rows[0].name == "Item"
        assert stored_relations(fresh, original["id"]) == ([refs["p3"]], [refs["c3"]])


@pytest.fixture
def filtered_catalog(relations: tuple) -> tuple:
    client, engine, refs = relations
    # Make the second category a child to prove category filtering is exact.
    with Session(engine) as session:
        session.get(Category, refs["other_category"]).parent_id = refs["category_id"]
        session.commit()
    all_relations = {
        "purpose_ids": [refs["p2"], refs["p1"]],
        "climate_ids": [refs["c2"], refs["c1"]],
    }
    a1 = create(client, refs, name="A", tracking_mode="grouped", quantity=0, **all_relations)
    a2 = create(client, refs, name="A", tracking_mode="grouped", quantity=9, **all_relations)
    b = create(client, refs, name="B", purpose_ids=[refs["p1"]], climate_ids=[refs["c2"]])
    c = create(
        client,
        refs,
        name="C",
        category_id=refs["other_category"],
        condition_id=refs["other_condition"],
        tracking_mode="grouped",
        quantity=1,
        purpose_ids=[refs["p2"]],
        climate_ids=[refs["c1"]],
    )
    d = create(
        client,
        refs,
        name="D",
        condition_id=refs["other_condition"],
        tracking_mode="grouped",
        quantity=2,
        purpose_ids=[refs["p2"]],
        climate_ids=[refs["c1"]],
    )
    hidden = create(
        client, refs, name="Hidden", tracking_mode="grouped", quantity=0, **all_relations
    )
    assert client.delete(f"/api/items/{hidden['id']}").status_code == 204
    return client, engine, refs, {"a1": a1, "a2": a2, "b": b, "c": c, "d": d}


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({}, ["a1", "a2", "b", "c", "d"]),
        ({"category_id": "category_id"}, ["a1", "a2", "b", "d"]),
        ({"category_id": "other_category"}, ["c"]),
        ({"condition_id": "condition_id"}, ["a1", "a2", "b"]),
        ({"purpose_id": "p1"}, ["a1", "a2", "b"]),
        ({"climate_id": "c1"}, ["a1", "a2", "c", "d"]),
        ({"tracking_mode": "grouped"}, ["a1", "a2", "c", "d"]),
        ({"tracking_mode": "individual"}, ["b"]),
        ({"purpose_id": "p1", "climate_id": "c1"}, ["a1", "a2"]),
        ({"category_id": "category_id", "condition_id": "other_condition"}, ["d"]),
        (
            {
                "category_id": "category_id",
                "condition_id": "condition_id",
                "purpose_id": "p1",
                "climate_id": "c1",
                "tracking_mode": "grouped",
            },
            ["a1", "a2"],
        ),
    ],
)
def test_filters_and_ordering(filtered_catalog: tuple, filters: dict, expected: list[str]) -> None:
    client, _, refs, rows = filtered_catalog
    params = {field: refs[value] if value in refs else value for field, value in filters.items()}
    response = client.get("/api/items", params=params)
    assert response.status_code == 200
    assert response.json() == [rows[key] for key in expected]
    assert len({row["id"] for row in response.json()}) == len(expected)


@pytest.mark.parametrize("field", ["category_id", "condition_id", "purpose_id", "climate_id"])
@pytest.mark.parametrize("value", [32767, 999999, 2**63])
def test_unknown_filter_ids_are_empty_without_reference_validation(
    filtered_catalog: tuple, field: str, value: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _, _, _ = filtered_catalog
    monkeypatch.setattr(operations, "check_references", Mock(side_effect=AssertionError))
    monkeypatch.setattr(operations, "check_relation_references", Mock(side_effect=AssertionError))
    response = client.get("/api/items", params={field: value})
    assert response.status_code == 200 and response.json() == []


@pytest.mark.parametrize("field", ["category_id", "condition_id", "purpose_id", "climate_id"])
@pytest.mark.parametrize("value", ["0", "-1", "abc", "1.5"])
def test_malformed_filters_are_422(relations: tuple, field: str, value: str) -> None:
    client, _, _ = relations
    assert client.get("/api/items", params={field: value}).status_code == 422


def test_invalid_tracking_mode_filter(relations: tuple) -> None:
    client, _, _ = relations
    assert client.get("/api/items", params={"tracking_mode": "unknown"}).status_code == 422


@pytest.mark.parametrize("count", [1, 8])
def test_list_and_get_relation_queries_do_not_grow_per_item(relations: tuple, count: int) -> None:
    client, engine, refs = relations
    rows = [
        create(
            client, refs, purpose_ids=[refs["p2"], refs["p1"]], climate_ids=[refs["c2"], refs["c1"]]
        )
        for _ in range(count)
    ]
    selects = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        response = client.get("/api/items")
        assert response.status_code == 200 and response.json() == rows
        assert len(selects) == 3
        selects.clear()
        assert client.get(f"/api/items/{rows[0]['id']}").json() == rows[0]
        assert len(selects) == 3
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_removal_preserves_every_field_and_relations_in_new_session(relations: tuple) -> None:
    client, engine, refs = relations
    row = create(
        client,
        refs,
        tracking_mode="grouped",
        quantity=0,
        **{field: f"{field} value" for field in SCALARS},
        extra_attributes={"waterproof": True, "nested": {"volume_l": 35}},
        purpose_ids=[refs["p2"], refs["p1"]],
        climate_ids=[refs["c2"], refs["c1"]],
    )
    path = f"/api/items/{row['id']}"
    for _ in range(2):
        removed = client.delete(path)
        assert removed.status_code == 204 and removed.content == b""
        assert client.get("/api/items").json() == []
        assert client.get(path).json() == {**row, "is_active": False}
        with Session(engine) as fresh:
            stored = fresh.get(Item, row["id"])
            assert stored is not None and stored.is_active is False
            for field in (
                "name",
                "category_id",
                "condition_id",
                "quantity",
                "tracking_mode",
                "extra_attributes",
                *SCALARS,
            ):
                assert getattr(stored, field) == row[field]
            assert stored.created_at.isoformat().replace("+00:00", "Z") == row["created_at"]
            assert stored.updated_at.isoformat().replace("+00:00", "Z") == row["updated_at"]
            assert stored_relations(fresh, row["id"]) == (row["purpose_ids"], row["climate_ids"])


@pytest.mark.parametrize("missing", [9223372036854775807, 2**63])
def test_remove_missing_item(relations: tuple, missing: int) -> None:
    client, _, _ = relations
    response = client.delete(f"/api/items/{missing}")
    assert response.status_code == 404 and response.json()["error"]["code"] == "item_not_found"

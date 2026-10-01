import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from veshichkin.core.config import get_settings
from veshichkin.db.models import Category, Item, RevisionCategoryResult, RevisionSession
from veshichkin.db.session import get_session
from veshichkin.main import create_app

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def test_engine() -> Iterator[Engine]:
    url = os.environ.get("VESHICHKIN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("VESHICHKIN_TEST_DATABASE_URL is not set; PostgreSQL integration skipped")
    assert url.startswith("postgresql+psycopg://"), "Tests require PostgreSQL with Psycopg"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("VESHICHKIN_DATABASE_URL", url)
        get_settings.cache_clear()
        try:
            command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
        finally:
            get_settings.cache_clear()
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_client(test_engine: Engine) -> Iterator[tuple[TestClient, Session]]:
    # Router commits release savepoints; the outer transaction isolates each test.
    with test_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            app = create_app()
            app.dependency_overrides[get_session] = lambda: session
            try:
                with TestClient(app) as client:
                    yield client, session
            finally:
                session.close()
                transaction.rollback()


def add_category(
    session: Session, name: str, parent_id: int | None = None, order: int = 0
) -> Category:
    row = Category(name=name, parent_id=parent_id, sort_order=order)
    session.add(row)
    session.flush()
    session.commit()
    return row


def assert_error(response: Response, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("child", [False, True])
def test_create_root_and_child(db_client: tuple[TestClient, Session], child: bool) -> None:
    client, session = db_client
    parent_id = add_category(session, "Parent").id if child else None
    response = client.post("/api/categories", json={"name": "  New  ", "parent_id": parent_id})
    assert response.status_code == 201
    data = response.json()
    assert data == {"id": data["id"], "name": "New", "parent_id": parent_id, "sort_order": 0}
    stored = session.get(Category, data["id"])
    assert stored is not None and stored.name == "New"
    # Duplicate names are allowed.
    assert client.post("/api/categories", json={"name": "New"}).status_code == 201


@pytest.mark.parametrize(
    "method,payload",
    [
        ("post", {"name": " "}),
        ("post", {"name": "New", "sort_order": -1}),
        ("patch", {"name": " "}),
        ("patch", {"sort_order": -1}),
        ("patch", {"name": None}),
        ("patch", {"sort_order": None}),
    ],
)
def test_validation(
    db_client: tuple[TestClient, Session], method: str, payload: dict[str, object]
) -> None:
    client, session = db_client
    row = add_category(session, "Original")
    path = "/api/categories" if method == "post" else f"/api/categories/{row.id}"
    assert client.request(method, path, json=payload).status_code == 422
    assert session.get(Category, row.id).name == "Original"


@pytest.mark.parametrize("method", ["post", "patch"])
def test_missing_parent(db_client: tuple[TestClient, Session], method: str) -> None:
    client, session = db_client
    row = add_category(session, "Original")
    path = "/api/categories" if method == "post" else f"/api/categories/{row.id}"
    payload = {"parent_id": 9223372036854775807}
    if method == "post":
        payload["name"] = "New"
    assert_error(client.request(method, path, json=payload), 404, "category_parent_not_found")


def test_tree_nesting_and_deterministic_order(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    root = add_category(session, "Custom root", order=1000)
    b = add_category(session, "B", root.id, 10)
    a1 = add_category(session, "A", root.id, 10)
    a2 = add_category(session, "A", root.id, 10)
    first = add_category(session, "Z", root.id, 0)
    grandchild = add_category(session, "Grandchild", a1.id)
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert data == sorted(data, key=lambda node: (node["sort_order"], node["name"], node["id"]))
    node = next(node for node in data if node["id"] == root.id)
    assert [child["id"] for child in node["children"]] == [first.id, a1.id, a2.id, b.id]
    assert node["children"][1]["children"][0]["id"] == grandchild.id
    assert client.get("/api/categories").json() == data


def test_patch_partial_rename_sort_reparent_and_root(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    parent = add_category(session, "Parent")
    other = add_category(session, "Other")
    row = add_category(session, "Original", parent.id, 9)
    path = f"/api/categories/{row.id}"
    response = client.patch(path, json={"name": "  Renamed  "})
    assert response.status_code == 200
    assert response.json() == {
        "id": row.id,
        "name": "Renamed",
        "parent_id": parent.id,
        "sort_order": 9,
    }
    assert client.patch(path, json={"sort_order": 7}).json()["sort_order"] == 7
    assert client.patch(path, json={"parent_id": other.id}).json()["parent_id"] == other.id
    assert client.patch(path, json={"parent_id": None}).json()["parent_id"] is None
    unchanged = client.patch(path, json={})
    assert unchanged.json() == {"id": row.id, "name": "Renamed", "parent_id": None, "sort_order": 7}


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_self_direct_and_deep_cycle(db_client: tuple[TestClient, Session], depth: int) -> None:
    client, session = db_client
    a = add_category(session, "Arbitrary A")
    b = add_category(session, "Arbitrary B", a.id)
    c = add_category(session, "Arbitrary C", b.id)
    target_id = [a.id, b.id, c.id][depth]
    assert_error(
        client.patch(f"/api/categories/{a.id}", json={"parent_id": target_id}),
        409,
        "category_cycle",
    )
    session.expire_all()
    assert session.get(Category, a.id).parent_id is None
    assert client.get("/api/categories").status_code == 200


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_missing_category(db_client: tuple[TestClient, Session], method: str) -> None:
    client, _ = db_client
    response = client.request(
        method, "/api/categories/9223372036854775807", json={} if method == "patch" else None
    )
    assert_error(response, 404, "category_not_found")


def test_delete_empty_category(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    row = add_category(session, "Empty")
    row_id = row.id
    response = client.delete(f"/api/categories/{row_id}")
    assert response.status_code == 204 and response.content == b""
    assert session.get(Category, row_id) is None


@pytest.mark.parametrize("dependency", ["child", "active_item", "inactive_item", "revision"])
def test_delete_in_use(db_client: tuple[TestClient, Session], dependency: str) -> None:
    client, session = db_client
    row = add_category(session, "Used")
    row_id = row.id
    if dependency == "child":
        add_category(session, "Child", row_id)
    elif dependency.endswith("item"):
        session.add(
            Item(
                category_id=row_id,
                name="Item",
                tracking_mode="individual",
                quantity=1,
                is_active=dependency == "active_item",
            )
        )
    else:
        revision = RevisionSession(status="in_progress")
        session.add(revision)
        session.flush()
        session.add(
            RevisionCategoryResult(
                revision_session_id=revision.id, category_id=row_id, status="pending"
            )
        )
    session.flush()
    session.commit()
    assert_error(client.delete(f"/api/categories/{row_id}"), 409, "category_in_use")
    assert session.get(Category, row_id) is not None


def test_delete_database_restrict_is_safe(
    db_client: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session = db_client
    parent = add_category(session, "Protected parent")
    child = add_category(session, "Protected child", parent.id)
    parent_id, child_id = parent.id, child.id
    # Simulate a dependency appearing after all prechecks have returned empty.
    monkeypatch.setattr(session, "scalar", lambda query: None)
    response = client.delete(f"/api/categories/{parent_id}")
    assert_error(response, 409, "category_in_use")
    assert "constraint" not in response.text and "DELETE" not in response.text
    assert session.get(Category, parent_id) is not None
    assert session.get(Category, child_id) is not None


@pytest.mark.parametrize(
    "kind,order,codes",
    [
        (
            "purposes",
            "sort_order",
            {
                "city_work",
                "home",
                "boxing",
                "gym",
                "acrobatics",
                "travel",
                "hiking",
                "water_trip",
                "horse_trip",
                "alpine_skiing",
            },
        ),
        ("conditions", "rank", {"new", "excellent", "good", "worn", "heavily_worn"}),
        ("climates", "sort_order", {"hot", "warm", "cool", "cold", "severe_cold", "wet"}),
    ],
)
def test_seeded_reference_values_shape_and_order(
    db_client: tuple[TestClient, Session],
    kind: str,
    order: str,
    codes: set[str],
) -> None:
    client, _ = db_client
    response = client.get(f"/api/reference/{kind}")
    assert response.status_code == 200
    data = response.json()
    assert codes <= {row["code"] for row in data}
    assert data == sorted(data, key=lambda row: (row[order], row["name"], row["id"]))
    keys = {"id", "code", "name", order}
    if kind == "conditions":
        keys.add("description")
        assert all(row["description"] for row in data if row["code"] in codes)
    assert all(set(row) == keys for row in data)

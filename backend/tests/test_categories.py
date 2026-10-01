from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.categories import operations
from veshichkin.categories.schemas import CategoryCreate, CategoryPatch
from veshichkin.core.errors import ApplicationError
from veshichkin.db.models import Category
from veshichkin.db.session import get_session
from veshichkin.main import create_app


def category(id: int, name: str, parent_id: int | None = None, order: int = 0) -> Category:
    return Category(id=id, name=name, parent_id=parent_id, sort_order=order)


def test_tree_orders_every_level_by_order_name_id() -> None:
    rows = [
        category(8, "B", 1, 0),
        category(4, "A", None, 10),
        category(1, "Root"),
        category(7, "A", 1, 0),
        category(6, "A", 1, 0),
        category(5, "Nested", 6),
        category(3, "B", None, 10),
        category(2, "Z", None, 5),
    ]
    roots = operations.build_tree(rows)
    assert [node.id for node in roots] == [1, 2, 4, 3]
    assert [node.id for node in roots[0].children] == [6, 7, 8]
    assert roots[0].children[0].children[0].id == 5
    assert roots[0].parent_id is None
    assert roots[0].children[0].parent_id == 1
    assert roots[1].children == []
    assert operations.build_tree([]) == []


@pytest.mark.parametrize("parent_id", [10, 20, 30])
def test_reject_self_direct_and_deep_cycle(parent_id: int) -> None:
    with pytest.raises(ApplicationError) as error:
        operations.validate_parent(10, parent_id, {10: None, 20: 10, 30: 20})
    assert (error.value.status_code, error.value.code) == (409, "category_cycle")


@pytest.mark.parametrize("category_id,parent_id", [(10, None), (10, 40), (None, 20)])
def test_valid_root_reparent_and_new_child(category_id: int | None, parent_id: int | None) -> None:
    operations.validate_parent(category_id, parent_id, {10: None, 20: 10, 40: None})


def test_missing_parent() -> None:
    with pytest.raises(ApplicationError) as error:
        operations.validate_parent(10, 99, {10: None})
    assert (error.value.status_code, error.value.code) == (404, "category_parent_not_found")


@pytest.mark.parametrize("schema", [CategoryCreate, CategoryPatch])
@pytest.mark.parametrize(
    "payload", [{"name": " \t "}, {"sort_order": -1}, {"name": None}, {"sort_order": None}]
)
def test_invalid_dto(
    schema: type[CategoryCreate] | type[CategoryPatch], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_dto_trim_defaults_and_patch_presence() -> None:
    assert CategoryCreate(name="  Example  ").model_dump() == {
        "name": "Example",
        "parent_id": None,
        "sort_order": 0,
    }
    assert CategoryPatch(name="  Renamed  ").model_dump(exclude_unset=True) == {"name": "Renamed"}
    assert CategoryPatch().model_dump(exclude_unset=True) == {}
    assert CategoryPatch(parent_id=None).model_dump(exclude_unset=True) == {"parent_id": None}


@pytest.fixture
def mock_client() -> Iterator[tuple[TestClient, Mock]]:
    app = create_app()
    session = Mock(spec=Session)
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client, session


def test_tree_http_contract(mock_client: tuple[TestClient, Mock]) -> None:
    client, session = mock_client
    session.scalars.return_value.all.return_value = [category(2, "Child", 1), category(1, "Root")]
    response = client.get("/api/categories")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Root",
            "parent_id": None,
            "sort_order": 0,
            "children": [
                {"id": 2, "name": "Child", "parent_id": 1, "sort_order": 0, "children": []}
            ],
        }
    ]
    session.scalars.assert_called_once()


@pytest.mark.parametrize("phase", ["flush", "commit"])
def test_delete_integrity_race_rolls_back_and_hides_sql(
    mock_client: tuple[TestClient, Mock],
    phase: str,
) -> None:
    client, session = mock_client
    session.get.return_value = category(1, "Unused")
    session.scalar.return_value = None
    getattr(session, phase).side_effect = IntegrityError(
        "secret SQL", {}, Exception("secret constraint")
    )
    response = client.delete("/api/categories/1")
    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "category_in_use", "message": "Category is in use"}
    }
    assert "secret" not in response.text
    session.rollback.assert_called_once()


def test_openapi_routes_and_read_only_reference() -> None:
    paths = create_app().openapi()["paths"]
    assert set(paths["/api/categories"]) == {"get", "post"}
    assert set(paths["/api/categories/{category_id}"]) == {"patch", "delete"}
    for kind in ("purposes", "conditions", "climates"):
        assert set(paths[f"/api/reference/{kind}"]) == {"get"}
    assert {"/api/health", "/api/ready"} <= paths.keys()

import ast
import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.dml import Delete

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND / "alembic/versions/0002_reference_data.py"


@pytest.fixture
def migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reference_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chain(migration: ModuleType) -> None:
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    assert script.get_heads() == ["0002_reference_data"]
    assert migration.revision == "0002_reference_data"
    assert migration.down_revision == "0001_initial_schema"
    assert [revision.revision for revision in script.walk_revisions()] == [
        "0002_reference_data",
        "0001_initial_schema",
    ]


def test_category_definitions(migration: ModuleType) -> None:
    groups = migration.CATEGORY_GROUPS
    assert [root for root, _ in groups] == ["Одежда и обувь", "Туризм", "Горные лыжи"]
    assert [len(children) for _, children in groups] == [11, 11, 9]
    assert sum(len(children) for _, children in groups) == 31
    for _, children in groups:
        assert len(set(children)) == len(children)


@pytest.mark.parametrize(
    "dataset,expected_codes",
    [
        (
            "PURPOSES",
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
        ("CONDITIONS", {"new", "excellent", "good", "worn", "heavily_worn"}),
        ("CLIMATES", {"hot", "warm", "cool", "cold", "severe_cold", "wet"}),
    ],
)
def test_reference_codes(migration: ModuleType, dataset: str, expected_codes: set[str]) -> None:
    rows = getattr(migration, dataset)
    codes = [row[0] for row in rows]
    assert len(codes) == len(set(codes))
    assert set(codes) == expected_codes
    assert len({row[1] for row in rows}) == len(rows)


def test_condition_scale_and_no_replacement_decision(migration: ModuleType) -> None:
    assert [row[2] for row in migration.CONDITIONS] == [0, 1, 2, 3, 4]
    heavily_worn = next(row for row in migration.CONDITIONS if row[0] == "heavily_worn")
    assert len(heavily_worn) == 4
    assert heavily_worn[3] == (
        "Сильный износ, но состояние само по себе не означает решение о замене"
    )
    assert set(migration.conditions.c.keys()) == {"code", "name", "rank", "description"}


@pytest.mark.parametrize("dataset", ["PURPOSES", "CLIMATES"])
def test_reference_sort_order(migration: ModuleType, dataset: str) -> None:
    rows = getattr(migration, dataset)
    assert [row[2] for row in rows] == list(range(10, len(rows) * 10 + 1, 10))


def test_upgrade_links_children_to_returned_ids_and_inserts_only_seed_datasets(
    migration: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execute = Mock()
    bulk_insert = Mock()
    monkeypatch.setattr(migration.op, "execute", execute)
    monkeypatch.setattr(migration.op, "bulk_insert", bulk_insert)
    migration.upgrade()
    assert execute.call_count == 3
    for order, (call, (root_name, children)) in enumerate(
        zip(execute.call_args_list, migration.CATEGORY_GROUPS, strict=True), start=1
    ):
        statement = call.args[0]
        sql = str(
            statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        )
        assert "WITH new_root AS" in sql
        assert "RETURNING categories.id" in sql
        assert "new_root.id" in sql and "JOIN new_root ON true" in sql
        assert f"VALUES ('{root_name}', {order * 10})" in sql
        for child_order, child in enumerate(children, start=1):
            assert f"('{child}', {child_order * 10})" in sql
        assert "INSERT INTO categories (name, parent_id, sort_order)" in sql
    assert [call.args[0].name for call in bulk_insert.call_args_list] == [
        "purposes",
        "conditions",
        "climates",
    ]
    assert [len(call.args[1]) for call in bulk_insert.call_args_list] == [10, 5, 6]


def test_downgrade_is_targeted_and_dependency_ordered(
    migration: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execute = Mock()
    monkeypatch.setattr(migration.op, "execute", execute)
    migration.downgrade()
    statements = [call.args[0] for call in execute.call_args_list]
    assert [statement.table.name for statement in statements] == [
        "categories",
        "categories",
        "categories",
        "categories",
        "purposes",
        "conditions",
        "climates",
    ]
    for statement in statements:
        assert isinstance(statement, Delete)
        assert statement.whereclause is not None
    sql = [
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement in statements
    ]
    for child_sql, (root, children) in zip(sql[:3], migration.CATEGORY_GROUPS, strict=True):
        assert "categories.parent_id IN (SELECT categories.id" in child_sql
        assert "categories.parent_id IS NULL" in child_sql
        assert f"categories.name = '{root}'" in child_sql
        for child in children:
            assert f"'{child}'" in child_sql
    assert "categories.parent_id IS NULL" in sql[3]
    for reference_sql, dataset in zip(
        sql[4:], (migration.PURPOSES, migration.CONDITIONS, migration.CLIMATES), strict=True
    ):
        assert ".code IN (" in reference_sql
        for code, *_ in dataset:
            assert f"'{code}'" in reference_sql


def test_migration_has_no_runtime_import_or_startup_seeding() -> None:
    tree = ast.parse(MIGRATION_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("veshichkin") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("veshichkin")
        if isinstance(node, ast.Call):
            assert not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr
                in {
                    "get_bind",
                    "create_all",
                    "get_settings",
                }
            )
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert functions == {"upgrade", "downgrade"}

import ast
import importlib.util
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    MetaData,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql

from veshichkin.db import models
from veshichkin.db.base import Base

TABLES = {
    "categories",
    "purposes",
    "conditions",
    "climates",
    "items",
    "item_purposes",
    "item_climates",
    "measurement_profile",
    "revision_sessions",
    "revision_category_results",
}
BACKEND = Path(__file__).resolve().parents[1]


def checks(table: Table) -> dict[str, str]:
    return {
        str(constraint.name): str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_expected_tables() -> None:
    assert set(Base.metadata.tables) == TABLES
    assert models.Item.__table__ is Base.metadata.tables["items"]


def test_item_tracking_and_quantity_constraints() -> None:
    table = Base.metadata.tables["items"]
    constraints = checks(table)
    assert (
        constraints["ck_items_tracking_mode_valid"] == "tracking_mode IN ('individual', 'grouped')"
    )
    assert constraints["ck_items_quantity_matches_tracking_mode"] == (
        "(tracking_mode = 'individual' AND quantity = 1) OR "
        "(tracking_mode = 'grouped' AND quantity >= 0)"
    )
    assert not table.c.tracking_mode.nullable
    assert not table.c.quantity.nullable
    assert not table.c.category_id.nullable


def test_item_active_defaults_and_no_boolean_index() -> None:
    table = models.Item.__table__
    column = table.c.is_active
    assert isinstance(column.type, Boolean)
    assert not column.nullable
    assert column.default is not None and column.default.arg is True
    assert column.server_default is not None and str(column.server_default.arg) == "true"
    assert all(tuple(index.columns.keys()) != ("is_active",) for index in table.indexes)


def test_item_active_migration_upgrade_and_downgrade_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "item_active_migration", BACKEND / "alembic/versions/0003_item_is_active.py"
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0003_item_is_active"
    assert migration.down_revision == "0002_reference_data"
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    monkeypatch.setattr(migration, "op", Operations(context))
    migration.upgrade()
    assert output.getvalue().strip() == (
        "ALTER TABLE items ADD COLUMN is_active BOOLEAN DEFAULT true NOT NULL;"
    )
    output.seek(0)
    output.truncate()
    migration.downgrade()
    assert output.getvalue().strip() == "ALTER TABLE items DROP COLUMN is_active;"


def test_measurement_singleton_and_positive_values() -> None:
    table = Base.metadata.tables["measurement_profile"]
    constraints = checks(table)
    assert constraints["ck_measurement_profile_singleton"] == "id = 1"
    assert table.c.id.identity is None
    for column in (
        "height_cm",
        "weight_kg",
        "chest_cm",
        "waist_cm",
        "hips_cm",
        "inseam_cm",
        "foot_length_cm",
    ):
        assert table.c[column].nullable
        assert f"{column} > 0" in constraints.values()


def test_foreign_keys_and_deletion_rules() -> None:
    expected = {
        ("categories", "parent_id"): ("categories.id", "RESTRICT"),
        ("items", "category_id"): ("categories.id", "RESTRICT"),
        ("items", "condition_id"): ("conditions.id", "RESTRICT"),
        ("item_purposes", "item_id"): ("items.id", "CASCADE"),
        ("item_purposes", "purpose_id"): ("purposes.id", "RESTRICT"),
        ("item_climates", "item_id"): ("items.id", "CASCADE"),
        ("item_climates", "climate_id"): ("climates.id", "RESTRICT"),
        ("revision_category_results", "revision_session_id"): ("revision_sessions.id", "CASCADE"),
        ("revision_category_results", "category_id"): ("categories.id", "RESTRICT"),
    }
    actual = {}
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            actual[(table.name, fk.parent.name)] = (fk.target_fullname, fk.ondelete)
            assert type(fk.parent.type) is type(fk.column.type)
    assert actual == expected
    assert "parent_id != id" in checks(Base.metadata.tables["categories"]).values()


def test_composite_primary_keys() -> None:
    for table_name, columns in {
        "revision_category_results": ["revision_session_id", "category_id"],
        "item_purposes": ["item_id", "purpose_id"],
        "item_climates": ["item_id", "climate_id"],
    }.items():
        assert list(Base.metadata.tables[table_name].primary_key.columns.keys()) == columns


@pytest.mark.parametrize(
    "table_name,column_name",
    [
        ("items", "extra_attributes"),
        ("measurement_profile", "extra_measurements"),
    ],
)
def test_jsonb_contract(table_name: str, column_name: str) -> None:
    column = Base.metadata.tables[table_name].c[column_name]
    assert isinstance(column.type, postgresql.JSONB)
    assert not column.nullable
    assert str(column.server_default.arg) == "'{}'::jsonb"


def test_revision_and_verification_constraints() -> None:
    assert (
        "last_verification_state IN ('empty', 'nonempty')"
        in checks(models.Category.__table__).values()
    )
    assert set(checks(models.RevisionSession.__table__).values()) == {
        "status IN ('in_progress', 'completed', 'cancelled')",
        "completed_at >= started_at",
    }
    assert set(checks(models.RevisionCategoryResult.__table__).values()) == {
        "status IN ('pending', 'in_progress', 'completed', 'skipped')",
        "result_state IN ('empty', 'nonempty')",
        "status != 'completed' OR (result_state IS NOT NULL AND verified_at IS NOT NULL)",
    }


def test_reference_uniqueness_and_nonnegative_order() -> None:
    for name in ("purposes", "conditions", "climates"):
        table = Base.metadata.tables[name]
        unique_columns = {
            tuple(constraint.columns.keys())
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        assert unique_columns == (
            {("code",), ("name",), ("rank",)} if name == "conditions" else {("code",), ("name",)}
        )
        assert ("rank >= 0" if name == "conditions" else "sort_order >= 0") in checks(
            table
        ).values()


def test_identity_timestamps_and_stable_names() -> None:
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            assert constraint.name
        for index in table.indexes:
            assert index.name.startswith(f"ix_{table.name}_")
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone
                if column.name in ("created_at", "updated_at", "started_at"):
                    assert column.server_default is not None
        if "id" in table.c and table.name != "measurement_profile":
            assert table.c.id.identity is not None
            expected = (
                "BIGINT"
                if table.name in ("categories", "items", "revision_sessions")
                else "SMALLINT"
            )
            assert str(table.c.id.type) == expected


def test_production_source_never_calls_create_all() -> None:
    paths = list((BACKEND / "src").rglob("*.py")) + list((BACKEND / "alembic").rglob("*.py"))
    for path in paths:
        tree = ast.parse(path.read_text())
        assert not any(
            isinstance(node, ast.Call)
            and (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "create_all"
                or isinstance(node.func, ast.Name)
                and node.func.id == "create_all"
            )
            for node in ast.walk(tree)
        ), path


def test_schema_migrations_match_metadata_and_initial_drops_in_dependency_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "initial_migration", BACKEND / "alembic/versions/0001_initial_schema.py"
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0001_initial_schema"
    assert migration.down_revision is None
    migrated = MetaData()

    def create_table(name: str, *args: object) -> Table:
        return Table(name, migrated, *args)

    def create_index(name: str, table_name: str, columns: list[str], unique: bool) -> None:
        Index(name, *(migrated.tables[table_name].c[column] for column in columns), unique=unique)

    monkeypatch.setattr(migration.op, "create_table", create_table)
    monkeypatch.setattr(migration.op, "create_index", create_index)
    monkeypatch.setattr(migration.op, "f", lambda name: name)
    migration.upgrade()
    assert set(migrated.tables) == TABLES

    spec = importlib.util.spec_from_file_location(
        "item_active_migration", BACKEND / "alembic/versions/0003_item_is_active.py"
    )
    assert spec is not None and spec.loader is not None
    item_migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item_migration)

    def add_column(table_name: str, column: Column[bool]) -> None:
        migrated.tables[table_name].append_column(column)

    monkeypatch.setattr(item_migration.op, "add_column", add_column)
    item_migration.upgrade()
    dialect = postgresql.dialect()
    for name, expected in Base.metadata.tables.items():
        actual = migrated.tables[name]
        assert list(actual.c.keys()) == list(expected.c.keys())
        for column_name, column in expected.c.items():
            other = actual.c[column_name]
            assert column.type.compile(dialect=dialect) == other.type.compile(dialect=dialect)
            assert column.nullable == other.nullable
            assert (column.identity is not None) == (other.identity is not None)
            if column.identity is None:
                if column.server_default is None:
                    assert other.server_default is None
                else:
                    assert other.server_default is not None
                    assert str(column.server_default.arg) == str(other.server_default.arg)
        assert checks(actual) == checks(expected)
        assert list(actual.primary_key.columns.keys()) == list(expected.primary_key.columns.keys())
        assert {
            (fk.parent.name, fk.target_fullname, fk.ondelete, fk.constraint.name)
            for fk in actual.foreign_keys
        } == {
            (fk.parent.name, fk.target_fullname, fk.ondelete, fk.constraint.name)
            for fk in expected.foreign_keys
        }
        assert {
            (tuple(c.columns.keys()), c.name)
            for c in actual.constraints
            if isinstance(c, UniqueConstraint)
        } == {
            (tuple(c.columns.keys()), c.name)
            for c in expected.constraints
            if isinstance(c, UniqueConstraint)
        }
        assert {(index.name, tuple(index.columns.keys())) for index in actual.indexes} == {
            (index.name, tuple(index.columns.keys())) for index in expected.indexes
        }
    drop = Mock()
    monkeypatch.setattr(migration.op, "drop_table", drop)
    migration.downgrade()
    dropped = [call.args[0] for call in drop.call_args_list]
    assert set(dropped) == TABLES and len(dropped) == len(TABLES)
    for table in migrated.tables.values():
        for fk in table.foreign_keys:
            if table.name != fk.column.table.name:
                assert dropped.index(table.name) < dropped.index(fk.column.table.name)

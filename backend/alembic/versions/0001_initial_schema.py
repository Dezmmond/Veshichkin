"""Create the initial catalog and revision persistence schema.

Revision ID: 0001_initial_schema
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_verification_state", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_verification_state IN ('empty', 'nonempty')",
            name=op.f("ck_categories_verification_state_valid"),
        ),
        sa.CheckConstraint("parent_id != id", name=op.f("ck_categories_parent_not_self")),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_categories_sort_order_nonnegative")),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name=op.f("fk_categories_parent_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)
    op.create_table(
        "climates",
        sa.Column("id", sa.SmallInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_climates_sort_order_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_climates")),
        sa.UniqueConstraint("code", name=op.f("uq_climates_code")),
        sa.UniqueConstraint("name", name=op.f("uq_climates_name")),
    )
    op.create_table(
        "conditions",
        sa.Column("id", sa.SmallInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("rank >= 0", name=op.f("ck_conditions_rank_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conditions")),
        sa.UniqueConstraint("code", name=op.f("uq_conditions_code")),
        sa.UniqueConstraint("name", name=op.f("uq_conditions_name")),
        sa.UniqueConstraint("rank", name=op.f("uq_conditions_rank")),
    )
    op.create_table(
        "measurement_profile",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("height_cm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("chest_cm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("waist_cm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("hips_cm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("inseam_cm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("foot_length_cm", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "extra_measurements",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("chest_cm > 0", name=op.f("ck_measurement_profile_chest_positive")),
        sa.CheckConstraint(
            "foot_length_cm > 0", name=op.f("ck_measurement_profile_foot_length_positive")
        ),
        sa.CheckConstraint("height_cm > 0", name=op.f("ck_measurement_profile_height_positive")),
        sa.CheckConstraint("hips_cm > 0", name=op.f("ck_measurement_profile_hips_positive")),
        sa.CheckConstraint("id = 1", name=op.f("ck_measurement_profile_singleton")),
        sa.CheckConstraint("inseam_cm > 0", name=op.f("ck_measurement_profile_inseam_positive")),
        sa.CheckConstraint("waist_cm > 0", name=op.f("ck_measurement_profile_waist_positive")),
        sa.CheckConstraint("weight_kg > 0", name=op.f("ck_measurement_profile_weight_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurement_profile")),
    )
    op.create_table(
        "purposes",
        sa.Column("id", sa.SmallInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_purposes_sort_order_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purposes")),
        sa.UniqueConstraint("code", name=op.f("uq_purposes_code")),
        sa.UniqueConstraint("name", name=op.f("uq_purposes_name")),
    )
    op.create_table(
        "revision_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'cancelled')",
            name=op.f("ck_revision_sessions_status_valid"),
        ),
        sa.CheckConstraint(
            "completed_at >= started_at",
            name=op.f("ck_revision_sessions_completion_not_before_start"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_revision_sessions")),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tracking_mode", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("condition_id", sa.SmallInteger(), nullable=True),
        sa.Column("brand", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("size", sa.Text(), nullable=True),
        sa.Column("material", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "extra_attributes",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(tracking_mode = 'individual' AND quantity = 1) OR (tracking_mode = 'grouped' AND quantity >= 0)",
            name=op.f("ck_items_quantity_matches_tracking_mode"),
        ),
        sa.CheckConstraint(
            "tracking_mode IN ('individual', 'grouped')", name=op.f("ck_items_tracking_mode_valid")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_items_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["condition_id"],
            ["conditions.id"],
            name=op.f("fk_items_condition_id_conditions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
    )
    op.create_index(op.f("ix_items_category_id"), "items", ["category_id"], unique=False)
    op.create_index(op.f("ix_items_condition_id"), "items", ["condition_id"], unique=False)
    op.create_table(
        "revision_category_results",
        sa.Column("revision_session_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("result_state", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "result_state IN ('empty', 'nonempty')",
            name=op.f("ck_revision_category_results_result_state_valid"),
        ),
        sa.CheckConstraint(
            "status != 'completed' OR (result_state IS NOT NULL AND verified_at IS NOT NULL)",
            name=op.f("ck_revision_category_results_completed_has_result"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name=op.f("ck_revision_category_results_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_revision_category_results_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revision_session_id"],
            ["revision_sessions.id"],
            name=op.f("fk_revision_category_results_revision_session_id_revision_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "revision_session_id", "category_id", name=op.f("pk_revision_category_results")
        ),
    )
    op.create_index(
        op.f("ix_revision_category_results_category_id"),
        "revision_category_results",
        ["category_id"],
        unique=False,
    )
    op.create_table(
        "item_climates",
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("climate_id", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["climate_id"],
            ["climates.id"],
            name=op.f("fk_item_climates_climate_id_climates"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_item_climates_item_id_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("item_id", "climate_id", name=op.f("pk_item_climates")),
    )
    op.create_index(
        op.f("ix_item_climates_climate_id"), "item_climates", ["climate_id"], unique=False
    )
    op.create_table(
        "item_purposes",
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose_id", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_item_purposes_item_id_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["purpose_id"],
            ["purposes.id"],
            name=op.f("fk_item_purposes_purpose_id_purposes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("item_id", "purpose_id", name=op.f("pk_item_purposes")),
    )
    op.create_index(
        op.f("ix_item_purposes_purpose_id"), "item_purposes", ["purpose_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("item_purposes")
    op.drop_table("item_climates")
    op.drop_table("revision_category_results")
    op.drop_table("items")
    op.drop_table("revision_sessions")
    op.drop_table("purposes")
    op.drop_table("measurement_profile")
    op.drop_table("conditions")
    op.drop_table("climates")
    op.drop_table("categories")

"""Keep inactive items without physically deleting them.

Revision ID: 0003_item_is_active
Revises: 0002_reference_data
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_item_is_active"
down_revision: str | Sequence[str] | None = "0002_reference_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("items", "is_active")

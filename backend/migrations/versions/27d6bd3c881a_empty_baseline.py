"""empty baseline

Revision ID: 27d6bd3c881a
Revises:
Create Date: 2026-09-11 15:40:43.681090

"""

revision: str = "27d6bd3c881a"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Upgrade schema. Empty baseline: only alembic_version is created."""


def downgrade() -> None:
    """Downgrade schema. Empty baseline: no tables to drop."""

"""Persist notification dismissal to prevent cleared alerts from returning.

Revision ID: 0008_add_notification_dismissal
Revises: 0007_remove_catchup_pref
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008_add_notification_dismissal"
down_revision: str | None = "0007_remove_catchup_pref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("cleared_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("notifications", "cleared_at")

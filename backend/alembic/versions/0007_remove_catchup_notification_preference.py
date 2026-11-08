"""Remove unused catch-up notification preference.

Revision ID: 0007_remove_catchup_pref
Revises: 0006_add_notifications
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_remove_catchup_pref"
down_revision: str | None = "0006_add_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("notification_preferences", "catchup_notifications_enabled")


def downgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column(
            "catchup_notifications_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )

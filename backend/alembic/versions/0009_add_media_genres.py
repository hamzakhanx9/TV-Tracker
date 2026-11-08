"""Store media genres for library insights and filtering.

Revision ID: 0009_add_media_genres
Revises: 0008_add_notification_dismissal
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_add_media_genres"
down_revision: str | None = "0008_add_notification_dismissal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "media",
        sa.Column("genres", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("media", "genres")

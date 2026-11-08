"""Add personal media ratings, reviews, and notes.

Revision ID: 0005_add_personal_feedback
Revises: 0004_add_episode_tracking
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_add_personal_feedback"
down_revision: str | None = "0004_add_episode_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_library", sa.Column("personal_rating", sa.Float(), nullable=True))
    op.add_column("user_library", sa.Column("personal_review", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_user_library_personal_rating",
        "user_library",
        "personal_rating IS NULL OR (personal_rating >= 1 AND personal_rating <= 10)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_library_personal_rating", "user_library", type_="check")
    op.drop_column("user_library", "personal_review")
    op.drop_column("user_library", "personal_rating")

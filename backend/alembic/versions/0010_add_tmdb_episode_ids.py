"""Support TMDB episodes when TVmaze has no matching show.

Revision ID: 0010_add_tmdb_episode_ids
Revises: 0009_add_media_genres
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_add_tmdb_episode_ids"
down_revision: str | None = "0009_add_media_genres"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.alter_column("tvmaze_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("tmdb_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_episodes_tmdb_id", ["tmdb_id"])


def downgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.drop_constraint("uq_episodes_tmdb_id", type_="unique")
        batch_op.drop_column("tmdb_id")
        batch_op.alter_column("tvmaze_id", existing_type=sa.Integer(), nullable=False)

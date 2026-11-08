"""Store aggregate ratings from external providers.

Revision ID: 0003_add_external_ratings
Revises: 0002_add_media_library
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_add_external_ratings"
down_revision: str | None = "0002_add_media_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("media", sa.Column("tmdb_rating", sa.Float(), nullable=True))
    op.add_column("media", sa.Column("tmdb_vote_count", sa.Integer(), nullable=True))
    op.add_column("media", sa.Column("imdb_rating", sa.Float(), nullable=True))
    op.add_column("media", sa.Column("rotten_tomatoes_rating", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("media", "rotten_tomatoes_rating")
    op.drop_column("media", "imdb_rating")
    op.drop_column("media", "tmdb_vote_count")
    op.drop_column("media", "tmdb_rating")

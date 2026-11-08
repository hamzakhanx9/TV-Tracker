"""Add seasons, episodes, and watch events.

Revision ID: 0004_add_episode_tracking
Revises: 0003_add_external_ratings
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_add_episode_tracking"
down_revision: str | None = "0003_add_external_ratings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "seasons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("poster_path", sa.String(length=500), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_id", "season_number", name="uq_seasons_media_number"),
    )
    op.create_index("ix_seasons_media_id", "seasons", ["media_id"], unique=False)

    op.create_table(
        "episodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("tvmaze_id", sa.Integer(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("air_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("runtime", sa.Integer(), nullable=True),
        sa.Column("still_path", sa.String(length=500), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tvmaze_id"),
    )
    op.create_index("ix_episodes_season_id", "episodes", ["season_id"], unique=False)

    op.create_table(
        "watch_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=True),
        sa.Column("episode_id", sa.Uuid(), nullable=True),
        sa.Column(
            "watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(media_id IS NOT NULL AND episode_id IS NULL) OR "
            "(media_id IS NULL AND episode_id IS NOT NULL)",
            name="ck_watch_events_exactly_one_target",
        ),
        sa.CheckConstraint(
            "event_type IN ('WATCHED', 'REWATCHED', 'UNWATCHED')", name="ck_watch_events_type"
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_watch_events_idempotency"),
    )
    for column in ("user_id", "media_id", "episode_id"):
        op.create_index(f"ix_watch_events_{column}", "watch_events", [column], unique=False)
    op.create_index(
        "uq_watch_events_current_media",
        "watch_events",
        ["user_id", "media_id"],
        unique=True,
        sqlite_where=sa.text("media_id IS NOT NULL AND episode_id IS NULL AND is_current = 1"),
        postgresql_where=sa.text("media_id IS NOT NULL AND episode_id IS NULL AND is_current"),
    )
    op.create_index(
        "uq_watch_events_current_episode",
        "watch_events",
        ["user_id", "episode_id"],
        unique=True,
        sqlite_where=sa.text("episode_id IS NOT NULL AND media_id IS NULL AND is_current = 1"),
        postgresql_where=sa.text("episode_id IS NOT NULL AND media_id IS NULL AND is_current"),
    )


def downgrade() -> None:
    op.drop_index("uq_watch_events_current_episode", table_name="watch_events")
    op.drop_index("uq_watch_events_current_media", table_name="watch_events")
    for column in ("episode_id", "media_id", "user_id"):
        op.drop_index(f"ix_watch_events_{column}", table_name="watch_events")
    op.drop_table("watch_events")
    op.drop_index("ix_episodes_season_id", table_name="episodes")
    op.drop_table("episodes")
    op.drop_index("ix_seasons_media_id", table_name="seasons")
    op.drop_table("seasons")

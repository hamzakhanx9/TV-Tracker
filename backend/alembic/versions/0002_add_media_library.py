"""Add normalized media and the local user's library.

Revision ID: 0002_add_media_library
Revises: 0001_create_users
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_media_library"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("original_title", sa.String(length=500), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("first_air_date", sa.Date(), nullable=True),
        sa.Column("poster_path", sa.String(length=500), nullable=True),
        sa.Column("backdrop_path", sa.String(length=500), nullable=True),
        sa.Column("runtime", sa.Integer(), nullable=True),
        sa.Column("original_language", sa.String(length=20), nullable=True),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
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
        sa.CheckConstraint("media_type IN ('MOVIE', 'TV')", name="ck_media_media_type"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_media_type", "media", ["media_type"])
    op.create_index("ix_media_title", "media", ["title"])

    op.create_table(
        "media_external_ids",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_media_external_provider_id"),
    )
    op.create_index("ix_media_external_ids_media_id", "media_external_ids", ["media_id"])

    op.create_table(
        "user_library",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "watch_status",
            sa.String(length=20),
            server_default="PLAN_TO_WATCH",
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("personal_notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "watch_status IN ('PLAN_TO_WATCH', 'WATCHING', 'COMPLETED', 'ON_HOLD', 'DROPPED')",
            name="ck_user_library_watch_status",
        ),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "media_id", name="uq_user_library_user_media"),
    )
    op.create_index("ix_user_library_user_id", "user_library", ["user_id"])
    op.create_index("ix_user_library_media_id", "user_library", ["media_id"])


def downgrade() -> None:
    op.drop_index("ix_user_library_media_id", table_name="user_library")
    op.drop_index("ix_user_library_user_id", table_name="user_library")
    op.drop_table("user_library")
    op.drop_index("ix_media_external_ids_media_id", table_name="media_external_ids")
    op.drop_table("media_external_ids")
    op.drop_index("ix_media_title", table_name="media")
    op.drop_index("ix_media_media_type", table_name="media")
    op.drop_table("media")

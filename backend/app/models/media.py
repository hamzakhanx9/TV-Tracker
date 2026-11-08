from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class Media(Base):
    __tablename__ = "media"
    __table_args__ = (
        CheckConstraint("media_type IN ('MOVIE', 'TV')", name="ck_media_media_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    original_title: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[date | None] = mapped_column(Date)
    first_air_date: Mapped[date | None] = mapped_column(Date)
    poster_path: Mapped[str | None] = mapped_column(String(500))
    backdrop_path: Mapped[str | None] = mapped_column(String(500))
    runtime: Mapped[int | None] = mapped_column(Integer)
    original_language: Mapped[str | None] = mapped_column(String(20))
    popularity: Mapped[float | None] = mapped_column(Float)
    tmdb_rating: Mapped[float | None] = mapped_column(Float)
    tmdb_vote_count: Mapped[int | None] = mapped_column(Integer)
    imdb_rating: Mapped[float | None] = mapped_column(Float)
    rotten_tomatoes_rating: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    external_ids: Mapped[list["MediaExternalId"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )
    library_entries: Mapped[list["UserLibrary"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )
    seasons: Mapped[list["Season"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class MediaExternalId(Base):
    __tablename__ = "media_external_ids"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_media_external_provider_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    media_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    media: Mapped[Media] = relationship(back_populates="external_ids")


class UserLibrary(Base):
    __tablename__ = "user_library"
    __table_args__ = (
        UniqueConstraint("user_id", "media_id", name="uq_user_library_user_media"),
        CheckConstraint(
            "watch_status IN ('PLAN_TO_WATCH', 'WATCHING', 'COMPLETED', 'ON_HOLD', 'DROPPED')",
            name="ck_user_library_watch_status",
        ),
        CheckConstraint(
            "personal_rating IS NULL OR (personal_rating >= 1 AND personal_rating <= 10)",
            name="ck_user_library_personal_rating",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    watch_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PLAN_TO_WATCH", server_default="PLAN_TO_WATCH"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    personal_rating: Mapped[float | None] = mapped_column(Float)
    personal_review: Mapped[str | None] = mapped_column(Text)
    personal_notes: Mapped[str | None] = mapped_column(Text)

    media: Mapped[Media] = relationship(back_populates="library_entries")


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("media_id", "season_number", name="uq_seasons_media_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    media_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text)
    poster_path: Mapped[str | None] = mapped_column(String(500))
    air_date: Mapped[date | None] = mapped_column(Date)

    media: Mapped[Media] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tvmaze_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    episode_number: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text)
    air_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    air_date: Mapped[date | None] = mapped_column(Date)
    runtime: Mapped[int | None] = mapped_column(Integer)
    still_path: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    season: Mapped[Season] = relationship(back_populates="episodes")
    watch_events: Mapped[list["WatchEvent"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )


class WatchEvent(Base):
    __tablename__ = "watch_events"
    __table_args__ = (
        CheckConstraint(
            "(media_id IS NOT NULL AND episode_id IS NULL) OR "
            "(media_id IS NULL AND episode_id IS NOT NULL)",
            name="ck_watch_events_exactly_one_target",
        ),
        CheckConstraint(
            "event_type IN ('WATCHED', 'REWATCHED', 'UNWATCHED')", name="ck_watch_events_type"
        ),
        UniqueConstraint("user_id", "idempotency_key", name="uq_watch_events_idempotency"),
        Index(
            "uq_watch_events_current_media",
            "user_id",
            "media_id",
            unique=True,
            postgresql_where=text("media_id IS NOT NULL AND episode_id IS NULL AND is_current"),
            sqlite_where=text("media_id IS NOT NULL AND episode_id IS NULL AND is_current = 1"),
        ),
        Index(
            "uq_watch_events_current_episode",
            "user_id",
            "episode_id",
            unique=True,
            postgresql_where=text("episode_id IS NOT NULL AND media_id IS NULL AND is_current"),
            sqlite_where=text("episode_id IS NOT NULL AND media_id IS NULL AND is_current = 1"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), index=True
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), index=True
    )
    watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    idempotency_key: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)

    episode: Mapped[Episode | None] = relationship(back_populates="watch_events")

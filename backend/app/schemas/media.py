from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MediaSearchResult(BaseModel):
    provider: Literal["tmdb"]
    external_id: str
    media_type: Literal["MOVIE", "TV"]
    title: str
    original_title: str | None = None
    overview: str | None = None
    release_date: date | None = None
    first_air_date: date | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    popularity: float | None = None
    tmdb_rating: float | None = None
    tmdb_vote_count: int | None = None
    original_language: str | None = None


class MediaImportRequest(BaseModel):
    provider: Literal["tmdb"] = "tmdb"
    external_id: int = Field(gt=0)
    media_type: Literal["MOVIE", "TV"]


class LibraryStatusUpdate(BaseModel):
    watch_status: Literal["PLAN_TO_WATCH", "WATCHING", "COMPLETED", "ON_HOLD", "DROPPED"]


class MediaResponse(BaseModel):
    id: UUID
    media_type: Literal["MOVIE", "TV"]
    title: str
    original_title: str | None
    overview: str | None
    release_date: date | None
    first_air_date: date | None
    poster_path: str | None
    backdrop_path: str | None
    runtime: int | None
    original_language: str | None
    popularity: float | None
    tmdb_rating: float | None
    tmdb_vote_count: int | None
    imdb_rating: float | None
    rotten_tomatoes_rating: int | None
    genres: list[str] = Field(default_factory=list)
    status: str | None

    model_config = ConfigDict(from_attributes=True)


class LibraryEntryResponse(BaseModel):
    media: MediaResponse
    watch_status: Literal["PLAN_TO_WATCH", "WATCHING", "COMPLETED", "ON_HOLD", "DROPPED"]
    added_at: datetime
    watched: bool = False
    watched_at: datetime | None = None
    personal_rating: float | None = None
    personal_review: str | None = None
    personal_notes: str | None = None


class LibraryFeedbackUpdate(BaseModel):
    personal_rating: float | None = Field(default=None, ge=1, le=10)
    personal_review: str | None = Field(default=None, max_length=10000)
    personal_notes: str | None = Field(default=None, max_length=5000)


class LibraryTitleDetailResponse(LibraryEntryResponse):
    pass


class WatchStatusUpdateRequest(BaseModel):
    watched: bool


class RewatchRequest(BaseModel):
    idempotency_key: UUID


class WatchActionResponse(BaseModel):
    watched: bool
    watched_at: datetime | None = None
    watch_status: Literal["PLAN_TO_WATCH", "WATCHING", "COMPLETED", "ON_HOLD", "DROPPED"]


class EpisodeTrackingResponse(BaseModel):
    id: UUID
    season_number: int
    episode_number: int | None
    title: str
    overview: str | None
    air_at: datetime | None
    air_date: date | None
    runtime: int | None
    still_path: str | None
    watched: bool
    watched_at: datetime | None = None


class SeasonTrackingResponse(BaseModel):
    id: UUID
    season_number: int
    name: str
    episodes: list[EpisodeTrackingResponse]
    watched_count: int
    episode_count: int


class MediaTrackingResponse(BaseModel):
    media_id: UUID
    seasons: list[SeasonTrackingResponse]
    watched_count: int
    episode_count: int
    tvmaze_available: bool


class ImportResponse(LibraryEntryResponse):
    tvmaze_id: int | None = None
    already_in_library: bool


class ExternalRatingsResponse(BaseModel):
    tmdb_id: str
    tmdb_rating: float | None = None
    tmdb_vote_count: int | None = None
    imdb_rating: float | None = None
    rotten_tomatoes_rating: int | None = None
    imdb_id: str | None = None
    omdb_configured: bool
    omdb_available: bool


class CalendarEventResponse(BaseModel):
    id: UUID
    media_id: UUID
    media_type: Literal["MOVIE", "TV"]
    title: str
    episode_title: str | None = None
    overview: str | None = None
    event_type: Literal["MOVIE_RELEASE", "EPISODE_AIRING"]
    event_date: date
    starts_at: datetime | None = None
    season_number: int | None = None
    episode_number: int | None = None
    watched: bool = False


class CalendarResponse(BaseModel):
    start: date
    end: date
    timezone: str
    events: list[CalendarEventResponse]


class CatchUpEpisodeResponse(BaseModel):
    id: UUID
    title: str
    season_number: int
    episode_number: int | None
    air_date: date


class CatchUpShowResponse(BaseModel):
    media_id: UUID
    title: str
    unwatched_count: int
    episodes: list[CatchUpEpisodeResponse]


class NotificationResponse(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str
    media_id: UUID | None
    episode_id: UUID | None
    event_date: date | None
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesResponse(BaseModel):
    release_notifications_enabled: bool = True
    timezone: str = "UTC"


class NotificationPreferencesUpdate(BaseModel):
    release_notifications_enabled: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)

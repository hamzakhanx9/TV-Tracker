import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.dependencies import (
    get_omdb_client,
    get_tmdb_client,
    get_tvmaze_client,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.errors import ProviderError
from app.integrations.omdb import OmdbClient
from app.integrations.tmdb import TmdbClient, parse_release_date
from app.integrations.tvmaze import TvmazeClient
from app.models import Episode, Media, MediaExternalId, Season, User, UserLibrary, WatchEvent
from app.schemas.media import (
    EpisodeTrackingResponse,
    ExternalRatingsResponse,
    ImportResponse,
    LibraryEntryResponse,
    LibraryFeedbackUpdate,
    LibraryStatusUpdate,
    LibraryTitleDetailResponse,
    MediaImportRequest,
    MediaSearchResult,
    MediaTrackingResponse,
    RewatchRequest,
    SeasonTrackingResponse,
    WatchActionResponse,
    WatchStatusUpdateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["media", "library"])


@router.get("/media/search", response_model=list[MediaSearchResult])
def search_media(
    q: str = Query(min_length=2, max_length=200),
    media_type: str | None = Query(default=None, pattern="^(MOVIE|TV)$"),
    tmdb: TmdbClient = Depends(get_tmdb_client),
) -> list[dict]:
    provider_type = {"MOVIE": "movie", "TV": "tv"}.get(media_type) if media_type else None
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query must contain at least two non-space characters.",
        )
    try:
        return tmdb.search(query, provider_type)
    except ProviderError as exc:
        logger.warning("Media search failed at %s: %s", exc.provider, exc)
        raise _provider_http_error(exc) from exc


@router.post(
    "/media/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_media(
    request: MediaImportRequest,
    response: Response,
    db: Session = Depends(get_db),
    tmdb: TmdbClient = Depends(get_tmdb_client),
    omdb: OmdbClient = Depends(get_omdb_client),
    tvmaze: TvmazeClient = Depends(get_tvmaze_client),
) -> ImportResponse:
    provider_type = "movie" if request.media_type == "MOVIE" else "tv"
    external_id = str(request.external_id)
    try:
        details = tmdb.get_details(provider_type, request.external_id)
        if details["external_id"] != external_id or details["media_type"] != request.media_type:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="TMDB returned metadata that did not match the requested title.",
            )
        tvmaze_id = None
        imdb_id = None
        external_ratings = None
        try:
            imdb_id = tmdb.get_imdb_id(provider_type, request.external_id)
        except ProviderError as exc:
            logger.warning("TMDB IMDb identifier lookup failed: %s", exc)
        if imdb_id:
            try:
                external_ratings = omdb.get_ratings(imdb_id)
            except ProviderError as exc:
                logger.warning("OMDb ratings lookup failed: %s", exc)
        if request.media_type == "TV" and details.get("title"):
            try:
                matched_show = tvmaze.find_matching_show(
                    details["title"], details.get("first_air_date")
                )
                if matched_show:
                    tvmaze_id = matched_show.get("id")
            except ProviderError as exc:
                logger.warning("TVmaze lookup failed during import: %s", exc)
    except ProviderError as exc:
        logger.warning("Media import metadata lookup failed at %s: %s", exc.provider, exc)
        raise _provider_http_error(exc) from exc

    try:
        with db.begin():
            existing_external = db.scalar(
                select(MediaExternalId).where(
                    MediaExternalId.provider == "tmdb",
                    MediaExternalId.external_id == external_id,
                )
            )
            media = db.get(Media, existing_external.media_id) if existing_external else None
            if media and media.media_type != request.media_type:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The provider identifier is already linked to a different media type.",
                )
            already_in_library = False

            if media is None:
                media = Media(
                    media_type=request.media_type,
                    title=details["title"],
                )
                db.add(media)
                db.flush()

            _update_metadata(media, details)
            _store_external_id(db, media.id, "tmdb", external_id)
            if imdb_id:
                _store_external_id(db, media.id, "imdb", imdb_id)
            if external_ratings:
                if external_ratings.get("imdb_rating") is not None:
                    media.imdb_rating = external_ratings["imdb_rating"]
                if external_ratings.get("rotten_tomatoes_rating") is not None:
                    media.rotten_tomatoes_rating = external_ratings["rotten_tomatoes_rating"]
            user = _get_or_create_local_user(db)
            entry = db.scalar(
                select(UserLibrary).where(
                    UserLibrary.user_id == user.id,
                    UserLibrary.media_id == media.id,
                )
            )
            if entry is None:
                entry = UserLibrary(user_id=user.id, media_id=media.id)
                db.add(entry)
            else:
                already_in_library = True
            if tvmaze_id is not None:
                if not _store_external_id(db, media.id, "tvmaze", str(tvmaze_id)):
                    tvmaze_id = None
            db.flush()
            db.refresh(media)
            db.refresh(entry)
            watch_event = db.scalar(
                select(WatchEvent).where(
                    WatchEvent.user_id == user.id,
                    WatchEvent.media_id == media.id,
                    WatchEvent.is_current.is_(True),
                )
            )

        response.status_code = (
            status.HTTP_200_OK if already_in_library else status.HTTP_201_CREATED
        )
        return ImportResponse(
            media=media,
            watch_status=entry.watch_status,
            added_at=entry.added_at,
            watched=watch_event is not None and watch_event.event_type != "UNWATCHED",
            watched_at=(
                watch_event.watched_at
                if watch_event is not None and watch_event.event_type != "UNWATCHED"
                else None
            ),
            tvmaze_id=tvmaze_id,
            already_in_library=already_in_library,
        )
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Media import violated a database constraint")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This title could not be imported because it conflicts with existing library data."
            ),
        ) from exc


@router.get("/library", response_model=list[LibraryEntryResponse])
def list_library(
    media_type: str | None = Query(default=None, pattern="^(MOVIE|TV)$"),
    db: Session = Depends(get_db),
) -> list[LibraryEntryResponse]:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        return []
    query = (
        select(UserLibrary)
        .options(joinedload(UserLibrary.media))
        .where(UserLibrary.user_id == user.id)
    )
    if media_type:
        query = query.join(UserLibrary.media).where(Media.media_type == media_type)
    entries = db.scalars(query.order_by(UserLibrary.added_at.desc())).unique().all()
    watched_events = db.scalars(
        select(WatchEvent).where(
            WatchEvent.user_id == user.id,
            WatchEvent.media_id.in_([entry.media_id for entry in entries]),
            WatchEvent.is_current.is_(True),
            WatchEvent.event_type.in_(("WATCHED", "REWATCHED")),
        )
    ).all() if entries else []
    watched_by_media = {event.media_id: event for event in watched_events}
    return [
        LibraryEntryResponse(
            media=entry.media,
            watch_status=entry.watch_status,
            added_at=entry.added_at,
            watched=entry.media_id in watched_by_media,
            watched_at=(
                watched_by_media[entry.media_id].watched_at
                if entry.media_id in watched_by_media
                else None
            ),
        )
        for entry in entries
    ]


@router.get(
    "/library/{media_id}",
    response_model=LibraryTitleDetailResponse,
)
def get_library_title_details(
    media_id: UUID,
    db: Session = Depends(get_db),
) -> LibraryTitleDetailResponse:
    return _library_title_detail_response(db, _get_library_entry(db, media_id))


@router.patch(
    "/library/{media_id}/feedback",
    response_model=LibraryTitleDetailResponse,
)
def update_library_feedback(
    media_id: UUID,
    update: LibraryFeedbackUpdate,
    db: Session = Depends(get_db),
) -> LibraryTitleDetailResponse:
    entry = _get_library_entry(db, media_id)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return _library_title_detail_response(db, entry)


@router.put(
    "/library/{media_id}/watched",
    response_model=WatchActionResponse,
)
def set_movie_watched(
    media_id: UUID,
    update: WatchStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> WatchActionResponse:
    entry = _get_library_entry(db, media_id)
    if entry.media.media_type != "MOVIE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie watch tracking is only available for movies.",
        )
    user = _get_or_create_local_user(db)
    event = db.scalar(
        select(WatchEvent).where(
            WatchEvent.user_id == user.id,
            WatchEvent.media_id == media_id,
            WatchEvent.is_current.is_(True),
        )
    )
    if update.watched:
        if event is None or event.event_type == "UNWATCHED":
            if event is not None:
                event.is_current = False
                db.flush()
            event = WatchEvent(
                user_id=user.id,
                media_id=media_id,
                watched_at=datetime.now(UTC),
                event_type="WATCHED",
                is_current=True,
            )
            db.add(event)
        entry.watch_status = "COMPLETED"
        if entry.started_at is None:
            entry.started_at = datetime.now(UTC)
        entry.completed_at = event.watched_at
    else:
        if event is not None and event.event_type != "UNWATCHED":
            event.is_current = False
            db.flush()
            db.add(
                WatchEvent(
                    user_id=user.id,
                    media_id=media_id,
                    watched_at=datetime.now(UTC),
                    event_type="UNWATCHED",
                    is_current=True,
                )
            )
        event = None
        if entry.watch_status == "COMPLETED":
            entry.watch_status = "PLAN_TO_WATCH"
        entry.completed_at = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        entry = _get_library_entry(db, media_id)
        user = _get_or_create_local_user(db)
        event = db.scalar(
            select(WatchEvent).where(
                WatchEvent.user_id == user.id,
                WatchEvent.media_id == media_id,
                WatchEvent.is_current.is_(True),
            )
        )
        is_watched = event is not None and event.event_type != "UNWATCHED"
        if is_watched == update.watched:
            return WatchActionResponse(
                watched=is_watched,
                watched_at=event.watched_at if is_watched and event else None,
                watch_status=entry.watch_status,
            )
        logger.exception("Concurrent movie watch update violated a database constraint")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie watch progress changed concurrently; refresh and try again.",
        )
    return WatchActionResponse(
        watched=update.watched,
        watched_at=event.watched_at if update.watched and event else None,
        watch_status=entry.watch_status,
    )


@router.post(
    "/library/{media_id}/rewatch",
    response_model=WatchActionResponse,
)
def rewatch_movie(
    media_id: UUID,
    request: RewatchRequest,
    db: Session = Depends(get_db),
) -> WatchActionResponse:
    entry = _get_library_entry(db, media_id)
    if entry.media.media_type != "MOVIE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie rewatch tracking is only available for movies.",
        )
    return _log_rewatch(db, entry.user_id, media_id, None, request.idempotency_key)


@router.get(
    "/library/{media_id}/episodes",
    response_model=MediaTrackingResponse,
)
def get_episode_tracking(
    media_id: UUID,
    db: Session = Depends(get_db),
) -> MediaTrackingResponse:
    entry = _get_library_entry(db, media_id)
    if entry.media.media_type != "TV":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Episode tracking is only available for TV shows.",
        )
    return _media_tracking_response(db, entry)


@router.post(
    "/library/{media_id}/episodes/sync",
    response_model=MediaTrackingResponse,
)
def sync_episode_tracking(
    media_id: UUID,
    db: Session = Depends(get_db),
    tvmaze: TvmazeClient = Depends(get_tvmaze_client),
) -> MediaTrackingResponse:
    entry = _get_library_entry(db, media_id)
    if entry.media.media_type != "TV":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Episode tracking is only available for TV shows.",
        )
    tvmaze_id = db.scalar(
        select(MediaExternalId.external_id).where(
            MediaExternalId.media_id == media_id,
            MediaExternalId.provider == "tvmaze",
        )
    )
    if tvmaze_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No TVmaze match is linked to this show, so its episodes cannot be synced.",
        )
    try:
        provider_episodes = tvmaze.get_episodes(int(tvmaze_id))
    except ProviderError as exc:
        logger.warning("TVmaze episode sync failed: %s", exc)
        raise _provider_http_error(exc) from exc

    try:
        for data in provider_episodes:
            season = db.scalar(
                select(Season).where(
                    Season.media_id == media_id,
                    Season.season_number == data["season_number"],
                )
            )
            if season is None:
                season = Season(
                    media_id=media_id,
                    season_number=data["season_number"],
                    name=(
                        "Specials"
                        if data["season_number"] == 0
                        else f"Season {data['season_number']}"
                    ),
                )
                db.add(season)
                db.flush()
            episode = db.scalar(
                select(Episode).where(Episode.tvmaze_id == data["tvmaze_id"])
            )
            if episode is not None and episode.season.media_id != media_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A TVmaze episode is already linked to a different show.",
                )
            if episode is None:
                episode = Episode(season_id=season.id, tvmaze_id=data["tvmaze_id"])
                db.add(episode)
            for field in (
                "episode_number",
                "title",
                "overview",
                "air_at",
                "air_date",
                "runtime",
                "still_path",
            ):
                value = data[field]
                if value is not None:
                    setattr(episode, field, value)
            episode.season_id = season.id
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Episode sync violated a database constraint")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Episode metadata conflicts with existing tracking data.",
        ) from exc
    return _media_tracking_response(db, _get_library_entry(db, media_id))


@router.put(
    "/episodes/{episode_id}/watched",
    response_model=WatchActionResponse,
)
def set_episode_watched(
    episode_id: UUID,
    update: WatchStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> WatchActionResponse:
    user = _get_or_create_local_user(db)
    episode = db.scalar(
        select(Episode)
        .join(Season)
        .join(UserLibrary, UserLibrary.media_id == Season.media_id)
        .where(
            Episode.id == episode_id,
            UserLibrary.user_id == user.id,
        )
    )
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    return _set_episode_watched(db, user.id, episode, update.watched)


@router.post(
    "/episodes/{episode_id}/rewatch",
    response_model=WatchActionResponse,
)
def rewatch_episode(
    episode_id: UUID,
    request: RewatchRequest,
    db: Session = Depends(get_db),
) -> WatchActionResponse:
    user = _get_or_create_local_user(db)
    episode = db.scalar(
        select(Episode)
        .join(Season)
        .join(UserLibrary, UserLibrary.media_id == Season.media_id)
        .where(
            Episode.id == episode_id,
            UserLibrary.user_id == user.id,
        )
    )
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    return _log_rewatch(
        db, user.id, None, episode.id, request.idempotency_key, episode.season.media_id
    )


@router.put(
    "/seasons/{season_id}/watched",
    response_model=MediaTrackingResponse,
)
def set_season_watched(
    season_id: UUID,
    update: WatchStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> MediaTrackingResponse:
    user = _get_or_create_local_user(db)
    season = db.scalar(
        select(Season)
        .join(UserLibrary, UserLibrary.media_id == Season.media_id)
        .where(Season.id == season_id, UserLibrary.user_id == user.id)
        .options(selectinload(Season.episodes))
    )
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    now = datetime.now(UTC)
    if update.watched:
        episodes = [episode for episode in season.episodes if _episode_has_aired(episode, now)]
    else:
        episodes = season.episodes
    episode_ids = [episode.id for episode in episodes]
    existing = db.scalars(
        select(WatchEvent).where(
            WatchEvent.user_id == user.id,
            WatchEvent.episode_id.in_(episode_ids),
            WatchEvent.is_current.is_(True),
        )
    ).all() if episode_ids else []
    existing_by_episode = {event.episode_id: event for event in existing}
    if update.watched:
        episodes_to_mark: list[Episode] = []
        for episode in episodes:
            current_event = existing_by_episode.get(episode.id)
            if current_event is None or current_event.event_type == "UNWATCHED":
                if current_event is not None:
                    current_event.is_current = False
                episodes_to_mark.append(episode)
        if episodes_to_mark:
            db.flush()
            for episode in episodes_to_mark:
                db.add(
                    WatchEvent(
                        user_id=user.id,
                        episode_id=episode.id,
                        watched_at=now,
                        event_type="WATCHED",
                        is_current=True,
                    )
                )
    else:
        events_to_clear = [event for event in existing if event.event_type != "UNWATCHED"]
        for event in events_to_clear:
            event.is_current = False
        if events_to_clear:
            db.flush()
            for event in events_to_clear:
                db.add(
                    WatchEvent(
                        user_id=user.id,
                        episode_id=event.episode_id,
                        watched_at=now,
                        event_type="UNWATCHED",
                        is_current=True,
                    )
                )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Season tracking action violated a database constraint")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Season tracking could not be updated due to conflicting watch events.",
        ) from exc
    entry = _get_library_entry(db, season.media_id)
    return _media_tracking_response(db, entry)


@router.get(
    "/media/{media_type}/{external_id}/ratings",
    response_model=ExternalRatingsResponse,
)
def get_search_ratings(
    media_type: Literal["MOVIE", "TV"],
    external_id: int = Path(gt=0),
    tmdb: TmdbClient = Depends(get_tmdb_client),
    omdb: OmdbClient = Depends(get_omdb_client),
) -> ExternalRatingsResponse:
    return _load_ratings(
        "movie" if media_type == "MOVIE" else "tv", external_id, tmdb, omdb
    )


@router.get(
    "/library/{media_id}/ratings",
    response_model=ExternalRatingsResponse,
)
def get_library_ratings(
    media_id: UUID,
    db: Session = Depends(get_db),
    tmdb: TmdbClient = Depends(get_tmdb_client),
    omdb: OmdbClient = Depends(get_omdb_client),
) -> ExternalRatingsResponse:
    entry = _get_library_entry(db, media_id)
    external = next(
        (item for item in entry.media.external_ids if item.provider == "tmdb"), None
    )
    if external is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider ratings are unavailable for this title.",
        )
    ratings = _load_ratings(
        "movie" if entry.media.media_type == "MOVIE" else "tv",
        int(external.external_id),
        tmdb,
        omdb,
    )
    if ratings.imdb_rating is None:
        ratings.imdb_rating = entry.media.imdb_rating
    if ratings.rotten_tomatoes_rating is None:
        ratings.rotten_tomatoes_rating = entry.media.rotten_tomatoes_rating
    if ratings.tmdb_rating is None:
        ratings.tmdb_rating = entry.media.tmdb_rating
    if ratings.tmdb_vote_count is None:
        ratings.tmdb_vote_count = entry.media.tmdb_vote_count
    if ratings.imdb_rating is not None:
        entry.media.imdb_rating = ratings.imdb_rating
    if ratings.rotten_tomatoes_rating is not None:
        entry.media.rotten_tomatoes_rating = ratings.rotten_tomatoes_rating
    if ratings.tmdb_rating is not None:
        entry.media.tmdb_rating = ratings.tmdb_rating
    if ratings.tmdb_vote_count is not None:
        entry.media.tmdb_vote_count = ratings.tmdb_vote_count
    db.commit()
    return ratings


@router.patch("/library/{media_id}", response_model=LibraryEntryResponse)
def update_library_status(
    media_id: UUID,
    update: LibraryStatusUpdate,
    db: Session = Depends(get_db),
) -> LibraryEntryResponse:
    entry = _get_library_entry(db, media_id)
    entry.watch_status = update.watch_status
    if update.watch_status == "WATCHING" and entry.started_at is None:
        entry.started_at = datetime.now(UTC)
    if update.watch_status == "COMPLETED" and entry.started_at is None:
        entry.started_at = datetime.now(UTC)
    if update.watch_status == "COMPLETED" and entry.completed_at is None:
        entry.completed_at = datetime.now(UTC)
    if update.watch_status != "COMPLETED":
        entry.completed_at = None
    db.commit()
    db.refresh(entry)
    return _library_entry_response(db, entry)


@router.delete("/library/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_library(media_id: UUID, db: Session = Depends(get_db)) -> Response:
    entry = _get_library_entry(db, media_id)
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_library_entry(db: Session, media_id: UUID) -> UserLibrary:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found")
    entry = db.scalar(
        select(UserLibrary)
        .options(joinedload(UserLibrary.media))
        .where(UserLibrary.user_id == user.id, UserLibrary.media_id == media_id)
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found")
    return entry


def _library_entry_response(db: Session, entry: UserLibrary) -> LibraryEntryResponse:
    event = db.scalar(
        select(WatchEvent).where(
            WatchEvent.user_id == entry.user_id,
            WatchEvent.media_id == entry.media_id,
            WatchEvent.is_current.is_(True),
        )
    )
    watched = event is not None and event.event_type != "UNWATCHED"
    return LibraryEntryResponse(
        media=entry.media,
        watch_status=entry.watch_status,
        added_at=entry.added_at,
        watched=watched,
        watched_at=event.watched_at if watched and event else None,
    )


def _library_title_detail_response(
    db: Session, entry: UserLibrary
) -> LibraryTitleDetailResponse:
    library_response = _library_entry_response(db, entry)
    return LibraryTitleDetailResponse(
        **library_response.model_dump(),
        personal_rating=entry.personal_rating,
        personal_review=entry.personal_review,
        personal_notes=entry.personal_notes,
    )


def _media_tracking_response(db: Session, entry: UserLibrary) -> MediaTrackingResponse:
    seasons = db.scalars(
        select(Season)
        .where(Season.media_id == entry.media_id)
        .options(selectinload(Season.episodes))
        .order_by(Season.season_number)
    ).all()
    episode_ids = [episode.id for season in seasons for episode in season.episodes]
    watch_events = db.scalars(
        select(WatchEvent).where(
            WatchEvent.user_id == entry.user_id,
            WatchEvent.episode_id.in_(episode_ids),
            WatchEvent.is_current.is_(True),
            WatchEvent.event_type.in_(("WATCHED", "REWATCHED")),
        )
    ).all() if episode_ids else []
    events_by_episode = {event.episode_id: event for event in watch_events}
    season_responses: list[SeasonTrackingResponse] = []
    for season in seasons:
        season_episodes = sorted(
            season.episodes,
            key=lambda episode: (
                episode.episode_number is None,
                episode.episode_number or 0,
                episode.title.casefold(),
            ),
        )
        episode_responses = [
            EpisodeTrackingResponse(
                id=episode.id,
                season_number=season.season_number,
                episode_number=episode.episode_number,
                title=episode.title,
                overview=episode.overview,
                air_at=episode.air_at,
                air_date=episode.air_date,
                runtime=episode.runtime,
                still_path=episode.still_path,
                watched=episode.id in events_by_episode,
                watched_at=(
                    events_by_episode[episode.id].watched_at
                    if episode.id in events_by_episode
                    else None
                ),
            )
            for episode in season_episodes
        ]
        season_responses.append(
            SeasonTrackingResponse(
                id=season.id,
                season_number=season.season_number,
                name=season.name,
                episodes=episode_responses,
                watched_count=sum(item.watched for item in episode_responses),
                episode_count=len(episode_responses),
            )
        )
    return MediaTrackingResponse(
        media_id=entry.media_id,
        seasons=season_responses,
        watched_count=len(events_by_episode),
        episode_count=len(episode_ids),
        tvmaze_available=any(
            external.provider == "tvmaze" for external in entry.media.external_ids
        ),
    )


def _set_episode_watched(
    db: Session, user_id: UUID, episode: Episode, watched: bool
) -> WatchActionResponse:
    event = db.scalar(
        select(WatchEvent).where(
            WatchEvent.user_id == user_id,
            WatchEvent.episode_id == episode.id,
            WatchEvent.is_current.is_(True),
        )
    )
    if watched and (event is None or event.event_type == "UNWATCHED"):
        if event is not None:
            event.is_current = False
            db.flush()
        event = WatchEvent(
            user_id=user_id,
            episode_id=episode.id,
            watched_at=datetime.now(UTC),
            event_type="WATCHED",
            is_current=True,
        )
        db.add(event)
    elif not watched and event is not None and event.event_type != "UNWATCHED":
        event.is_current = False
        db.flush()
        db.add(
            WatchEvent(
                user_id=user_id,
                episode_id=episode.id,
                watched_at=datetime.now(UTC),
                event_type="UNWATCHED",
                is_current=True,
            )
        )
        event = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        event = db.scalar(
            select(WatchEvent).where(
                WatchEvent.user_id == user_id,
                WatchEvent.episode_id == episode.id,
                WatchEvent.is_current.is_(True),
            )
        )
        is_watched = event is not None and event.event_type != "UNWATCHED"
        if is_watched == watched:
            library_entry = _get_library_entry(db, episode.season.media_id)
            return WatchActionResponse(
                watched=is_watched,
                watched_at=event.watched_at if is_watched and event else None,
                watch_status=library_entry.watch_status,
            )
        logger.exception("Concurrent episode watch update violated a database constraint")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Episode watch progress changed concurrently; refresh and try again.",
        )
    library_entry = _get_library_entry(db, episode.season.media_id)
    return WatchActionResponse(
        watched=watched,
        watched_at=event.watched_at if watched and event else None,
        watch_status=library_entry.watch_status,
    )


def _log_rewatch(
    db: Session,
    user_id: UUID,
    media_id: UUID | None,
    episode_id: UUID | None,
    idempotency_key: UUID,
    library_media_id: UUID | None = None,
) -> WatchActionResponse:
    if (media_id is None) == (episode_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rewatch event must target exactly one movie or episode.",
        )
    target_media_id = media_id or library_media_id
    if target_media_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rewatch event must belong to a library title.",
        )
    existing_request = db.scalar(
        select(WatchEvent).where(
            WatchEvent.user_id == user_id,
            WatchEvent.idempotency_key == idempotency_key,
        )
    )
    if existing_request is not None and (
        existing_request.media_id != media_id or existing_request.episode_id != episode_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This rewatch request key was already used for a different title.",
        )
    target_filter = (
        (WatchEvent.media_id == media_id) & WatchEvent.episode_id.is_(None)
        if media_id is not None
        else (WatchEvent.media_id.is_(None) & (WatchEvent.episode_id == episode_id))
    )
    current_event = db.scalar(
        select(WatchEvent).where(
            WatchEvent.user_id == user_id,
            target_filter,
            WatchEvent.is_current.is_(True),
        )
    )
    if existing_request is None:
        if current_event is None or current_event.event_type == "UNWATCHED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mark this title watched before logging a rewatch.",
            )
        current_event.is_current = False
        db.flush()
        db.add(
            WatchEvent(
                user_id=user_id,
                media_id=media_id,
                episode_id=episode_id,
                watched_at=datetime.now(UTC),
                event_type="REWATCHED",
                is_current=True,
                idempotency_key=idempotency_key,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing_request = db.scalar(
                select(WatchEvent).where(
                    WatchEvent.user_id == user_id,
                    WatchEvent.idempotency_key == idempotency_key,
                )
            )
            if existing_request is None or (
                existing_request.media_id != media_id
                or existing_request.episode_id != episode_id
            ):
                logger.exception("Rewatch update violated a database constraint")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Rewatch tracking changed concurrently; retry with a new request key.",
                )
    else:
        db.rollback()
    current_event = db.scalar(
        select(WatchEvent).where(
            WatchEvent.user_id == user_id,
            target_filter,
            WatchEvent.is_current.is_(True),
        )
    )
    entry = _get_library_entry(db, target_media_id)
    is_watched = current_event is not None and current_event.event_type != "UNWATCHED"
    return WatchActionResponse(
        watched=is_watched,
        watched_at=current_event.watched_at if is_watched and current_event else None,
        watch_status=entry.watch_status,
    )


def _episode_has_aired(episode: Episode, now: datetime) -> bool:
    if episode.air_at is not None:
        air_at = episode.air_at
        if air_at.tzinfo is None:
            air_at = air_at.replace(tzinfo=UTC)
        return air_at <= now
    return episode.air_date is not None and episode.air_date <= now.date()


def _load_ratings(
    media_type: str,
    external_id: int,
    tmdb: TmdbClient,
    omdb: OmdbClient,
) -> ExternalRatingsResponse:
    try:
        details = tmdb.get_details(media_type, external_id)
    except ProviderError as exc:
        logger.warning("Could not retrieve TMDB ratings: %s", exc)
        raise _provider_http_error(exc) from exc

    imdb_id = None
    imdb_rating = None
    rotten_tomatoes_rating = None
    omdb_available = not omdb.configured
    try:
        imdb_id = tmdb.get_imdb_id(media_type, external_id)
    except ProviderError as exc:
        logger.warning("TMDB IMDb identifier lookup failed: %s", exc)
    if imdb_id:
        try:
            ratings = omdb.get_ratings(imdb_id)
            if ratings:
                imdb_rating = ratings["imdb_rating"]
                rotten_tomatoes_rating = ratings["rotten_tomatoes_rating"]
                omdb_available = True
        except ProviderError as exc:
            logger.warning("OMDb ratings lookup failed: %s", exc)
    return ExternalRatingsResponse(
        tmdb_id=str(external_id),
        tmdb_rating=details.get("tmdb_rating"),
        tmdb_vote_count=details.get("tmdb_vote_count"),
        imdb_rating=imdb_rating,
        rotten_tomatoes_rating=rotten_tomatoes_rating,
        imdb_id=imdb_id,
        omdb_configured=omdb.configured,
        omdb_available=omdb_available,
    )


def _get_or_create_local_user(db: Session) -> User:
    email = get_settings().default_user_email
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
        db.flush()
    return user


def _update_metadata(media: Media, details: dict) -> None:
    media.media_type = details["media_type"]
    media.title = details["title"]
    optional_metadata = {
        "original_title": details.get("original_title"),
        "overview": details.get("overview"),
        "release_date": parse_release_date(details.get("release_date")),
        "first_air_date": parse_release_date(details.get("first_air_date")),
        "poster_path": details.get("poster_path"),
        "backdrop_path": details.get("backdrop_path"),
        "runtime": details.get("runtime"),
        "original_language": details.get("original_language"),
        "popularity": details.get("popularity"),
        "tmdb_rating": details.get("tmdb_rating"),
        "tmdb_vote_count": details.get("tmdb_vote_count"),
        "status": details.get("status"),
    }
    for field, value in optional_metadata.items():
        if value is not None:
            setattr(media, field, value)


def _store_external_id(
    db: Session, media_id: UUID, provider: str, external_id: str
) -> bool:
    existing = db.scalar(
        select(MediaExternalId).where(
            MediaExternalId.provider == provider,
            MediaExternalId.external_id == external_id,
        )
    )
    if existing is None:
        db.add(MediaExternalId(media_id=media_id, provider=provider, external_id=external_id))
        return True
    elif existing.media_id == media_id:
        existing.last_synced_at = datetime.now(UTC)
        return True
    else:
        logger.warning(
            "Provider identifier %s:%s is already linked to another title",
            provider,
            external_id,
        )
        return False


def _provider_http_error(exc: ProviderError) -> HTTPException:
    if exc.not_found:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=(
            status.HTTP_503_SERVICE_UNAVAILABLE
            if exc.unavailable
            else status.HTTP_502_BAD_GATEWAY
        ),
        detail=str(exc),
    )

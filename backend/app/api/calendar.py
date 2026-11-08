from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Episode, Season, User, UserLibrary, WatchEvent
from app.schemas.media import CalendarEventResponse, CalendarResponse

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.get("", response_model=CalendarResponse)
def get_calendar(
    start: date,
    end: date,
    timezone: str = Query(default="UTC", min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> CalendarResponse:
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Calendar start date must be on or before its end date.",
        )
    if (end - start).days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Calendar ranges cannot exceed 367 days.",
        )
    try:
        user_timezone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested timezone is not a valid IANA timezone.",
        ) from exc

    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        return CalendarResponse(start=start, end=end, timezone=timezone, events=[])
    entries = db.scalars(
        select(UserLibrary)
        .options(joinedload(UserLibrary.media))
        .where(UserLibrary.user_id == user.id)
    ).unique().all()
    media_by_id = {entry.media_id: entry.media for entry in entries}
    tv_media_ids = [
        media_id for media_id, media in media_by_id.items() if media.media_type == "TV"
    ]
    events: list[CalendarEventResponse] = []

    for media in media_by_id.values():
        if (
            media.media_type == "MOVIE"
            and media.release_date
            and start <= media.release_date <= end
        ):
            events.append(
                CalendarEventResponse(
                    id=media.id,
                    media_id=media.id,
                    media_type="MOVIE",
                    title=media.title,
                    overview=media.overview,
                    event_type="MOVIE_RELEASE",
                    event_date=media.release_date,
                )
            )

    watched_episode_ids: set[UUID] = set()
    if tv_media_ids:
        episodes = db.scalars(
            select(Episode)
            .join(Season)
            .where(Season.media_id.in_(tv_media_ids))
            .options(joinedload(Episode.season))
        ).unique().all()
        airing_episodes: list[tuple[Episode, date, datetime | None]] = []
        episode_ids = [episode.id for episode in episodes]
        if episode_ids:
            current_events = db.scalars(
                select(WatchEvent).where(
                    WatchEvent.user_id == user.id,
                    WatchEvent.episode_id.in_(episode_ids),
                    WatchEvent.is_current.is_(True),
                    WatchEvent.event_type.in_(("WATCHED", "REWATCHED")),
                )
            ).all()
            watched_episode_ids = {event.episode_id for event in current_events}
        for episode in episodes:
            local_airing = _local_airing(episode.air_at, episode.air_date, user_timezone)
            if local_airing is None:
                continue
            event_date, starts_at = local_airing
            if start <= event_date <= end:
                airing_episodes.append((episode, event_date, starts_at))
        for episode, event_date, starts_at in airing_episodes:
            media = media_by_id[episode.season.media_id]
            events.append(
                CalendarEventResponse(
                    id=episode.id,
                    media_id=media.id,
                    media_type="TV",
                    title=(
                        f"{media.title}: S{episode.season.season_number:02d}"
                        f"E{episode.episode_number:02d}"
                        if episode.episode_number is not None
                        else f"{media.title}: S{episode.season.season_number:02d}E??"
                    ),
                    episode_title=episode.title,
                    overview=episode.overview,
                    event_type="EPISODE_AIRING",
                    event_date=event_date,
                    starts_at=starts_at,
                    season_number=episode.season.season_number,
                    episode_number=episode.episode_number,
                    watched=episode.id in watched_episode_ids,
                )
            )

    events.sort(
        key=lambda event: (
            event.event_date,
            event.starts_at is not None,
            event.starts_at or datetime.min.replace(tzinfo=user_timezone),
            event.title.casefold(),
        )
    )
    return CalendarResponse(start=start, end=end, timezone=timezone, events=events)


def _local_airing(
    air_at: datetime | None,
    air_date: date | None,
    timezone: ZoneInfo,
) -> tuple[date, datetime | None] | None:
    if air_at is not None:
        if air_at.tzinfo is None:
            air_at = air_at.replace(tzinfo=UTC)
        local_time = air_at.astimezone(timezone)
        return local_time.date(), local_time
    if air_date is not None:
        return air_date, None
    return None

from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Episode, Season, User, UserLibrary, WatchEvent
from app.schemas.media import CatchUpEpisodeResponse, CatchUpShowResponse

router = APIRouter(prefix="/api/v1/catch-up", tags=["catch-up"])


@router.get("", response_model=list[CatchUpShowResponse])
def get_catch_up(
    timezone: str = Query(default="UTC", min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> list[CatchUpShowResponse]:
    try:
        user_timezone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested timezone is not a valid IANA timezone.",
        ) from exc

    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        return []
    entries = db.scalars(
        select(UserLibrary)
        .options(joinedload(UserLibrary.media))
        .where(UserLibrary.user_id == user.id, UserLibrary.watch_status == "WATCHING")
    ).unique().all()
    media_by_id = {entry.media_id: entry.media for entry in entries}
    if not media_by_id:
        return []

    episodes = db.scalars(
        select(Episode)
        .join(Season)
        .where(Season.media_id.in_(media_by_id))
        .options(joinedload(Episode.season))
    ).unique().all()
    episode_ids = [episode.id for episode in episodes]
    watched_ids: set[UUID] = set()
    if episode_ids:
        watched_events = db.scalars(
            select(WatchEvent).where(
                WatchEvent.user_id == user.id,
                WatchEvent.episode_id.in_(episode_ids),
                WatchEvent.is_current.is_(True),
                WatchEvent.event_type.in_(("WATCHED", "REWATCHED")),
            )
        ).all()
        watched_ids = {event.episode_id for event in watched_events}

    now = datetime.now(UTC)
    local_today = now.astimezone(user_timezone).date()
    episodes_by_media: dict[UUID, list[tuple[Episode, date]]] = {}
    for episode in episodes:
        if episode.id in watched_ids:
            continue
        if episode.air_at is not None:
            air_at = episode.air_at
            if air_at.tzinfo is None:
                air_at = air_at.replace(tzinfo=UTC)
            local_air = air_at.astimezone(user_timezone)
            if air_at.astimezone(UTC) > now:
                continue
            aired_date = local_air.date()
        elif episode.air_date is not None and episode.air_date <= local_today:
            aired_date = episode.air_date
        else:
            continue
        episodes_by_media.setdefault(episode.season.media_id, []).append(
            (episode, aired_date)
        )

    shows: list[CatchUpShowResponse] = []
    for media_id, missed in episodes_by_media.items():
        media = media_by_id[media_id]
        missed.sort(
            key=lambda item: (
                item[1],
                item[0].season.season_number,
                item[0].episode_number or 0,
            )
        )
        shows.append(
            CatchUpShowResponse(
                media_id=media_id,
                title=media.title,
                unwatched_count=len(missed),
                episodes=[
                    CatchUpEpisodeResponse(
                        id=episode.id,
                        title=episode.title,
                        season_number=episode.season.season_number,
                        episode_number=episode.episode_number,
                        air_date=aired_date,
                    )
                    for episode, aired_date in missed
                ],
            )
        )
    return sorted(shows, key=lambda show: (-show.unwatched_count, show.title.casefold()))

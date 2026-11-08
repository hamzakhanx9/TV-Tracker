import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Episode,
    Notification,
    NotificationPreference,
    Season,
    User,
    UserLibrary,
)

logger = logging.getLogger(__name__)


def generate_notifications(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise ValueError("Notification generation requires a timezone-aware timestamp.")
    current_time = current_time.astimezone(UTC)
    created_count = 0

    users = db.scalars(select(User)).all()
    for user in users:
        preferences = db.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
        timezone = ZoneInfo(preferences.timezone if preferences else "UTC")
        local_today = current_time.astimezone(timezone).date()
        entries = db.scalars(
            select(UserLibrary)
            .options(joinedload(UserLibrary.media))
            .where(
                UserLibrary.user_id == user.id,
                UserLibrary.watch_status == "WATCHING",
            )
        ).unique().all()
        media_by_id = {entry.media_id: entry.media for entry in entries}

        tv_ids = [media_id for media_id, media in media_by_id.items() if media.media_type == "TV"]
        if not tv_ids:
            continue
        episodes = db.scalars(
            select(Episode)
            .join(Season)
            .where(Season.media_id.in_(tv_ids))
            .options(joinedload(Episode.season))
        ).unique().all()
        episode_notifications: dict[UUID, tuple[str, date]] = {}
        for episode in episodes:
            if episode.air_at is not None:
                air_at = episode.air_at
                if air_at.tzinfo is None:
                    air_at = air_at.replace(tzinfo=UTC)
                local_air = air_at.astimezone(timezone)
                if air_at > current_time:
                    episode_notifications[episode.id] = ("EPISODE_ANNOUNCED", local_air.date())
                elif air_at >= current_time - timedelta(hours=48):
                    episode_notifications[episode.id] = ("EPISODE_RELEASE", local_air.date())
            elif episode.air_date is not None:
                if episode.air_date > local_today:
                    episode_notifications[episode.id] = (
                        "EPISODE_ANNOUNCED",
                        episode.air_date,
                    )
                elif episode.air_date >= local_today - timedelta(days=1):
                    episode_notifications[episode.id] = ("EPISODE_RELEASE", episode.air_date)
        if not episode_notifications:
            continue

        for episode in episodes:
            notification = episode_notifications.get(episode.id)
            if notification is None:
                continue
            media = media_by_id[episode.season.media_id]
            kind, event_date = notification
            episode_label = (
                f"S{episode.season.season_number:02d}E{episode.episode_number:02d}"
                if episode.episode_number is not None
                else f"S{episode.season.season_number:02d}E??"
            )
            if preferences is None or preferences.release_notifications_enabled:
                is_announcement = kind == "EPISODE_ANNOUNCED"
                created_count += _create_notification(
                    db,
                    user.id,
                    f"episode-{kind.lower()}:{episode.id}",
                    kind,
                    (
                        f"New episode announced for {media.title}"
                        if is_announcement
                        else f"New episode of {media.title}"
                    ),
                    (
                        f"{media.title}: {episode_label} · {episode.title} is scheduled for "
                        f"{event_date.isoformat()}."
                        if is_announcement
                        else (
                            f"{media.title}: {episode_label} · {episode.title} is now available "
                            f"(aired {event_date.isoformat()})."
                        )
                    ),
                    media.id,
                    episode.id,
                    event_date,
                )
    db.commit()
    logger.info("Generated %d FRAME notification(s)", created_count)
    return created_count


def _create_notification(
    db: Session,
    user_id: UUID,
    dedupe_key: str,
    kind: str,
    title: str,
    body: str,
    media_id: UUID | None,
    episode_id: UUID | None,
    event_date: date,
) -> int:
    if db.scalar(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.dedupe_key == dedupe_key,
        )
    ):
        return 0
    try:
        with db.begin_nested():
            db.add(
                Notification(
                    user_id=user_id,
                    dedupe_key=dedupe_key,
                    kind=kind,
                    title=title,
                    body=body,
                    media_id=media_id,
                    episode_id=episode_id,
                    event_date=event_date,
                )
            )
            db.flush()
    except IntegrityError:
        if not db.scalar(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.dedupe_key == dedupe_key,
            )
        ):
            raise
        return 0
    return 1

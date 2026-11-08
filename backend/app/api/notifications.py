from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Notification, NotificationPreference, User, UserLibrary
from app.schemas.media import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
)

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Notification]:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        return []
    watching_media_ids = select(UserLibrary.media_id).where(
        UserLibrary.user_id == user.id,
        UserLibrary.watch_status == "WATCHING",
    )
    query = select(Notification).where(
        Notification.user_id == user.id,
        Notification.media_id.in_(watching_media_ids),
        Notification.kind.in_(("EPISODE_ANNOUNCED", "EPISODE_RELEASE")),
        Notification.cleared_at.is_(None),
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    return list(
        db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)).all()
    )


@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> Notification:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    notification = (
        db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
                Notification.cleared_at.is_(None),
            )
        )
        if user
        else None
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    result = db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.cleared_at.is_(None),
        )
        .values(cleared_at=datetime.now(UTC))
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    db.commit()


@router.delete("/notifications", status_code=status.HTTP_200_OK)
def clear_all_notifications(db: Session = Depends(get_db)) -> dict[str, int]:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    if user is None:
        return {"cleared_count": 0}
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.cleared_at.is_(None))
        .values(cleared_at=datetime.now(UTC))
    )
    db.commit()
    return {"cleared_count": result.rowcount or 0}


@router.get("/notification-preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
) -> NotificationPreferencesResponse:
    user = db.scalar(select(User).where(User.email == get_settings().default_user_email))
    preferences = (
        db.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
        if user
        else None
    )
    return NotificationPreferencesResponse(
        release_notifications_enabled=(
            preferences.release_notifications_enabled if preferences else True
        ),
        timezone=preferences.timezone if preferences else "UTC",
    )


@router.patch(
    "/notification-preferences",
    response_model=NotificationPreferencesResponse,
)
def update_notification_preferences(
    request: NotificationPreferencesUpdate,
    db: Session = Depends(get_db),
) -> NotificationPreferencesResponse:
    updates = request.model_dump(exclude_unset=True)
    timezone = updates.get("timezone")
    if timezone is not None:
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The requested timezone is not a valid IANA timezone.",
            ) from exc

    email = get_settings().default_user_email
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
        db.flush()
    preferences = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    if preferences is None:
        preferences = NotificationPreference(user_id=user.id)
        db.add(preferences)
    for field, value in updates.items():
        if value is not None:
            setattr(preferences, field, value)
    db.commit()
    db.refresh(preferences)
    return NotificationPreferencesResponse(
        release_notifications_enabled=preferences.release_notifications_enabled,
        timezone=preferences.timezone,
    )

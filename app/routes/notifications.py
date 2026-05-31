from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_business, get_current_user
from ..models import Notification, User
from ..schemas import NotificationCreateRequest
from ..serializers import notification_payload
from ..utils import make_id

router = APIRouter(prefix="/notifications", tags=["notifications"])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def user_notification_items(user: User, db: Session) -> list[Notification]:
    return list(db.scalars(select(Notification).where(Notification.recipient_user_id == user.id).order_by(Notification.created_at.desc())))


@router.get("")
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": [notification_payload(notification) for notification in user_notification_items(current_user, db)]}


@router.post("")
def create_notification_from_business(payload: NotificationCreateRequest, current_business=Depends(get_current_business), db: Session = Depends(get_db)):
    recipient = db.get(User, payload.recipient_user_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient user not found")
    notification = Notification(
        id=make_id("note"),
        recipient_user_id=payload.recipient_user_id,
        type=payload.type,
        title=payload.title,
        message=payload.message,
        read=False,
    )
    del current_business
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return {"notification": notification_payload(notification)}


@router.get("/unread-count")
def unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = sum(1 for notification in user_notification_items(current_user, db) if not notification.read)
    return {"count": count}


@router.patch("/{notification_id}/read")
def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.get(Notification, notification_id)
    if not notification or notification.recipient_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    notification.read_at = utcnow()
    db.commit()
    return {"notification": notification_payload(notification)}


@router.patch("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for notification in user_notification_items(current_user, db):
        notification.read = True
        notification.read_at = utcnow()
    db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
def delete_notification(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.get(Notification, notification_id)
    if not notification or notification.recipient_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted"}

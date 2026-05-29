from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.dependencies import get_current_user, get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationOut
from app.models.user import User
from uuid import UUID

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationOut])
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch all notifications for the current user, newest first."""
    notifications = db.query(Notification)\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.created_at.desc())\
        .all()
    return notifications

@router.patch("/{notification_id}/read", status_code=204)
def mark_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a specific notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()

@router.patch("/read-all", status_code=204)
def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all unread notifications for the current user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()

@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific notification."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notif)
    db.commit()

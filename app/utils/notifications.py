from sqlalchemy.orm import Session
from app.models.notification import Notification
from uuid import UUID

def create_notification(
    db: Session,
    user_id: UUID,
    title: str,
    message: str,
    notif_type: str = "info"
):
    """
    Utility to create a notification in the database.
    notif_type can be: info, success, warning, danger
    """
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

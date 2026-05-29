from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"

class NotificationCreate(NotificationBase):
    user_id: UUID

class NotificationOut(NotificationBase):
    id: UUID
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# app/schemas/chat.py

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class ChatMessageCreate(BaseModel):
    message: str

class ChatMessageOut(BaseModel):
    id: UUID
    booking_id: UUID
    sender_id: UUID
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

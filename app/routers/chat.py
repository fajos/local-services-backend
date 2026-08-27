# app/routers/chat.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.dependencies import get_db, get_current_user
from app.models.message import ChatMessage
from app.models.booking import Booking
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatMessageCreate

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/{booking_id}", response_model=List[ChatMessageOut])
def get_messages(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify user is part of the booking
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Check if user is customer or provider owner
    is_customer = booking.customer_id == current_user.id

    # Need to check provider owner
    from app.models.provider import Provider
    from app.models.service import Service

    service = db.query(Service).filter(Service.id == booking.service_id).first()
    provider = db.query(Provider).filter(Provider.id == service.provider_id).first()
    is_provider = provider.user_id == current_user.id

    if not (is_customer or is_provider):
        raise HTTPException(status_code=403, detail="Not authorized to view this chat")

    messages = db.query(ChatMessage)\
        .filter(ChatMessage.booking_id == booking_id)\
        .order_by(ChatMessage.created_at.asc())\
        .all()
    return messages

@router.post("/{booking_id}", response_model=ChatMessageOut)
def send_message(
    booking_id: UUID,
    msg_in: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    from app.models.provider import Provider
    from app.models.service import Service

    service = db.query(Service).filter(Service.id == booking.service_id).first()
    provider = db.query(Provider).filter(Provider.id == service.provider_id).first()

    if current_user.id != booking.customer_id and current_user.id != provider.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to send messages to this booking")

    db_msg = ChatMessage(
        booking_id=booking_id,
        sender_id=current_user.id,
        message=msg_in.message
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

# app/models/booking.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.enums import BookingStatus, QuoteStatus, VisitStatus, PaymentStatus


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    note = Column(Text, nullable=True)

    booking_status = Column(Enum(BookingStatus), default=BookingStatus.pending)
    quote_price = Column(Integer, nullable=True)
    quote_status = Column(Enum(QuoteStatus), default=QuoteStatus.pending)
    admin_released = Column(Boolean, default=False)
    city_or_lga = Column(String(120), nullable=True)

    visit_required = Column(Boolean, default=False)
    visit_status = Column(Enum(VisitStatus), default=VisitStatus.not_started)

    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.unpaid)
    created_at = Column(DateTime, default=datetime.utcnow)

    service = relationship("Service", back_populates="bookings")
    customer = relationship("User", back_populates="bookings")
    payout_txn_id  = Column(String, nullable=True)

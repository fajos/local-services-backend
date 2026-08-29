# app/models/review.py
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

class Review(Base):
    __tablename__ = "reviews"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id   = Column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    provider_id  = Column(UUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    customer_id  = Column(UUID(as_uuid=True), ForeignKey("users.id",      ondelete="SET NULL"))
    rating       = Column(Integer, nullable=False)      # 1‑5
    comment      = Column(Text, nullable=True)

    provider_response = Column(Text, nullable=True)
    responded_at      = Column(DateTime, nullable=True)

    created_at   = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider", back_populates="reviews")
    customer = relationship("User", foreign_keys=[customer_id])
    booking  = relationship("Booking")

class CustomerReview(Base):
    """Providers rating customers"""
    __tablename__ = "customer_reviews"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id   = Column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    provider_id  = Column(UUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    customer_id  = Column(UUID(as_uuid=True), ForeignKey("users.id",      ondelete="CASCADE"), nullable=False)

    rating       = Column(Integer, nullable=False)      # 1-5
    comment      = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider")
    customer = relationship("User", foreign_keys=[customer_id])
    booking  = relationship("Booking")

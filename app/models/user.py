# app/models/user.py

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(255), nullable=True)
    is_identity_verified = Column(Boolean, default=False)
    id_type = Column(String(50), nullable=True) # e.g. NIN, Driver's License
    id_number = Column(String(100), nullable=True)
    id_photo_url = Column(String, nullable=True)
    identity_status = Column(String(20), default="unverified") # unverified, pending, verified, rejected
    is_provider = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_email_confirmed        = Column(Boolean, default=False, nullable=False)
    is_phone_confirmed        = Column(Boolean, default=False, nullable=False)
    phone_confirmation_code   = Column(String, nullable=True)
    phone_confirmation_expires_at = Column(DateTime, nullable=True)

    # One-to-one with Provider (if upgraded)
    provider = relationship("Provider", back_populates="user", uselist=False)

    # One-to-many relationship with Booking (as customer)
    bookings = relationship("Booking", back_populates="customer")
    is_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)

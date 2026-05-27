# app/models/provider.py

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

class Provider(Base):
    __tablename__ = "providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    business_name = Column(String, nullable=False)
    business_address = Column(String, nullable=False)
    business_phone = Column(String, nullable=False)
    business_email = Column(String, nullable=True)
    open_hours = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    average_rating  = Column(Integer, nullable=True)  # store as *hundredths* e.g. 453 = 4.53
    reviews_count   = Column(Integer, default=0)

    user = relationship("User", back_populates="provider")
    services = relationship("Service", back_populates="provider")
    stripe_account     = Column(String, nullable=True)   # acct_123...
    paystack_recipient = Column(String, nullable=True)   # RCP_xyz..
    reviews = relationship("Review", back_populates="provider", cascade="all, delete-orphan")
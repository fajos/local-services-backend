# app/models/service.py

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.enums import PriceType


class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Integer, nullable=True)
    price_type = Column(Enum(PriceType), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider", back_populates="services")
    bookings = relationship("Booking", back_populates="service")


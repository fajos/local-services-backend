# app/schemas/booking.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.enums import BookingStatus, QuoteStatus, VisitStatus, PaymentStatus
from typing import Optional

class BookingCreate(BaseModel):
    service_id: UUID
    note: str | None = None
    city_or_lga: str = Field(..., min_length=2, max_length=120) 
    visit_required: bool = False
    scheduled_at: Optional[datetime] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None

    is_recurring: bool = False
    frequency: Optional[str] = "once"


class BookingOut(BaseModel):
    id: UUID
    service_id: UUID
    customer_id: UUID
    note: str | None = None
    booking_status: BookingStatus
    quote_price: int | None = None
    quote_status: QuoteStatus
    visit_required: bool
    visit_status: VisitStatus
    payment_status: PaymentStatus
    created_at: datetime
    city_or_lga: str | None = None  

    scheduled_at: datetime | None = None
    latitude: str | None = None
    longitude: str | None = None

    is_disputed: bool = False
    dispute_reason: str | None = None
    dispute_status: str | None = None

    is_recurring: bool = False
    frequency: str | None = None

    class Config:
        from_attributes = True

class CustomerContact(BaseModel):
    phone: str
    address: str | None = None

class BookingOutExtended(BookingOut):
    service_name: str
    service_category: str
    customer_name: str
    admin_released: bool = False
    customer_info: Optional[CustomerContact] = None
    provider_name: str 
    has_customer_review: bool = False

class BookingCustomerOut(BookingOut):
    service_name: str
    service_category: str
    provider_name: str
    provider_business_name: str | None = None
    has_review: bool = False

class RescheduleRequest(BaseModel):
    new_date: datetime
    reason: str | None = None

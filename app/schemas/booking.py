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

    class Config:
        from_attributes = True

class CustomerContact(BaseModel):
    phone: str
    address: str | None = None

class BookingOutExtended(BookingOut):
    service_name: str
    service_category: str
    customer_name: str
    admin_released: bool = False   # default ⇒ no validation erro
    customer_info: Optional[CustomerContact] = None
    provider_name: str 

class BookingCustomerOut(BookingOut):
    service_name: str
    service_category: str       # NEW
    provider_name: str

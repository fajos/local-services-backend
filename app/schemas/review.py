# app/schemas/review.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

# app/schemas/review.py
class ReviewCreate(BaseModel):
    booking_id: UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None

class ReviewRespond(BaseModel):
    response: str

class ReviewOut(BaseModel):
    id: UUID
    booking_id: UUID
    rating: int
    comment: str | None
    provider_response: str | None = None
    responded_at: datetime | None = None
    created_at: datetime
    customer_name: str
    service_name: str | None = None

    class Config:
        from_attributes = True

class CustomerReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None

class CustomerReviewOut(BaseModel):
    id: UUID
    booking_id: UUID
    rating: int
    comment: str | None
    created_at: datetime
    provider_name: str

    class Config:
        from_attributes = True


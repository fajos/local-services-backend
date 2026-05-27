# app/schemas/review.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

# app/schemas/review.py
class ReviewCreate(BaseModel):
    booking_id: UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None

class ReviewOut(BaseModel):
    id: UUID
    rating: int
    comment: str | None
    created_at: datetime
    customer_name: str

    class Config:
        from_attributes = True


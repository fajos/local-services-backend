# app/schemas/service.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.enums import PriceType
from typing import Optional
from decimal   import Decimal


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=10)
    category: str
    price_type: PriceType
    price: int | None = None  # Required if price_type is 'Fixed'

    class Config:
        use_enum_values = True
    
class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=3,
        description="Must be at least 3 characters",
    )
    category: Optional[str] = Field(
        None,
        description="One of your predefined categories",
    )
    description: Optional[str] = Field(
        None,
        min_length=5,
        description="Must be at least 5 characters",
    )
    price_type: Optional[PriceType] = Field(
        None,
        description="Fixed, Negotiable, or Visit Required",
    )
    price: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Required only for Fixed price_type",
    )

class ServiceOut(BaseModel):
    id: UUID
    provider_id: UUID
    name: str
    description: str
    category: str
    price_type: PriceType
    price: int | None = None
    is_active: bool
    created_at: datetime
    provider_verified: bool = False  # Added to show badge in lists

    class Config:
        from_attributes = True

class PublicUser(BaseModel):
    first_name: str
    last_name: str
    is_identity_verified: bool = False

    class Config:
        from_attributes = True

class PublicProviderInfo(BaseModel):
    id: UUID
    business_name: str
    business_address: str
    open_hours: str | None = None
    rating: float | None = None
    verified: bool = False
    user: PublicUser

class ServiceDetailOut(BaseModel):
    id: UUID
    name: str
    description: str
    category: str
    price_type: str
    price: Optional[int]
    created_at: datetime
    provider: PublicProviderInfo

    class Config:
        from_attributes = True
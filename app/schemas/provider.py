# app/schemas/provider.py

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime


# -----------------------------------
# 🏢 Provider Setup (Form Input)
# -----------------------------------

class ProviderCreate(BaseModel):
    business_name: str = Field(..., min_length=2)
    business_address: str
    business_phone: str = Field(..., min_length=10, max_length=20)
    business_email: EmailStr | None = None
    open_hours: str | None = None


# -----------------------------------
# 🧾 Response Schema
# -----------------------------------

class ProviderOut(BaseModel):
    id: UUID
    user_id: UUID
    business_name: str
    business_address: str
    business_phone: str
    business_email: EmailStr | None = None
    open_hours: str | None = None
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProviderUpdate(BaseModel):
    business_name:    str | None = None
    business_address: str | None = None
    business_phone:   str | None = None
    open_hours:       str | None = None

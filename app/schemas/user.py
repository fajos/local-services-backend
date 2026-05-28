# app/schemas/user.py

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


# ------------------------------
# 👤 User Registration Schema
# ------------------------------

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: str = Field(..., min_length=10, max_length=20)
    address: str


# ------------------------------
# 🔐 Login Schema
# ------------------------------

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ------------------------------
# 👤 Public User Info (response)
# ------------------------------

class UserOut(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str | None = None
    is_identity_verified: bool | None = False
    identity_status: str | None = "unverified"
    id_type: str | None = None
    id_number: str | None = None
    id_photo_url: str | None = None
    is_email_confirmed: bool | None = False
    is_phone_confirmed: bool | None = False
    is_provider: bool | None = False
    is_active: bool | None = True
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name:  str | None = None
    phone:      str | None = None
    address:    str | None = None
    id_type:    str | None = None
    id_number:  str | None = None
    id_photo_url: str | None = None

class UserOutExtended(UserOut):
    is_admin: bool | None = False
    is_super_admin: bool | None = False
    is_verified_provider: Optional[bool] = False

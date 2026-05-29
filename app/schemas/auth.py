# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name:  str = Field(..., min_length=2, max_length=50)
    email:      Optional[EmailStr] = None
    phone:      Optional[str]       = Field(None, min_length=10, max_length=20)
    password:   str = Field(..., min_length=8)
    address:    str

class ConfirmEmailRequest(BaseModel):
    token: str

class ConfirmPhoneRequest(BaseModel):
    user_id: str
    code:    str   = Field(..., min_length=6, max_length=6)

class ResendEmailRequest(BaseModel):
    email: EmailStr

class ResendPhoneRequest(BaseModel):
    phone: str
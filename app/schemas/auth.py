# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class RegisterRequest(BaseModel):
    first_name: str
    last_name:  str
    email:      Optional[EmailStr] = None
    phone:      Optional[str]       = None
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
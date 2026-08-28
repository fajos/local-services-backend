# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token, create_reset_token, verify_reset_token, hash_password, OTP_EXPIRE_MIN
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.core.config import settings
from app.utils.mailer import send_email
from app.schemas.auth import (
    RegisterRequest, ConfirmEmailRequest, ConfirmPhoneRequest,
    ResendEmailRequest, ResendPhoneRequest)
from app.core.security import (
    create_confirmation_token, verify_confirmation_token,
    generate_otp
)
from datetime import datetime, timedelta
from pydantic import BaseModel

import asyncio

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_EXP_HOURS = 1
CONFIRM_EXP_HOURS = 1

class RegisterResponse(BaseModel):
   user_id: str
   confirmation: str   # "email" or "phone"



@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator for assistance."
        )

    access_token = create_access_token(data={
        "sub": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_provider": user.is_provider,
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_email_confirmed": user.is_email_confirmed,
        "is_phone_confirmed": user.is_phone_confirmed,
        "is_identity_verified": user.is_identity_verified
    })

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password", status_code=204)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return  # don’t reveal existence

    token = create_reset_token(str(user.id))
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    text_body = (
        f"Hello {user.first_name},\n\n"
        "You requested a password reset. Click the link below to set a new password:\n\n"
        f"{reset_link}\n\n"
        "This link expires in 1 hour.\n"
        "If you didn’t request this, you can ignore this email."
    )

    html_body = (
        "<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;'>"
        f"<h2 style='color: #1e3a8a;'>Hello {user.first_name},</h2>"
        "<p style='color: #475569;'>You requested a password reset. Click the button below to set a new password:</p>"
        "<div style='text-align: center; margin: 30px 0;'>"
        f"<a href='{reset_link}' style='display:inline-block;background:#2563eb;color:white;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;'>Reset Password</a>"
        "</div>"
        f"<p style='font-size: 12px; color: #64748b;'>Or copy this link into your browser:<br>{reset_link}</p>"
        "<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;'>"
        "<p style='font-size: 11px; color: #94a3b8; text-align: center;'>"
        "Local Service Finder • 123 Business St, Lagos, Nigeria<br>"
        "If you didn’t request this, please ignore this email."
        "</p>"
        "</div>"
    )

    background_tasks.add_task(
        send_email,
        subject="Your password reset link",
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body
    )

@router.post("/reset-password", status_code=204)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        user_id = verify_reset_token(payload.token)
    except:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.password_hash = hash_password(payload.new_password)
    db.commit()

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 1) ensure email provided
    if not data.email:
        raise HTTPException(400, "Email is required for registration.")

    # 2) enforce uniqueness
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(400, "Email already registered.")

    # Phone uniqueness (still good to keep phone as a contact field)
    if data.phone and db.query(User).filter_by(phone=data.phone).first():
        raise HTTPException(400, "Phone number already in use.")

    # 3) create user
    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        is_active=True,
        address=data.address,
        is_phone_confirmed=True # Auto-confirm phone since we aren't verifying it
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # 4) Email flow
    token = create_confirmation_token(str(user.id))
    link = f"{settings.FRONTEND_URL}/confirm-email?token={token}"

    text_body = (
        f"Hi {user.first_name},\n\n"
        "Thank you for registering! Please confirm your email by clicking the link below:\n\n"
        f"{link}\n\nThis link expires in {CONFIRM_EXP_HOURS} hours."
    )

    html_body = (
        "<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;'>"
        f"<h2 style='color: #1e3a8a;'>Hi {user.first_name},</h2>"
        "<p style='color: #475569;'>Thank you for registering at Local Service Finder! Please confirm your email by clicking the button below:</p>"
        "<div style='text-align: center; margin: 30px 0;'>"
        f"<a href='{link}' style='display:inline-block;background:#2563eb;color:white;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;'>Confirm Email</a>"
        "</div>"
        f"<p style='font-size: 12px; color: #64748b;'>Or copy this link into your browser:<br>{link}</p>"
        "<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;'>"
        "<p style='font-size: 11px; color: #94a3b8; text-align: center;'>"
        "Local Service Finder • 123 Business St, Lagos, Nigeria<br>"
        "You received this because you signed up for an account."
        "</p>"
        "</div>"
    )

    background_tasks.add_task(
        send_email,
        "Confirm your email",
        [data.email],
        text_body,
        html_body
    )

    return RegisterResponse(user_id=str(user.id), confirmation="email")

@router.post("/confirm-email", status_code=204)
def confirm_email(
    payload: ConfirmEmailRequest,
    db: Session = Depends(get_db),
):
    try:
        user_id = verify_confirmation_token(payload.token)
    except:
        raise HTTPException(400, "Invalid or expired token.")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    user.is_email_confirmed = True
    db.commit()

@router.post("/confirm-phone", status_code=204)
def confirm_phone(
    payload: ConfirmPhoneRequest,
    db: Session = Depends(get_db),
):
    # Phone is now auto-confirmed. We keep this as a no-op for backward compatibility.
    user = db.query(User).get(payload.user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    user.is_phone_confirmed = True
    db.commit()

@router.post("/resend-email", status_code=204)
def resend_email(
    payload: ResendEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(email=payload.email).first()
    if not user:
        raise HTTPException(404, "Email not registered.")

    token = create_confirmation_token(str(user.id))
    link = f"{settings.FRONTEND_URL}/confirm-email?token={token}"

    text_body = f"Please confirm your email by clicking: {link}"
    html_body = (
        f"<h2>Confirm Your Email</h2>"
        "<p>Please click the button below to verify your email address:</p>"
        f"<a href='{link}' style='display:inline-block;background:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;'>Verify Email</a>"
        f"<p>Or copy this link:<br>{link}</p>"
    )

    background_tasks.add_task(
        send_email,
        "Confirm your email",
        [payload.email],
        text_body,
        html_body
    )

@router.post("/resend-phone", status_code=204)
def resend_phone(
    payload: ResendPhoneRequest,
    db: Session = Depends(get_db),
):
    # SMS is deprecated.
    raise HTTPException(400, "SMS verification is no longer supported. Phone numbers are auto-confirmed.")
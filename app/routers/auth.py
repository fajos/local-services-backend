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
import uuid

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
        "We received a request to reset the password for your Local Service Finder account. "
        "If you made this request, please click the link below to set a new password:\n\n"
        f"{reset_link}\n\n"
        "For your security, this link will expire in 1 hour. If you did not request a password reset, "
        "no further action is required and you can safely ignore this email.\n\n"
        "Best regards,\n"
        "The Local Service Finder Team"
    )

    html_body = (
        "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #edf2f7; border-radius: 16px; background-color: #ffffff;'>"
        f"<h2 style='color: #1a365d; margin-top: 0;'>Password Reset Request</h2>"
        f"<p style='color: #4a5568; font-size: 16px; line-height: 1.6;'>Hello {user.first_name},</p>"
        "<p style='color: #4a5568; font-size: 16px; line-height: 1.6;'>We received a request to reset the password for your Local Service Finder account. Click the secure button below to choose a new password:</p>"
        "<div style='text-align: center; margin: 35px 0;'>"
        f"<a href='{reset_link}' style='display:inline-block; background-color: #2563eb; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);'>Reset My Password</a>"
        "</div>"
        "<p style='color: #718096; font-size: 14px;'>If the button above doesn't work, copy and paste this link into your browser:</p>"
        f"<p style='color: #2563eb; font-size: 13px; word-break: break-all;'>{reset_link}</p>"
        "<hr style='border: 0; border-top: 1px solid #edf2f7; margin: 30px 0;'>"
        "<p style='font-size: 12px; color: #a0aec0; text-align: center; line-height: 1.5;'>"
        "This is an automated security notification. Please do not reply to this email.<br>"
        "&copy; 2026 Local Service Finder. Lagos, Nigeria."
        "</p>"
        "</div>"
    )

    background_tasks.add_task(
        send_email,
        subject="Action Required: Reset your Local Service Finder password",
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
    ref_code = f"LSF-{uuid.uuid4().hex[:8].upper()}"

    referred_by_id = None
    if data.referral_code:
        referrer = db.query(User).filter(User.referral_code == data.referral_code.upper()).first()
        if referrer:
            referred_by_id = referrer.id

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        is_active=True,
        address=data.address,
        is_phone_confirmed=True, # Auto-confirm phone since we aren't verifying it
        referral_code=ref_code,
        referred_by_id=referred_by_id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # 4) Email flow
    token = create_confirmation_token(str(user.id))
    link = f"{settings.FRONTEND_URL}/confirm-email?token={token}"

    text_body = (
        f"Hi {user.first_name},\n\n"
        "Welcome to Local Service Finder! We're excited to have you on board. "
        "To start booking services or listing your business, please verify your email address by clicking the link below:\n\n"
        f"{link}\n\n"
        f"This verification link will expire in {CONFIRM_EXP_HOURS} hours. "
        "Verifying your email ensures you receive important booking updates and secure access to your account.\n\n"
        "Thank you,\n"
        "The Local Service Finder Team"
    )

    html_body = (
        "<div style='font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 30px; border: 1px solid #edf2f7; border-radius: 16px; background-color: #ffffff;'>"
        f"<h2 style='color: #1a365d; margin-top: 0;'>Welcome to Local Service Finder!</h2>"
        f"<p style='color: #4a5568; font-size: 16px; line-height: 1.6;'>Hi {user.first_name},</p>"
        "<p style='color: #4a5568; font-size: 16px; line-height: 1.6;'>Thank you for joining our community! To get started with booking services and exploring top-rated local pros, please verify your email address:</p>"
        "<div style='text-align: center; margin: 35px 0;'>"
        f"<a href='{link}' style='display:inline-block; background-color: #2563eb; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);'>Verify My Email Address</a>"
        "</div>"
        "<p style='color: #718096; font-size: 14px;'>Or copy and paste this link into your browser:</p>"
        f"<p style='color: #2563eb; font-size: 13px; word-break: break-all;'>{link}</p>"
        "<hr style='border: 0; border-top: 1px solid #edf2f7; margin: 30px 0;'>"
        "<p style='font-size: 12px; color: #a0aec0; text-align: center; line-height: 1.5;'>"
        "You received this email because you created an account on Local Service Finder.<br>"
        "&copy; 2026 Local Service Finder. Lagos, Nigeria."
        "</p>"
        "</div>"
    )

    background_tasks.add_task(
        send_email,
        "Action Required: Verify your Local Service Finder account",
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
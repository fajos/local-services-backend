# app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.models.provider import Provider
from app.models.booking import Booking
from app.schemas.booking import BookingOutExtended
from app.schemas.user import UserOut, UserOutExtended, UserCreate
from app.schemas.provider import ProviderOut, ProviderCreate
from app.dependencies import get_current_admin, get_db, get_current_super_admin
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import verify_password, create_access_token, hash_password
from app.enums import BookingStatus, PaymentStatus
from app.models.service import Service
from fastapi import BackgroundTasks
from app.core.payment import send_payout, GATEWAY
from app.database import SessionLocal
from decimal import Decimal
from uuid import uuid4
from app.schemas.auth import ResetPasswordRequest

from app.utils.mailer import send_email

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login")
def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Case-insensitive search for the user
    user = db.query(User).filter(func.lower(User.email) == func.lower(form_data.username)).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Handle NULL is_active by treating it as True (Active)
    if user.is_active is False:
        raise HTTPException(
            status_code=403,
            detail="Your account has been deactivated. Please contact the administrator for assistance."
        )

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="You are not authorized as admin.")

    access_token = create_access_token({
        "sub": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": "admin",
        "is_provider": user.is_provider,
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_email_confirmed": user.is_email_confirmed,
        "is_phone_confirmed": user.is_phone_confirmed,
        "is_identity_verified": user.is_identity_verified
    })

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/summary")
def get_admin_summary(
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    total_users = db.query(User).count()
    total_providers = db.query(Provider).count()
    unverified_providers = db.query(Provider).filter(Provider.verified == False).count()
    pending_payouts = db.query(Booking).filter(
        Booking.payment_status == "paid",
        Booking.admin_released == False
    ).count()

    return {
        "total_users": total_users,
        "total_providers": total_providers,
        "unverified_providers": unverified_providers,
        "pending_payouts": pending_payouts
    }

@router.get("/bookings/paid", response_model=List[BookingOutExtended])
def list_paid_bookings_not_released(
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    """
    Return bookings that are:
      * booking_status = completed
      * payment_status = paid
      * admin_released = False
    Plus the extra fields service_name & customer_name required by BookingOutExtended
    """
    rows = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .join(User,   Booking.customer_id == User.id)
        .filter(
            Booking.booking_status == BookingStatus.completed,
            Booking.payment_status == PaymentStatus.paid,
            Booking.admin_released == False,
        )
        .all()
    )

    enriched: list[dict] = []
    for b in rows:
        enriched.append({
            "id": b.id,
            "service_id": b.service_id,
            "customer_id": b.customer_id,
            "note": b.note,
            "booking_status": b.booking_status,
            "quote_price": b.quote_price,
            "quote_status": b.quote_status,
            "visit_required": b.visit_required,
            "visit_status": b.visit_status,
            "payment_status": b.payment_status,
            "created_at": b.created_at,
            "admin_released": b.admin_released,
            "service_category": b.service.category,
            "service_name": b.service.name,   # <- required
            "customer_name": f"{b.customer.first_name} {b.customer.last_name}",  # <- required
            "provider_name": b.service.provider.business_name,
        })

    return enriched          # <- ALWAYS return this list

@router.get("/users", response_model=List[UserOutExtended])
def list_all_users(
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    return db.query(User).all()

@router.get("/providers", response_model=List[ProviderOut])
def list_all_providers(
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    return db.query(Provider).all()

@router.get("/providers/pending", response_model=List[ProviderOut])
def list_pending_providers(
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    return db.query(Provider).filter(Provider.verified == False).all()

@router.post("/bookings/{booking_id}/release", response_model=BookingOutExtended)
def release_payment_to_provider(
    booking_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.admin_released:
        raise HTTPException(400, "Already released")
    if (
        booking.payment_status != PaymentStatus.paid
        or booking.booking_status != BookingStatus.completed
    ):
        raise HTTPException(400, "Booking not ready for payout")

    # ─────────────────────────────────────────────────────────
    # 1️⃣  Net amount & destination
    # ─────────────────────────────────────────────────────────
    gross_ngn = Decimal(booking.quote_price or booking.service.price or 0)
    gross_kobo = int(gross_ngn * 100)

    platform_fee = int(gross_kobo * Decimal("0.10"))   # 10 % commission
    net_kobo     = gross_kobo - platform_fee           # ← money to provider

    provider = booking.service.provider
    payout_dest = (
        provider.stripe_account      # if you use Stripe Connect
        or provider.paystack_recipient   # if you use Paystack
    )
    if not payout_dest:
        raise HTTPException(400, "Provider has no payout destination")

    reference = f"PAYOUT-{uuid4().hex[:8]}-{booking.id}"

    # ─────────────────────────────────────────────────────────
    # 2️⃣  Kick off background payout task
    # ─────────────────────────────────────────────────────────
    background_tasks.add_task(
        execute_payout,
        net_kobo,
        payout_dest,
        reference,
        booking.id,
    )
    payout_dest = provider.stripe_account or provider.paystack_recipient
    if not payout_dest:
        raise HTTPException(400, "Provider has no payout destination on file")

    # ─────────────────────────────────────────────────────────
    # 3️⃣  Immediate response to admin (admin_released still False)
    # ─────────────────────────────────────────────────────────
    return {
        "id": booking.id,
        "service_id": booking.service_id,
        "customer_id": booking.customer_id,
        "note": booking.note,
        "booking_status": booking.booking_status,
        "quote_price": booking.quote_price,
        "quote_status": booking.quote_status,
        "visit_required": booking.visit_required,
        "visit_status": booking.visit_status,
        "payment_status": booking.payment_status,
        "created_at": booking.created_at,
        "admin_released": booking.admin_released,           # False now, flips in task
        "service_name": booking.service.name,
        "customer_name": f"{booking.customer.first_name} {booking.customer.last_name}",
    }


async def execute_payout(
    amount_kobo: int,
    destination: str,
    reference: str,
    booking_id: str,
):
    """
    Called by BackgroundTasks.
    Tries to send the payout and updates the booking record.
    """
    success, txn_id_or_err = await send_payout(
        amount_kobo,
        "ngn",                 # currency
        destination,
        reference,
    )

    # Use a fresh DB session inside the task
    with SessionLocal() as task_db:
        booking = task_db.query(Booking).get(booking_id)
        if not booking:
            return  # booking was deleted—nothing to do

        if success:
            booking.admin_released = True
            booking.payout_txn_id  = txn_id_or_err  # store transfer/txn ID
        else:
            # You might store the failure reason or send an alert e‑mail
            print("❌ Payout failed:", txn_id_or_err)

        task_db.commit()

@router.patch("/users/{user_id}/verify-identity", response_model=UserOut)
def verify_user_identity(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_identity_verified = True
    user.identity_status = "verified"
    db.commit()
    db.refresh(user)
    return user

@router.patch("/users/{user_id}/reject-identity", response_model=UserOut)
def reject_user_identity(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_identity_verified = False
    user.identity_status = "rejected"
    db.commit()
    db.refresh(user)
    return user

@router.post("/providers/{provider_id}/verify", response_model=ProviderOut)
def verify_provider(
    provider_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")

    provider.verified = True
    db.commit()
    db.refresh(provider)

    # Send Approval Email
    if provider.user and provider.user.email:
        body = (
            f"Hi {provider.user.first_name},\n\n"
            f"Great news! Your provider application for '{provider.business_name}' has been approved.\n"
            "You can now create services, manage bookings, and start receiving requests from customers.\n\n"
            "Log in to your dashboard to get started!"
        )
        background_tasks.add_task(
            send_email,
            "Provider Application Approved! 🎉",
            [provider.user.email],
            body
        )

    return provider

@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False  # (You need to add is_active field to User model if you want this soft ban feature)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/providers/{provider_id}/deactivate", response_model=ProviderOut)
def deactivate_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")

    provider.verified = False  # deactivate by setting verified to False
    db.commit()
    db.refresh(provider)
    return provider

@router.patch("/users/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_permanently(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """
    Permanently delete a user from the database.
    Only Super Admins can perform this action.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Prevent self-deletion via this endpoint for safety
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    db.delete(user)
    db.commit()
    return None

@router.patch("/providers/{provider_id}/activate", response_model=ProviderOut)
def activate_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_admin)
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")

    provider.verified = True
    db.commit()
    db.refresh(provider)
    return provider

@router.patch("/users/{user_id}/make-admin", response_model=UserOut)
def make_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_admin = True
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/remove-admin", response_model=UserOut)
def remove_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_admin = False
    db.commit()
    db.refresh(user)
    return user

@router.patch("/users/{user_id}/reset-password", status_code=204)
def admin_reset_user_password(
    user_id: str,
    payload: ResetPasswordRequest,               # just reuse new_password field
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully"}

@router.post("/users", response_model=UserOut)
def admin_create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    new_user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        password_hash=hash_password(payload.password),
        is_email_confirmed=True, # Admin created users are pre-confirmed
        is_phone_confirmed=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/users/{user_id}/make-provider", response_model=ProviderOut)
def admin_make_provider(
    user_id: str,
    payload: ProviderCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.is_provider:
        # Check if they already have a provider record
        existing_p = db.query(Provider).filter(Provider.user_id == user.id).first()
        if existing_p:
             raise HTTPException(status_code=400, detail="User is already a provider.")

    # Create provider record
    new_provider = Provider(
        user_id=user.id,
        business_name=payload.business_name,
        business_address=payload.business_address,
        business_phone=payload.business_phone,
        business_email=payload.business_email,
        open_hours=payload.open_hours,
        verified=True # Admin created providers are pre-verified
    )
    user.is_provider = True
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    return new_provider

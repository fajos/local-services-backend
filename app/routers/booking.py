# app/routers/booking.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.booking import BookingCreate, BookingOut, BookingCustomerOut, BookingOutExtended
from app.models.booking import Booking
from app.models.service import Service
from app.models.provider import Provider
from app.models.user import User
from app.enums import BookingStatus, QuoteStatus, VisitStatus, PaymentStatus, PriceType
from app.dependencies import get_db
from app.dependencies import get_current_user, get_current_admin
from app.utils.notifications import create_notification
import uuid

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingOut)
def book_service(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = (
        db.query(Service)
        .filter(Service.id == data.service_id, Service.is_active == True)
        .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not available.")

    # ---------------------------------------------
    # Set initial quote / payment logic by price type
    # ---------------------------------------------
    if service.price_type == PriceType.fixed:
        quote_price   = service.price            # lock price immediately
        quote_status  = QuoteStatus.accepted
        booking_stat  = BookingStatus.pending
    else:  # Negotiable or Visit Required
        quote_price   = None
        quote_status  = QuoteStatus.pending
        booking_stat  = BookingStatus.pending

    booking = Booking(
        id=uuid.uuid4(),
        service_id=service.id,
        customer_id=current_user.id,
        note=data.note,
        city_or_lga  = data.city_or_lga, 
        visit_required=(service.price_type == PriceType.visit_required),
        booking_status=booking_stat,
        quote_price=quote_price,
        quote_status=quote_status,
        visit_status=VisitStatus.scheduled if service.price_type == PriceType.visit_required else VisitStatus.not_started,
        payment_status=PaymentStatus.unpaid,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Notify Provider
    create_notification(
        db,
        service.provider.user_id,
        "New Booking Request 📩",
        f"You have a new booking request for '{service.name}' from {current_user.first_name}.",
        "info"
    )

    return booking

@router.get("/me", response_model=List[BookingCustomerOut])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookings = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .join(Provider, Service.provider_id == Provider.id)
        .join(User, Provider.user_id == User.id)
        .filter(Booking.customer_id == current_user.id)
        .all()
    )

    return [
        {
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
            "service_name": b.service.name,
            "service_category": b.service.category,          # 👈
            "provider_name": f"{b.service.provider.user.first_name} {b.service.provider.user.last_name}",
        }
        for b in bookings
    ]

@router.get("/provider/me", response_model=List[BookingOutExtended])
def get_bookings_for_provider(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. robust provider lookup
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .first()
    )
    if not provider:
        # still raise 404 – caller gets proper error, not None
        raise HTTPException(404, "You are not registered as a provider.")

    # 2. collect service IDs (can be empty)
    service_ids = (
        db.query(Service.id)
        .filter(Service.provider_id == provider.id)
        .all()
    )
    service_ids = [row.id for row in service_ids]

    if not service_ids:                # ← no services yet
        return []                      #   return empty list, not None

    # 3. fetch bookings
    bookings = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .join(User, Booking.customer_id == User.id)
        .filter(Booking.service_id.in_(service_ids))
        .all()
    )

    # 4. build list (may still be empty, but never None!)
    result = []
    for b in bookings:
        contact = (
            {
                "phone": b.customer.phone,
                "address": b.customer.address,
            }
            if b.payment_status == PaymentStatus.paid
            else None
        )

        result.append(
            {
                "id": b.id,
                "service_id": b.service_id,
                "customer_id": b.customer_id,
                "note": b.note,
                "city_or_lga": b.city_or_lga,
                "booking_status": b.booking_status,
                "quote_price": b.quote_price,
                "quote_status": b.quote_status,
                "visit_required": b.visit_required,
                "visit_status": b.visit_status,
                "payment_status": b.payment_status,
                "created_at": b.created_at,
                "service_name": b.service.name,
                "service_category": b.service.category,
                "customer_name": f"{b.customer.first_name} {b.customer.last_name}",
                "provider_name": provider.business_name,
                "admin_released": b.admin_released,
                "customer_info": contact,
            }
        )

    return result                      # ← ALWAYS a list

@router.post("/{booking_id}/mark-complete", response_model=BookingOut)
def provider_mark_complete(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not your booking")

    if booking.payment_status != PaymentStatus.paid:
        raise HTTPException(400, "Customer hasn’t paid yet")

    booking.booking_status = BookingStatus.completed
    db.commit()
    db.refresh(booking)

    # Notify Customer
    create_notification(
        db,
        booking.customer_id,
        "Service Completed 🏆",
        f"'{booking.service.name}' has been marked as completed by the provider. Please leave a review!",
        "success"
    )

    return booking

@router.patch("/{booking_id}/cancel", response_model=BookingCustomerOut)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == current_user.id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.booking_status != BookingStatus.pending:
        raise HTTPException(400, "Only pending bookings can be cancelled")

    booking.booking_status = BookingStatus.declined
    db.commit()
    db.refresh(booking)

    # Notify Provider
    create_notification(
        db,
        booking.service.provider.user_id,
        "Booking Cancelled 🚫",
        f"{current_user.first_name} has cancelled their booking for '{booking.service.name}'.",
        "warning"
    )

    # Re-use the enrich logic (brevity):
    service   = booking.service
    provider  = service.provider.user
    return {
        **booking.__dict__,
        "service_name": service.name,
        "service_category": service.category,
        "provider_name": f"{provider.first_name} {provider.last_name}",
    }

@router.post("/{booking_id}/send-quote", response_model=BookingOut)
def send_quote(
    booking_id: str,
    quote_price: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.quote_status != QuoteStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote already sent or accepted."
        )

    # Only provider who owns service can send quote
    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to quote on this booking."
        )

    booking.quote_price = quote_price
    booking.quote_status = QuoteStatus.pending
    db.commit()
    db.refresh(booking)

    # Notify Customer
    create_notification(
        db,
        booking.customer_id,
        "New Quote Received 💰",
        f"You received a quote of ₦{quote_price:,} for '{booking.service.name}'. Check your dashboard to accept or decline.",
        "info"
    )

    return booking


@router.post("/{booking_id}/accept-quote", response_model=BookingOut)
def accept_quote(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to accept this quote."
        )

    if booking.quote_status != QuoteStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending quote to accept."
        )

    booking.quote_status = QuoteStatus.accepted
    db.commit()
    db.refresh(booking)

    # Notify Provider
    create_notification(
        db,
        booking.service.provider.user_id,
        "Quote Accepted ✅",
        f"{current_user.first_name} accepted your quote for '{booking.service.name}'. You can now proceed with the service.",
        "success"
    )

    return booking

@router.post("/{booking_id}/decline-quote", response_model=BookingOut)
def decline_quote(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to decline this quote."
        )

    if booking.quote_status != QuoteStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending quote to decline."
        )

    booking.quote_status = QuoteStatus.declined
    db.commit()
    db.refresh(booking)

    # Notify Provider
    create_notification(
        db,
        booking.service.provider.user_id,
        "Quote Declined ❌",
        f"{current_user.first_name} declined your quote for '{booking.service.name}'.",
        "danger"
    )

    return booking

@router.post("/{booking_id}/mark-paid", response_model=BookingOut)
def mark_booking_paid(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to pay for this booking."
        )

    if booking.payment_status != PaymentStatus.unpaid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking already paid."
        )

    booking.payment_status = PaymentStatus.paid
    db.commit()
    db.refresh(booking)

    # Notify Provider
    create_notification(
        db,
        booking.service.provider.user_id,
        "Payment Received 💵",
        f"{current_user.first_name} has paid for '{booking.service.name}'. You can now see their contact details in your dashboard.",
        "success"
    )

    return booking

# Provider ACCEPTS a booking (e.g., fixed-price job)
@router.post("/{booking_id}/accept-booking", response_model=BookingOut)
def provider_accept_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    # Only the provider who owns the service can accept
    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not your booking")

    if booking.booking_status != BookingStatus.pending:
        raise HTTPException(400, "Booking already processed")

    booking.booking_status = BookingStatus.accepted
    db.commit()
    db.refresh(booking)

    # Notify Customer
    create_notification(
        db,
        booking.customer_id,
        "Booking Accepted ✅",
        f"Your booking for '{booking.service.name}' has been accepted by the provider.",
        "success"
    )

    return booking


# Provider DECLINES a booking
@router.post("/{booking_id}/decline-booking", response_model=BookingOut)
def provider_decline_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not your booking")

    if booking.booking_status != BookingStatus.pending:
        raise HTTPException(400, "Booking already processed")

    booking.booking_status = BookingStatus.declined
    db.commit()
    db.refresh(booking)

    # Notify Provider
    create_notification(
        db,
        booking.service.provider.user_id,
        "Booking Cancelled 🚫",
        f"{current_user.first_name} has cancelled their booking for '{booking.service.name}'.",
        "warning"
    )
    return booking


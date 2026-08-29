from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.schemas.booking import BookingCreate, BookingOut, BookingCustomerOut, BookingOutExtended, RescheduleRequest
from app.models.booking import Booking
from app.models.service import Service
from app.models.provider import Provider
from app.models.user import User
from app.models.review import Review, CustomerReview
from app.schemas.review import ReviewCreate, ReviewOut, CustomerReviewCreate, CustomerReviewOut
from app.enums import BookingStatus, QuoteStatus, VisitStatus, PaymentStatus, PriceType
from app.dependencies import get_db
from app.dependencies import get_current_user, get_current_admin
from app.utils.notifications import create_notification
import uuid
from datetime import datetime, timedelta

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
        .order_by(Booking.created_at.desc())
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
            "service_category": b.service.category,
            "provider_name": f"{b.service.provider.user.first_name} {b.service.provider.user.last_name}",
            "provider_business_name": b.service.provider.business_name,
            "is_disputed": b.is_disputed,
            "has_review": db.query(Review).filter(Review.booking_id == b.id).first() is not None
        }
        for b in bookings
    ]

@router.get("/provider/me", response_model=List[BookingOutExtended])
def get_bookings_for_provider(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .first()
    )
    if not provider:
        raise HTTPException(404, "You are not registered as a provider.")

    service_ids = (
        db.query(Service.id)
        .filter(Service.provider_id == provider.id)
        .all()
    )
    service_ids = [row.id for row in service_ids]

    if not service_ids:
        return []

    bookings = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .join(User, Booking.customer_id == User.id)
        .filter(Booking.service_id.in_(service_ids))
        .order_by(Booking.created_at.desc())
        .all()
    )

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
                "has_customer_review": db.query(CustomerReview).filter(CustomerReview.booking_id == b.id).first() is not None
            }
        )

    return result

@router.post("/{booking_id}/mark-en-route", response_model=BookingOut)
def provider_mark_en_route(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not your booking")

    if booking.booking_status != BookingStatus.accepted:
        raise HTTPException(400, "Booking must be accepted before going en route")

    booking.booking_status = BookingStatus.en_route
    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.customer_id,
        "Provider is en route! 🚚",
        f"Great news! Your provider for '{booking.service.name}' has started driving to your location.",
        "info"
    )

    return booking

@router.post("/{booking_id}/mark-in-progress", response_model=BookingOut)
def provider_mark_in_progress(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not your booking")

    # Status can move from accepted or en_route
    if booking.booking_status not in [BookingStatus.accepted, BookingStatus.en_route, BookingStatus.rescheduled]:
        raise HTTPException(400, "Booking status invalid for starting job")

    booking.booking_status = BookingStatus.in_progress
    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.customer_id,
        "Job Started 🚀",
        f"The provider has started working on '{booking.service.name}'.",
        "info"
    )

    return booking

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

    create_notification(
        db,
        booking.service.provider.user_id,
        "Booking Cancelled 🚫",
        f"{current_user.first_name} has cancelled their booking for '{booking.service.name}'.",
        "warning"
    )

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
        raise HTTPException(404, "Booking not found.")

    if booking.quote_status != QuoteStatus.pending:
        raise HTTPException(400, "Quote already processed.")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not authorized.")

    booking.quote_price = quote_price
    booking.quote_status = QuoteStatus.pending
    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.customer_id,
        "New Quote Received 💰",
        f"You received a quote of ₦{quote_price:,} for '{booking.service.name}'.",
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
        raise HTTPException(404, "Booking not found.")

    if booking.customer_id != current_user.id:
        raise HTTPException(403, "Not authorized.")

    if booking.quote_status != QuoteStatus.pending:
        raise HTTPException(400, "No pending quote to accept.")

    booking.quote_status = QuoteStatus.accepted
    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.service.provider.user_id,
        "Quote Accepted ✅",
        f"{current_user.first_name} accepted your quote for '{booking.service.name}'.",
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
        raise HTTPException(404, "Booking not found.")

    if booking.customer_id != current_user.id:
        raise HTTPException(403, "Not authorized.")

    if booking.quote_status != QuoteStatus.pending:
        raise HTTPException(400, "No pending quote to decline.")

    booking.quote_status = QuoteStatus.declined
    db.commit()
    db.refresh(booking)

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
        raise HTTPException(404, "Booking not found.")

    if booking.customer_id != current_user.id:
        raise HTTPException(403, "Not authorized.")

    if booking.payment_status != PaymentStatus.unpaid:
        raise HTTPException(400, "Booking already paid.")

    booking.payment_status = PaymentStatus.paid

    # -------------------------------------------------------------
    # Referral Reward Logic
    # -------------------------------------------------------------
    if current_user.referred_by_id:
        paid_count = db.query(Booking).filter(
            Booking.customer_id == current_user.id,
            Booking.payment_status == PaymentStatus.paid,
            Booking.id != booking.id
        ).count()

        if paid_count == 0:
            reward_amount = 500
            referrer = db.query(User).filter(User.id == current_user.referred_by_id).first()
            if referrer:
                referrer.wallet_balance = (referrer.wallet_balance or 0) + reward_amount
                create_notification(
                    db, referrer.id,
                    "Referral Reward! 💰",
                    f"You earned ₦{reward_amount} because {current_user.first_name} completed their first booking.",
                    "success"
                )

                current_user.wallet_balance = (current_user.wallet_balance or 0) + reward_amount
                create_notification(
                    db, current_user.id,
                    "Welcome Bonus! 🎁",
                    f"You earned ₦{reward_amount} as a welcome bonus for your first booking.",
                    "success"
                )
    # -------------------------------------------------------------

    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.service.provider.user_id,
        "Payment Received 💵",
        f"{current_user.first_name} has paid for '{booking.service.name}'.",
        "success"
    )

    return booking

@router.post("/{booking_id}/accept-booking", response_model=BookingOut)
def provider_accept_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")

    if booking.booking_status != BookingStatus.pending:
        raise HTTPException(400, "Booking already processed")

    booking.booking_status = BookingStatus.accepted
    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.customer_id,
        "Booking Accepted ✅",
        f"Your booking for '{booking.service.name}' has been accepted.",
        "success"
    )

    return booking

@router.post("/{booking_id}/review", response_model=ReviewOut, status_code=201)
def add_booking_review(
    booking_id: uuid.UUID,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == current_user.id,
        Booking.booking_status == BookingStatus.completed,
        Booking.payment_status == PaymentStatus.paid
    ).first()

    if not booking:
        raise HTTPException(400, "Booking not eligible for review")

    if db.query(Review).filter(Review.booking_id == booking.id).first():
        raise HTTPException(400, "Already reviewed")

    review = Review(
        booking_id=booking.id,
        provider_id=booking.service.provider_id,
        customer_id=current_user.id,
        rating=data.rating,
        comment=data.comment
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    prov = booking.service.provider
    avg = db.query(func.avg(Review.rating)).filter(Review.provider_id == prov.id).scalar() or 0
    prov.average_rating = int(round(avg * 100))
    prov.reviews_count += 1
    db.commit()

    return {
        **review.__dict__,
        "customer_name": f"{current_user.first_name} {current_user.last_name}",
        "service_name": booking.service.name
    }

@router.post("/{booking_id}/rate-customer", response_model=CustomerReviewOut, status_code=201)
def rate_customer(
    booking_id: uuid.UUID,
    data: CustomerReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.service.provider.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")

    if booking.booking_status != BookingStatus.completed:
        raise HTTPException(400, "Can only rate customer after completion")

    if db.query(CustomerReview).filter(CustomerReview.booking_id == booking.id).first():
        raise HTTPException(400, "Already rated")

    review = CustomerReview(
        booking_id=booking.id,
        provider_id=booking.service.provider_id,
        customer_id=booking.customer_id,
        rating=data.rating,
        comment=data.comment
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    customer = booking.customer
    avg = db.query(func.avg(CustomerReview.rating)).filter(CustomerReview.customer_id == customer.id).scalar() or 0
    customer.average_customer_rating = int(round(avg * 100))
    customer.customer_reviews_count += 1
    db.commit()

    return {
        **review.__dict__,
        "provider_name": booking.service.provider.business_name
    }

@router.patch("/{booking_id}/reschedule", response_model=BookingOut)
def propose_reschedule(
    booking_id: uuid.UUID,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    is_customer = booking.customer_id == current_user.id
    is_provider = booking.service.provider.user_id == current_user.id

    if not (is_customer or is_provider):
        raise HTTPException(403, "Not authorized")

    booking.reschedule_proposed_at = payload.new_date
    booking.reschedule_reason = payload.reason
    booking.reschedule_by = current_user.id
    booking.booking_status = BookingStatus.rescheduled

    db.commit()
    db.refresh(booking)

    other_party_id = booking.service.provider.user_id if is_customer else booking.customer_id
    create_notification(
        db,
        other_party_id,
        "Reschedule Proposed 🕒",
        f"{current_user.first_name} proposed a new time for '{booking.service.name}'.",
        "warning"
    )

    return booking

@router.post("/{booking_id}/dispute", response_model=BookingOut)
def report_booking_dispute(
    booking_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.customer_id != current_user.id:
        raise HTTPException(403, "Only customers can report issues")

    booking.is_disputed = True
    booking.dispute_reason = payload.get("reason")
    booking.dispute_status = "pending"

    db.commit()
    db.refresh(booking)

    return booking

@router.post("/cron/reminders")
def send_booking_reminders(
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    # 24h
    target_24h = now + timedelta(hours=24)
    bookings_24h = db.query(Booking).filter(
        Booking.scheduled_at >= target_24h - timedelta(minutes=30),
        Booking.scheduled_at <= target_24h + timedelta(minutes=30),
        Booking.booking_status == BookingStatus.accepted
    ).all()
    for b in bookings_24h:
        create_notification(db, b.customer_id, "Reminder: 24h to go! ⏰", f"Your booking for '{b.service.name}' is tomorrow.", "info")
        create_notification(db, b.service.provider.user_id, "Upcoming Job Tomorrow 🗓️", f"Job '{b.service.name}' is scheduled for tomorrow.", "info")

    # 1h
    target_1h = now + timedelta(hours=1)
    bookings_1h = db.query(Booking).filter(
        Booking.scheduled_at >= target_1h - timedelta(minutes=15),
        Booking.scheduled_at <= target_1h + timedelta(minutes=15),
        Booking.booking_status == BookingStatus.accepted
    ).all()
    for b in bookings_1h:
        create_notification(db, b.customer_id, "Reminder: 1 hour left! ⏳", f"Provider for '{b.service.name}' in 1 hour.", "warning")
        create_notification(db, b.service.provider.user_id, "Job starts in 1 hour! 🚀", f"'{b.service.name}' starts in 1 hour.", "warning")

    return {"message": "Reminders sent"}

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
        raise HTTPException(403, "Not authorized")

    booking.booking_status = BookingStatus.declined
    db.commit()
    db.refresh(booking)

    create_notification(
        db,
        booking.customer_id,
        "Booking Declined ❌",
        f"The provider declined your request for '{booking.service.name}'.",
        "danger"
    )
    return booking

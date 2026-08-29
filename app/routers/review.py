# app/routers/review.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.booking import Booking
from app.models.provider import Provider
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewOut, ReviewRespond
from app.dependencies import get_db, get_current_user
from app.enums import BookingStatus, PaymentStatus
from sqlalchemy import func
from datetime import datetime


router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/", response_model=ReviewOut, status_code=201)
def add_review(
        data: ReviewCreate,
        db: Session = Depends(get_db),
        current: User = Depends(get_current_user)
):
    # ① booking must exist & belong to caller
    booking = db.query(Booking).filter(
        Booking.id == data.booking_id,
        Booking.customer_id == current.id,
        Booking.booking_status == BookingStatus.completed,
        Booking.payment_status == PaymentStatus.paid
    ).first()
    if not booking:
        raise HTTPException(400, "Booking not eligible for review. Must be completed and paid.")

    # ② one review per booking
    if db.query(Review).filter(Review.booking_id == booking.id).first():
        raise HTTPException(400, "You have already reviewed this booking")

    review = Review(
        booking_id  = booking.id,
        provider_id = booking.service.provider_id,
        customer_id = current.id,
        rating      = data.rating,
        comment     = data.comment
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # ③ bump cached average on provider
    prov = booking.service.provider
    prov.average_rating = _new_average(db, prov.id)
    prov.reviews_count += 1
    db.commit()

    return _to_out(review, current)

@router.post("/{review_id}/respond", response_model=ReviewOut)
def respond_to_review(
    review_id: UUID,
    payload: ReviewRespond,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(404, "Review not found")

    # Only the provider owner can respond
    if review.provider.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to respond to this review")

    review.provider_response = payload.response
    review.responded_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return _to_out(review, review.customer)

@router.get("/provider/{provider_id}", response_model=List[ReviewOut])
def list_provider_reviews(provider_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(Review)
          .filter(Review.provider_id == provider_id)
          .order_by(Review.created_at.desc())
          .all()
    )

    return [
        ReviewOut(
            id=r.id,
            booking_id=r.booking_id,
            rating=r.rating,
            comment=r.comment,
            provider_response=r.provider_response,
            responded_at=r.responded_at,
            created_at=r.created_at,
            customer_name=f"{r.customer.first_name} {r.customer.last_name}" if r.customer else "Anonymous",
            service_name=r.booking.service.name
        )
        for r in rows
    ]

# helpers
def _new_average(db: Session, pid: UUID):
    agg = db.query(func.avg(Review.rating)).filter(Review.provider_id == pid).scalar() or 0
    return int(round(agg * 100)) # Store as hundredths

def _to_out(r: Review, u: User):
    return ReviewOut(
        id=r.id,
        booking_id=r.booking_id,
        rating=r.rating,
        comment=r.comment,
        provider_response=r.provider_response,
        responded_at=r.responded_at,
        created_at=r.created_at,
        customer_name=f"{u.first_name} {u.last_name}" if u else "Anonymous",
        service_name=r.booking.service.name if r.booking and r.booking.service else None
    )

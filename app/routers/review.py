# app/routers/review.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.booking import Booking
from app.models.provider import Provider
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewOut
from app.dependencies import get_db, get_current_user
from app.enums import BookingStatus, PaymentStatus
from sqlalchemy import func


router = APIRouter(prefix="/providers", tags=["Reviews"])

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
        Booking.booking_status == BookingStatus.completed,     # only after provider marks complete
        Booking.payment_status == PaymentStatus.paid
    ).first()
    if not booking:
        raise HTTPException(400, "Booking not eligible for review")

    # ② one review per booking
    if db.query(Review).filter(Review.booking_id == booking.id).first():
        raise HTTPException(400, "Already reviewed")

    review = Review(
        booking_id  = booking.id,
        provider_id = booking.service.provider_id,
        customer_id = current.id,
        rating      = data.rating,
        comment     = data.comment
    )
    db.add(review)

    # ③ bump cached average on provider (simple running avg)
    prov = booking.service.provider
    prov.average_rating = _new_average(db, prov.id, data.rating)

    db.commit(); db.refresh(review)
    return _to_out(review, current)

@router.get("/{provider_id}/reviews", response_model=List[ReviewOut])
def list_reviews(provider_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(Review)
          .join(User, Review.customer_id == User.id)
          .filter(Review.provider_id == provider_id)
          .order_by(Review.created_at.desc())
          .all()
    )

    return [
        ReviewOut(
            id=r.id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            customer_name=f"{r.booking.customer.first_name} {r.booking.customer.last_name}",
            service_name=r.booking.service.name
        )
        for r in rows
    ]

# helpers
def _new_average(db, pid, new_rating):
    agg = db.query(func.avg(Review.rating)).filter(Review.provider_id == pid).scalar() or 0
    return round(agg, 2)

def _to_out(r: Review, u: User):
    return ReviewOut(
        id=r.id,
        rating=r.rating,
        comment=r.comment,
        created_at=r.created_at,
        customer_name=f"{u.first_name} {u.last_name}"
    )

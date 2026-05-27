from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingUpdateStatus
import uuid
from app.models.booking import Booking
from app.models.provider import Provider
from uuid import UUID
from app.models.service import Service
from app.models.user import User
from fastapi import HTTPException

def create_booking(db: Session, customer_id: uuid.UUID, data: BookingCreate) -> Booking:
    booking = Booking(customer_id=customer_id, **data.dict())  # ✅ Changed from user_id to customer_id
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

def get_all_bookings(db: Session):
    return db.query(Booking).all()

def get_bookings_by_user(db: Session, user_id: UUID):
    bookings = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .join(Provider, Booking.provider_id == Provider.id)
        .join(User, Booking.customer_id == User.id)
        .filter(Booking.customer_id == user_id)
        .all()
    )

    results = []
    for b in bookings:
        results.append({
            "id": b.id,
            "customer_id": b.customer_id,
            "provider_id": b.provider_id,
            "provider_name": b.provider.name,
            "service_id": b.service_id,
            "service_name": b.service.name,
            "customer_name": b.customer.full_name,
            "customer_phone": b.customer.phone,
            "customer_location": b.customer.location,
            "status": b.status,
            "note": b.note,
            "timestamp": b.timestamp,
        })

    return results


def get_bookings_by_provider(db: Session, provider_id: uuid.UUID):
    return db.query(Booking).filter(Booking.provider_id == provider_id).all()

def get_bookings_by_provider_user(db: Session, user_id: UUID):
    provider = db.query(Provider).filter(Provider.user_id == user_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")

    bookings = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .join(User, Booking.customer_id == User.id)
        .filter(Booking.provider_id == provider.id)
        .all()
    )

    results = []
    for b in bookings:
        results.append({
            "id": b.id,
            "customer_id": b.customer_id,
            "provider_id": b.provider_id,
            "provider_name": provider.name,  # 🔧 FIXED HERE
            "service_id": b.service_id,
            "service_name": b.service.name,
            "customer_name": b.customer.full_name,
            "customer_phone": b.customer.phone,
            "customer_location": b.customer.location,
            "status": b.status,
            "note": b.note,
            "timestamp": b.timestamp,
        })

    return results

def update_booking_status(db: Session, booking_id: UUID, status: BookingUpdateStatus):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Prevent updating canceled or completed bookings
    if booking.status in ["canceled", "completed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status of a {booking.status} booking."
        )

    # Only allow valid transitions
    valid_transitions = {
        "pending": ["accepted", "canceled"],
        "accepted": ["completed", "canceled"],
    }

    if status.status not in valid_transitions.get(booking.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status change from {booking.status} to {status.status}."
        )

    booking.status = status.status
    db.commit()
    db.refresh(booking)

    return {
        "id": booking.id,
        "customer_id": booking.customer_id,
        "provider_id": booking.provider_id,
        "provider_name": booking.provider.name,
        "service_id": booking.service_id,
        "service_name": booking.service.name,
        "customer_name": booking.customer.full_name,
        "customer_phone": booking.customer.phone,
        "customer_location": booking.customer.location,
        "status": booking.status,
        "note": booking.note,
        "timestamp": booking.timestamp,
    }

def delete_booking(db: Session, booking_id: UUID, customer_id: UUID):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == customer_id   # Only allow deleting your own booking
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or not authorized")

    db.delete(booking)
    db.commit()

    return {"detail": "Booking cancelled successfully"}
# app/routers/service.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.service import ServiceCreate, ServiceOut, ServiceDetailOut, ServiceUpdate
from app.models.service import Service
from app.models.provider import Provider
from app.models.user import User
from app.models.review import Review
from app.dependencies import get_db
from app.dependencies import get_current_user
import uuid
from uuid import UUID
from fastapi import Query
from sqlalchemy import func


router = APIRouter(prefix="/services", tags=["Services"])


@router.post("/", response_model=ServiceOut)
def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is provider
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=400, detail="You must complete provider setup before creating a service.")

    if not provider.verified:
        raise HTTPException(status_code=403, detail="Your provider profile is not yet verified.")
    
    service = Service(
        id=uuid.uuid4(),
        provider_id=provider.id,
        name=data.name,
        description=data.description,
        category=data.category,
        price_type=data.price_type,
        price=data.price
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

class ServiceWithRating(ServiceOut):
    average_rating: float | None = None

@router.get("/me", response_model=list[ServiceOut])
def get_my_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    provider = (
        db.query(Provider)
          .filter(Provider.user_id == current_user.id)
          .first()
    )
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not registered as a provider."
        )

    # 🚫  remove join to Review.service_id – we no longer need it
    services = (
        db.query(Service)
          .filter(Service.provider_id == provider.id)
          .all()
    )
    return services

@router.get("/category/{category_name}", response_model=List[ServiceOut])
def get_services_by_category(
    category_name: str,
    db: Session = Depends(get_db),
):
    """Public: list all active & verified services in this category."""
    results = (
        db.query(Service, Provider.verified)
        .join(Provider, Service.provider_id == Provider.id)
        .filter(
            Service.category.ilike(category_name),
            Service.is_active == True,
            Provider.verified == True,
        )
        .all()
    )

    # Map to include provider_verified in ServiceOut
    services = []
    for service, verified in results:
        service.provider_verified = verified
        services.append(service)

    return services

@router.get("/{service_id}", response_model=ServiceDetailOut)
def get_service_details_public(
    service_id: UUID,
    db: Session = Depends(get_db),
):
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active.is_(True))
        .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    provider = db.query(Provider).filter(Provider.id == service.provider_id).first()
    if not provider or not provider.verified:
        raise HTTPException(status_code=403, detail="Provider not verified")

    user = db.query(User).filter(User.id == provider.user_id).first()

    return {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "category": service.category,
        "price_type": service.price_type,
        "price": service.price,
        "created_at": service.created_at,
        "provider": {
            "id": provider.id,
            "business_name": provider.business_name,
            "business_address": provider.business_address,
            "open_hours": provider.open_hours,
            "rating": None,
            "verified": provider.verified,
            "user": {
                "first_name": user.first_name,
                "last_name":  user.last_name,
                "is_identity_verified": user.is_identity_verified
            },
        },
    }

@router.patch("/{service_id}", status_code=204)
def update_service(
    service_id: str,
    body: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(404, "Service not found")

    # only owner may edit
    if svc.provider.user_id != current_user.id:
        raise HTTPException(403, "Not your service")

    update_data = body.dict(exclude_unset=True)
    if "price_type" in update_data and update_data["price_type"] != "Fixed":
        update_data["price"] = None  # clear price for non‑fixed types

    for field, value in update_data.items():
        setattr(svc, field, value)

    db.commit()
    return  # 204 No Content


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider profile not found."
        )

    service = db.query(Service).filter(Service.id == service_id, Service.provider_id == provider.id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found."
        )

    service.is_active = False
    db.commit()
    return

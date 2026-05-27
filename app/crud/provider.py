from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.provider import ProviderCreate
from app.models.provider import Provider
from app.models.service import Service
import uuid
from uuid import UUID

# ✅ In crud/provider.py

def create_provider(db: Session, user_id: uuid.UUID, data: ProviderCreate) -> Provider:
    provider = Provider(
        user_id=user_id,
        name=data.name,
        category=data.category,
        description=data.description,
        phone=data.phone,
        location=data.location,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)

    # If service_ids are passed, link them
    if data.service_ids:
        services = db.query(Service).filter(Service.id.in_(data.service_ids)).all()
        for service in services:
            service.provider_id = provider.id

    # If custom_services are passed, create new services
    if data.custom_services:
        for custom in data.custom_services:
            new_service = Service(
                name=custom.name,
                description=custom.description,
                category=custom.category,
                provider_id=provider.id,
            )
            db.add(new_service)

    db.commit()
    db.refresh(provider)
    return provider

def get_all_providers(db: Session) -> List[Provider]:
    return db.query(Provider).all()

def get_provider_by_user(db: Session, user_id: UUID):
    provider = db.query(Provider).filter(Provider.user_id == user_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    return provider

def get_provider_by_id(db: Session, provider_id: int) -> Optional[Provider]:
    return db.query(Provider).filter(Provider.id == provider_id).first()

def get_providers_by_service_id(db: Session, service_id: uuid.UUID):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return []  # Return empty list if service doesn't exist
    return [service.provider] if service.provider else []

def update_provider(db: Session, provider: Provider, update_data: ProviderCreate) -> Provider:
    for key, value in update_data.dict().items():
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return provider


def delete_provider(db: Session, provider: Provider) -> None:
    db.delete(provider)
    db.commit()

from sqlalchemy.orm import Session
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate
import uuid
from uuid import UUID
from fastapi import HTTPException

def create_service(db: Session, data: ServiceCreate) -> Service:
    service = Service(**data.dict())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

def get_all_services(db: Session):
    return db.query(Service).all()

def get_services_by_provider_user(db: Session, user_id: UUID):
    from app.models.provider import Provider
    provider = db.query(Provider).filter(Provider.user_id == user_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")

    return db.query(Service).filter(Service.provider_id == provider.id).all()

def get_service_by_id(db: Session, service_id: uuid.UUID):
    return db.query(Service).filter(Service.id == service_id).first()

def update_service(db: Session, service_id: uuid.UUID, update_data: ServiceUpdate):
    service = get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service

def delete_service(db: Session, service_id: UUID):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return None
    db.delete(service)
    db.commit()
    return service

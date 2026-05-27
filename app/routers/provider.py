# app/routers/provider.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.provider import ProviderCreate, ProviderOut, ProviderUpdate
from app.models.provider import Provider
from app.models.user import User
from app.dependencies import get_db
from app.dependencies import get_current_user
import uuid

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.post("/setup", response_model=ProviderOut)
def setup_provider(
    data: ProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already set up a provider profile."
        )

    provider = Provider(
        id=uuid.uuid4(),
        user_id=current_user.id,
        business_name=data.business_name,
        business_address=data.business_address,
        business_phone=data.business_phone,
        business_email=data.business_email,
        open_hours=data.open_hours
    )
    db.add(provider)

    # Upgrade user to provider
    current_user.is_provider = True
    db.commit()
    db.refresh(provider)
    return provider

@router.get("/me", response_model=ProviderOut)
def get_my_provider(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .first()
    )
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found.",
        )
    return provider

@router.get("/provider/me", include_in_schema=False)
def _alias_my_provider(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_provider(db, current_user)

@router.put("/me", response_model=ProviderOut)
def update_my_provider(
    payload: ProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = current_user.provider
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile missing")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    return provider

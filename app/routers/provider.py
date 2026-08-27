# app/routers/provider.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.schemas.provider import ProviderCreate, ProviderOut, ProviderUpdate
from app.models.provider import Provider
from app.models.portfolio import PortfolioItem
from app.schemas.portfolio import PortfolioItemCreate, PortfolioItemOut
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
        business_description=data.business_description,
        image_url=data.image_url,
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
        .options(joinedload(Provider.portfolio))
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


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider_by_id(provider_id: uuid.UUID, db: Session = Depends(get_db)):
    # Try looking up by Provider ID first
    provider = db.query(Provider).options(joinedload(Provider.portfolio)).filter(Provider.id == provider_id).first()
    if not provider:
        # Fallback: Try looking up by User ID
        provider = db.query(Provider).options(joinedload(Provider.portfolio)).filter(Provider.user_id == provider_id).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.get("/user/{user_id}", response_model=ProviderOut)
def get_provider_by_user_id(user_id: uuid.UUID, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.user_id == user_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found for this user")
    return provider


# --- Portfolio Endpoints ---

@router.get("/{provider_id}/portfolio", response_model=list[PortfolioItemOut])
def get_provider_portfolio(provider_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(PortfolioItem).filter(PortfolioItem.provider_id == provider_id).all()


@router.get("/me/portfolio", response_model=list[PortfolioItemOut])
def get_my_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.provider:
        raise HTTPException(status_code=400, detail="Not a provider")
    return db.query(PortfolioItem).filter(PortfolioItem.provider_id == current_user.provider.id).all()


@router.post("/me/portfolio", response_model=PortfolioItemOut)
def add_to_portfolio(
    data: PortfolioItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.provider:
        raise HTTPException(status_code=400, detail="Not a provider")

    item = PortfolioItem(
        id=uuid.uuid4(),
        provider_id=current_user.provider.id,
        title=data.title,
        image_url=data.image_url
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/me/portfolio/{item_id}", status_code=204)
def remove_from_portfolio(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.provider:
        raise HTTPException(status_code=400, detail="Not a provider")

    item = db.query(PortfolioItem).filter(
        PortfolioItem.id == item_id,
        PortfolioItem.provider_id == current_user.provider.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")

    db.delete(item)
    db.commit()
    return None

# app/routers/user.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.models.user import User
from app.core.security import hash_password
from app.dependencies import get_db
from app.dependencies import get_current_user
import uuid
from app.models.provider import Provider
from app.schemas.user import UserOutExtended, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=UserOut)
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use."
        )
    
    user = User(
        id=uuid.uuid4(),
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        address=data.address,
        is_provider=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/create-super-admin")
def create_super_admin(db: Session = Depends(get_db)):
    from app.core.security import hash_password

    email = "orjidom@yahoo.com"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Super admin already exists.")

    user = User(
        first_name="Femi",
        last_name="Adeyemi",
        email=email,
        password_hash=hash_password("fajos2014"),
        phone="08068319016",
        is_admin=True,
        is_super_admin=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Super admin created", "email": email}


@router.get("/me", response_model=UserOutExtended)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "address": current_user.address,
        "is_identity_verified": current_user.is_identity_verified,
        "identity_status": current_user.identity_status,
        "id_type": current_user.id_type,
        "id_number": current_user.id_number,
        "id_photo_url": current_user.id_photo_url,
        "is_email_confirmed": current_user.is_email_confirmed,
        "is_phone_confirmed": current_user.is_phone_confirmed,
        "is_provider": current_user.is_provider,
        "created_at": current_user.created_at,
        "is_admin": current_user.is_admin,
        "is_super_admin": current_user.is_super_admin,
        "is_verified_provider": provider.verified if provider else False
    }

@router.put("/me", response_model=UserOut)
def update_my_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)

    # If submitting ID info, set status to pending
    if "id_type" in data or "id_number" in data or "id_photo_url" in data:
        if current_user.identity_status != "verified":
            current_user.identity_status = "pending"

    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.patch("/me/deactivate", status_code=204)
def deactivate_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.is_active = False
    db.commit()
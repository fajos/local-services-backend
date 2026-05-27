# app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.security import decode_access_token
from app.database import SessionLocal
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
# app/dependencies.py

def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )
    return user

def get_current_super_admin(user: User = Depends(get_current_user)):
    if not user.is_super_admin:
        raise HTTPException(403, detail="Super admin access only.")
    return user

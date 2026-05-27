# app/core/security.py

import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.core.config import settings
import random, string

RESET_EXP_HOURS = 1
CONFIRM_EXP_HOURS = 24  
OTP_LENGTH = 6
OTP_EXPIRE_MIN = 10


def hash_password(password: str) -> str:
    # bcrypt requires bytes, so we encode the password string
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt.checkpw compares the plain password against the hashed one
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid token")
    
def create_reset_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=RESET_EXP_HOURS),
        "type": "password_reset",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_reset_token(token: str) -> str:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if data.get("type") != "password_reset":
            raise jwt.PyJWTError()
        return data["sub"]
    except jwt.PyJWTError:
        raise

def create_confirmation_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "email_confirm",
        "exp": datetime.utcnow() + timedelta(hours=CONFIRM_EXP_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_confirmation_token(token: str) -> str:
    data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if data.get("type") != "email_confirm":
        raise JWTError()
    return data["sub"]

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))
# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr

class Settings(BaseSettings):
     # ── App / JWT / DB settings ────────────────────────────────
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str

     # ── Frontend host (for reset links) ────────────────────────
    FRONTEND_URL: str

     # ── Email (SMTP) settings ─────────────────────────────────
    mail_username: str
    mail_password: str
    mail_from: EmailStr
    mail_server: str
    mail_port: int = 465

    mail_starttls: bool = False  
    mail_ssl_tls: bool = True  

    # ── Cloudinary settings ────────────────────────────────────
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_upload_preset: str

    # ── Payout / Payment settings ──────────────────────────────
    PAYOUT_GATEWAY: str = "paystack"  # "stripe" or "paystack"
    PAYSTACK_SECRET_KEY: str | None = None
    STRIPE_SECRET_KEY: str | None = None

     # ── Pydantic V2 config ────────────────────────────────────
    model_config = SettingsConfigDict(
         env_file=".env",
         case_sensitive=False,
         extra="ignore",
     )

settings = Settings()
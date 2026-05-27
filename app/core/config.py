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

    at_username: str
    at_api_key: str  

     # ── Pydantic V2 config ────────────────────────────────────
    model_config = SettingsConfigDict(
         env_file=".env",
         case_sensitive=False,
         extra="ignore",
     )

settings = Settings()
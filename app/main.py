# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.core.security import hash_password
from contextlib import asynccontextmanager
from app.routers import auth, user, provider, service, booking, admin, review, notification, chat
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    server_error_handler,
)
from sqlalchemy import text

# Create database tables
Base.metadata.create_all(bind=engine)

def fix_missing_columns():
    """Manually add columns and tables if they are missing (Common issue on Render deployments)"""
    db = SessionLocal()
    try:
        # Columns for 'users'
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_url VARCHAR"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS id_type VARCHAR"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS id_number VARCHAR"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS id_photo_url VARCHAR"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS identity_status VARCHAR DEFAULT 'unverified'"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS average_customer_rating INTEGER"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_reviews_count INTEGER DEFAULT 0"))
        db.commit()

        # Columns for 'providers'
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS image_url VARCHAR"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS business_email VARCHAR"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS business_description VARCHAR"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS open_hours VARCHAR"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT TRUE"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS service_radius INTEGER DEFAULT 10"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS background_checked BOOLEAN DEFAULT FALSE"))
        db.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS verification_tier VARCHAR DEFAULT 'standard'"))
        db.commit()

        # Columns for 'bookings'
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reschedule_proposed_at TIMESTAMP"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reschedule_reason TEXT"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reschedule_by UUID"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS latitude VARCHAR(50)"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS longitude VARCHAR(50)"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_disputed BOOLEAN DEFAULT FALSE"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS dispute_reason TEXT"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS dispute_status VARCHAR(50)"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS frequency VARCHAR(20)"))
        db.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS parent_booking_id UUID"))
        db.commit()

        # Columns for 'reviews'
        db.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS booking_id UUID UNIQUE REFERENCES bookings(id) ON DELETE CASCADE"))
        db.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS provider_response TEXT"))
        db.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS responded_at TIMESTAMP"))
        db.commit()

        # Ensure Enum values exist in PostgreSQL (BookingStatus)
        # Note: ALTER TYPE ... ADD VALUE cannot run in a transaction with other commands in some PG environments.
        # We use a separate raw connection with AUTOCOMMIT for this.
        try:
            with engine.connect() as conn:
                with conn.execution_options(isolation_level="AUTOCOMMIT") as autocommit_conn:
                    for value in ['in-progress', 'paid', 'cancelled', 'rescheduled']:
                        try:
                            autocommit_conn.execute(text(f"ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS '{value}'"))
                        except Exception as e:
                            print(f"ℹ️ Enum value '{value}' exists or error: {e}")
        except Exception as e:
            print(f"⚠️ Enum update skipped: {e}")

        # Tables for Chat and Notifications (Base.metadata.create_all handles creation, but just in case)
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY,
                booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                sender_id UUID NOT NULL REFERENCES users(id),
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR NOT NULL,
                message VARCHAR NOT NULL,
                type VARCHAR DEFAULT 'info',
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio_items (
                id UUID PRIMARY KEY,
                provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
                title VARCHAR,
                image_url VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        db.commit()
        print("✅ Database columns and tables verified/updated.")
    except Exception as e:
        print(f"⚠️ Column fix skipped or failed: {e}")
    finally:
        db.close()

def create_default_admin():
    db = SessionLocal()
    try:
        admin_email = "orjidom@yahoo.com"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                first_name="Femi",
                last_name="Adeyemi",
                email=admin_email,
                password_hash=hash_password("fajos2014"),
                phone="08068319016",
                is_admin=True,
                is_super_admin=True,
                is_active=True,
                is_email_confirmed=True,
                is_phone_confirmed=True
            )
            db.add(admin_user)
            print(f"✅ Default admin user created: {admin_email}")
        else:
            # Ensure existing user has admin privileges AND the correct password
            admin_user.is_admin = True
            admin_user.is_super_admin = True
            admin_user.is_active = True
            admin_user.is_email_confirmed = True
            admin_user.is_phone_confirmed = True
            admin_user.password_hash = hash_password("fajos2014")
            print(f"✅ Admin privileges and password verified for: {admin_email}")

        db.commit()
    except Exception as e:
        print(f"❌ Error creating/updating default admin: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    fix_missing_columns()
    create_default_admin()
    yield

app = FastAPI(
    title="Local Service Finder",
    description="Connect customers and service providers easily.",
    version="1.0.0",
    lifespan=lifespan
)

# Allow frontend apps to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(provider.router)
app.include_router(service.router)
app.include_router(booking.router)
app.include_router(admin.router)
app.include_router(review.router)
app.include_router(notification.router)
app.include_router(chat.router)

# Register global handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, server_error_handler)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Local Service Finder API!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Server is alive and kicking!"}

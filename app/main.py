# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.core.security import hash_password
from contextlib import asynccontextmanager
from app.routers import auth, user, provider, service, booking, admin, review
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    server_error_handler,
)

# Create database tables
Base.metadata.create_all(bind=engine)

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
            db.commit()
            print(f"✅ Default admin user created: {admin_email}")
    except Exception as e:
        print(f"❌ Error creating default admin: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Register global handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, server_error_handler)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Local Service Finder API!"}

import uuid
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.provider import Provider
from app.models.service import Service
from app.models.booking import Booking

def seed_test_data():
    db: Session = SessionLocal()
    try:
        # Create test user
        user = User(
            id=uuid.uuid4(),
            full_name="Test User",
            email="test@example.com",
            password_hash="hashedpassword",
            is_provider=True,
            location="Lagos",
            phone="08012345678"
        )
        db.add(user)
        db.flush()  # To get user.id

        # Create services
        haircut = Service(
            id=uuid.uuid4(),
            name="Haircut",
            description="Basic haircut service",
            category="Salon"
        )
        plumbing = Service(
            id=uuid.uuid4(),
            name="Plumbing",
            description="Fix pipes and leaks",
            category="Home Services"
        )
        db.add_all([haircut, plumbing])
        db.flush()

        # Create provider and link to haircut service
        provider = Provider(
            id=uuid.uuid4(),
            name="Joe's Cuts",
            category="Salon",
            description="Sharp fades and trims",
            phone="08098765432",
            location="Ikeja",
            user_id=user.id,
            services=[haircut]
        )
        db.add(provider)
        db.flush()

        # Optional: create a booking
        booking = Booking(
            id=uuid.uuid4(),
            customer_id=user.id,
            provider_id=provider.id,
            service_id=haircut.id,
            status="pending"
        )
        db.add(booking)

        db.commit()
        print("✅ Test data seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error while seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_data()
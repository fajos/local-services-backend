# 🧰 Local Service Finder API – Backend

This is the **backend API** for the **Local Service Finder platform** – a comprehensive ecosystem where customers can book services from verified providers, and providers can manage their business offerings. Admins have full control over verification, user management, and platform integrity.

---

## 🚀 Features

✅ **JWT-based Authentication** – Secure access with token-based sessions.  
✅ **Multi-Channel Verification** – Link-based email confirmation and Africa's Talking SMS OTP.  
✅ **Hierarchical Role Access** – Granular permissions for Customers, Providers, Admins, and Super Admins.  
✅ **Automated Trust Signals** – Automatic "Verified" status (Blue Tick) upon successful phone verification.  
✅ **Service Management** – Smart pricing models (Fixed / Negotiable / Visit Required).  
✅ **Admin Dashboard Suite** – Approve provider applications, manage user status, and elevate administrators.  
✅ **Global Error Handling** – Consistent API responses and validation.  
✅ **Environment Driven** – Fully configurable via `.env`.  

---

## 🛠 Tech Stack

- **FastAPI** (Python 3.10+)
- **SQLAlchemy** (ORM)
- **PostgreSQL / SQLite** (Database)
- **Pydantic V2** (Data validation)
- **Africa's Talking** (SMS Gateway)
- **FastAPI Mail** (SMTP Integration)
- **Alembic** (Migration Management)

---

## 📁 Folder Structure

```
app/
├── core/             → Configs, Security, Security Logic
├── models/           → Database Models (User, Provider, Service, Booking, Review)
├── schemas/          → Pydantic Validation Schemas
├── routers/          → Modular API Endpoints (Auth, Admin, Provider, User, etc.)
├── utils/            → Helpers for Mailer, SMS, and Verification
├── database.py       → SQLAlchemy Engine & Session
├── dependencies.py   → Auth helpers & DB Injection
└── main.py           → FastAPI app entry point
```

---

## ⚙️ Setup Instructions

### 1. Clone & Install

```bash
git clone https://github.com/your-repo/local-service-backend.git
cd local-service-backend
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Create a `.env` file in the root directory:

```env
# Base Configuration
DATABASE_URL=sqlite:///./local_service.db
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FRONTEND_URL=http://localhost:3000

# Africa's Talking (SMS)
AT_USERNAME=sandbox
AT_API_KEY=your_at_api_key

# Email (SMTP)
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_FROM=your_email@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=465
```

### 3. Run the App

```bash
uvicorn app.main:app --reload
```

### 4. Access the Docs

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔐 Verification Flow

The platform operates on a high-trust model:
1. **Email Verification**: A confirmation link is sent upon registration.
2. **Phone Verification**: A 6-digit OTP is sent via SMS.
3. **Verification Badge**: The "Identity Verified" blue tick is automatically granted once a user confirms their phone number.

---

## 🧑‍💼 Admin & Super Admin Actions

### Admin Capabilities:
- **User Management**: View all users and deactivate accounts.
- **Provider Oversight**: Review and verify provider applications.
- **Payment Release**: Manually release payments to providers after service completion.

### Super Admin Exclusive:
- **Admin Management**: Elevate regular users to Admin status or revoke permissions.
- **System Configuration**: Full access to critical platform overrides.

---

## 📄 License

MIT — Created with ❤️ for local service entrepreneurs.

---

## 🙌 Built by Femi Adeyemi (a.k.a. Fajos)

Ready to launch your local service empire 🚀

---

🗓️ **Last Updated:** May 01, 2025

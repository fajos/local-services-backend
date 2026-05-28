# 🧰 Local Service Finder API – Backend

This is the **backend API** for the **Local Service Finder platform** – a comprehensive ecosystem where customers can book services from verified providers, and providers can manage their business offerings. Admins have full control over verification, user management, and platform integrity.

---

## 🚀 Features

✅ **JWT-based Authentication** – Secure access with token-based sessions.  
✅ **Multi-Channel Verification** – Link-based email confirmation and Africa's Talking SMS OTP.  
✅ **Hierarchical Role Access** – Granular permissions for Customers, Providers, Admins, and Super Admins.  
✅ **Manual Identity Verification** – High-trust verification pipeline involving government-issued ID review (NIN, BVN, Passport).  
✅ **Identity Lifecycle Management** – Users progress through `unverified`, `pending`, `verified`, and `rejected` states.  
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

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migration

Before running the app, initialize your database tables:

```bash
alembic upgrade head
```

### 3. Configure Environment (`.env`)

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

### 4. Run the App

```bash
uvicorn app.main:app --reload
```

### 5. Access the Docs

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🌐 Deployment (Render)

When deploying to Render, use the following settings:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

> **Note:** The `$PORT` variable is automatically injected by Render. Ensure all required environment variables from the `.env` section are added in the Render **Environment** tab.

---

## 🔐 Identity Verification Flow

The platform operates on a high-trust, multi-layered verification model:
1. **ID Submission**: Users upload government-issued ID details (Type, Number) and photo URLs for review.
2. **Pending Review**: Accounts are marked as `pending` once identity documents are submitted.
3. **Admin Audit**: Administrators manually review the provided ID photos via the Admin Dashboard.
4. **Verification Badge**: The "Identity Verified" blue tick is granted only after manual admin approval.
5. **Rejection Handling**: Admins can reject invalid IDs, allowing users to re-submit corrected information.

---

## 🧑‍💼 Admin & Super Admin Actions

### Admin Capabilities:
- **Identity Audit**: Review, approve, or reject user-submitted identity documents.
- **User Management**: View all users, filter by identity status, and deactivate accounts.
- **Provider Oversight**: Review and verify provider applications and service listings.
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

🗓️ **Last Updated:** May 27, 2026

🍽️ DineOS Backend – Step‑by‑Step Guide for the Team
Project: DineOS – Multi‑Tenant Restaurant Management SaaS
Backend Stack: FastAPI · PostgreSQL · Redis · Alembic · Argon2 · JWT · Brevo · Razorpay

📖 Overview
DineOS is a SaaS platform that lets a restaurant owner run multiple restaurants (tenants) from a single code‑base.
All business logic lives in the backend – a modern, async FastAPI service that: - Handles authentication, role‑based permissions, and OTP/MFA flows - Manages restaurants, menus, orders, kitchen display, billing, inventory, CRM, reports, and subscription billing - Stores data in PostgreSQL, uses Redis for OTPs, rate‑limiting and real‑time KDS updates - Emits an audit log for every DB change

The purpose of this document is to walk a new developer through the whole code‑base, explain the design decisions, and show how to get the backend up and running locally.

🗂️ Repository Layout
backend/
├─ app/                     # FastAPI application package
│  ├─ main.py               # entry point – creates FastAPI app, registers routers
│  ├─ core/                 # shared infrastructure
│  │  ├─ config.py          # Pydantic Settings – reads .env
│  │  ├─ db.py              # async SQLAlchemy engine & session dependency
│  │  ├─ redis.py           # Redis connection wrapper
│  │  ├─ security.py        # Argon2 password hashing + JWT helpers
│  │  ├─ deps.py            # auth dependencies (get_current_user, require_role)
│  │  ├─ audit.py           # SQLAlchemy event listener → AuditLog rows
│  │  ├─ notifications.py   # Unified email/SMS/WhatsApp service (Brevo, Twilio)
│  │  └─ limiter.py         # SlowAPI rate‑limiting middleware
│  ├─ common/               # reusable utilities (exceptions, pagination, responses)
│  └─ modules/              # feature modules – one folder per domain
│     ├─ auth/               # registration, login, OTP, MFA, password reset
│     ├─ tenancy/            # restaurant & branch models
│     ├─ menu/               # categories, items, variants, add‑ons, per‑branch pricing
│     ├─ orders/             # order lifecycle, idempotency, KOT generation
│     ├─ kds/                # WebSocket + Redis pub/sub for kitchen display
│     ├─ billing/            # invoices, GST calculation, payment & refunds
│     ├─ inventory/          # ingredients, recipes, stock ledger
│     ├─ operations/         # floors, tables, tips, staff allocations
│     ├─ crm/                # customers, loyalty points, feedback
│     ├─ reports/            # sales, GST, inventory reports – CSV/Excel/PDF
│     ├─ subscriptions/      # Razorpay plan billing & webhook verification
│     └─ system/             # AuditLog model, system‑wide utilities
├─ alembic/                 # DB migration scripts
├─ requirements.txt         # Python dependencies
└─ .env.example             # template for environment variables (never commit real secrets)
All modules follow the four‑file pattern (models.py, schemas.py, service.py, router.py). This keeps the code clean, testable and easy to extend.

🧱 Core Infrastructure (app/core/)
1️⃣ Configuration – config.py
Uses Pydantic Settings to load environment variables from a .env file.
All secrets (DB URL, JWT secret, Brevo API key, Razorpay secret, etc.) live here – no hard‑coded values.
2️⃣ Database – db.py
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
Async‑first – the whole stack can serve thousands of concurrent requests.
Migrations are managed by Alembic (alembic/versions/).
3️⃣ Redis – redis.py
redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
Used for OTP storage, rate limiting, JWT black‑listing, and KDS pub/sub.
4️⃣ Security – security.py
Argon2id (PasswordHasher) – the most secure password‑hashing algorithm.
JWT helpers create access (15 min) and refresh (7 days) tokens with a unique jti claim.
Tokens can be read from Authorization header or an httpOnly cookie (ideal for browsers).
5️⃣ Dependency Injection – deps.py
get_current_user extracts the JWT, verifies it, loads the user and roles from the DB.
require_role(*roles) is a factory that raises 403 unless the user has one of the supplied roles.
get_current_tenant resolves the restaurant (tenant) based on the user’s restaurant_id (or a query param for super_admin).
6️⃣ Audit Logging – audit.py
Uses SQLAlchemy's event.listens_for(Session, "before_flush").
Automatically records insert, update, and delete actions with:
user_id, restaurant_id, IP, user‑agent
JSON snapshots of old and new values
No manual audit.log() calls required anywhere in the code.
🔐 Authentication Module (modules/auth/)
Data Model (models.py)
Permission ──< many‑to‑many >── Role ──< many‑to‑many >── User
UserSession (stores refresh token hash, device info)
Permissions are atomic strings like manage_menu, view_reports.
Roles aggregate permissions – e.g. owner, manager, staff, cashier.
Role‑Based Access Control (RBAC)
Roles are seeded via POST /auth/seed (run once on a fresh DB).
Every protected endpoint adds Depends(require_role("owner", "manager")).
super_admin bypasses all checks (for platform‑wide admin tasks).
Full Auth Flow
Register – POST /auth/register creates a user with role owner and sends a 6‑digit OTP via email.
Email verification – POST /auth/verify-email/request (anyone can call) → sends OTP; POST /auth/verify-email/verify validates it.
Phone OTP – POST /auth/otp/send → SMS; POST /auth/otp/verify → marks phone verified.
Login – POST /auth/login verifies password, returns access + refresh JWTs, also sets httpOnly cookies.
MFA (optional) – POST /auth/mfa/setup returns a QR code for Google Authenticator; POST /auth/mfa/verify activates it.
Password Reset – POST /auth/password-reset/request (email → OTP) → POST /auth/password-reset/reset (email, OTP, new_password).
Refresh – POST /auth/refresh exchanges a valid refresh token for a new access token.
Logout – POST /auth/logout revokes the session and black‑lists the refresh token.
OTP Design (Email, Phone, Password Reset)
Stored in Redis with a namespaced key:
email_verify:{email}:{otp}
phone_otp:{phone}:{otp}
pwd_reset:{email}:{otp}
TTLs: 10 min for email verification, 5 min for phone OTP, 15 min for password‑reset OTP.
Using the email/phone in the key prevents collisions between different users.
🏢 Tenancy (modules/tenancy/)
After registration, the owner creates a Restaurant (POST /tenancy/restaurants).
A restaurant can have many Branches (POST /tenancy/branches).
All subsequent data rows carry a restaurant_id foreign key – this is the multi‑tenant isolation.
super_admin can access any tenant by passing ?restaurant_id= query param.
🍽️ Menu (modules/menu/)
Category → Item → Variant → Add‑on hierarchy.
Items can have different prices per branch (MenuItemBranchPrice).
Each item includes GST‑related fields (HSN code, tax rate) for automatic billing.
CRUD endpoints are fully RBAC‑protected – only owner/manager can modify the menu.
📦 Orders (modules/orders/)
An order follows a state machine: placed → confirmed → preparing → ready → served → completed
Idempotency‑Key header prevents duplicate orders on retries.
When an order reaches served, the system automatically:
Deducts ingredient quantities from inventory (via the recipe linkage).
Emits a KOT (Kitchen Order Ticket) to the KDS via Redis pub/sub.
Endpoints exist for creating, updating status, listing, and canceling orders.
👨🍳 Kitchen Display System (modules/kds/)
Uses WebSocket (/ws/kds/{branch_id}) for the kitchen screen.
Backend publishes JSON payloads to Redis channel kds:{branch_id}.
Kitchen clients subscribe via WebSocket and receive real‑time updates – no polling.
💳 Billing (modules/billing/)
Generates GST‑compliant invoices (CGST/SGST for intra‑state, IGST for inter‑state).
Each line item stores the HSN code and tax rate.
Supports multiple payment methods (cash, card, UPI) and refund flows.
When a payment is successful, the system awards loyalty points (10 % of the amount).
📦 Inventory (modules/inventory/)
Ingredient master table (unit of measure, current stock).
Recipe joins an ingredient to a menu item with quantity needed.
Stock ledger automatically decrements when an order is served.
Manual stock adjustments are recorded with audit logs.
🪑 Operations (modules/operations/)
Hierarchy: Floor → TableSection → DiningTable.
Tables have capacity, status and can be assigned to a waiter.
Tips can be recorded per order and allocated to staff members.
👥 CRM (modules/crm/)
Customer records (lookup by phone/email, created on first order).
Loyalty Points – earned on each payment, can be redeemed for discounts.
Feedback – rating (1‑5) and free‑text comment stored per order.
📊 Reports (modules/reports/)
Endpoints return JSON aggregations (sales, GST, inventory levels) with optional date filters.
Export routes support CSV, XLSX (via openpyxl) and PDF (via reportlab).
All reports are scoped to the current tenant (restaurant).
💰 Subscriptions (modules/subscriptions/)
SaaS billing via Razorpay.
GET /subscriptions/plans – list available pricing tiers.
POST /subscriptions/checkout – creates a Razorpay order and returns the checkout URL.
POST /subscriptions/webhook – Razorpay posts payment status; the endpoint verifies the HMAC signature and activates the plan.
🔔 Notifications (core/notifications.py)
Unified class exposing: - send_email(to, subject, html_body) – uses Brevo (formerly SendinBlue). - send_sms(to, text) – uses Twilio. - send_whatsapp(to, text) – uses Meta Business API. All OTPs, password‑reset links, order confirmations, and invoices go through this service.

🚦 Rate Limiting & Security
# Example: limit login to 5 attempts per minute per IP
@limiter.limit("5/minute")
async def login(...):
General API limit: 100 requests/minute.
All secrets live in .env; never checked into VCS.
All DB writes are audit‑logged.
Refresh tokens are stored hashed in UserSession – can be revoked on logout.
📦 Database Migrations (Alembic)
Run alembic revision --autogenerate -m "description" after changing a model.
Apply with alembic upgrade head.
Roll back with alembic downgrade -1.
Migration files live under alembic/versions/ and are version‑controlled.
🏃♀️ Local Development Workflow
Clone repo and create a virtual environment bash git clone https://github.com/hemant-pawade/restaurant-saas.git cd restaurant-saas python -m venv venv && .\venv\Scripts\activate pip install -r requirements.txt
Create .env from the example and fill in your local secrets (PostgreSQL, Redis, Brevo key, etc.)
Run DB migrations bash alembic upgrade head
Seed default data (roles, permissions, test restaurant) bash curl -X POST http://127.0.0.1:8000/api/v1/auth/seed
Start the server – the dev.bat script (generated earlier) will start PostgreSQL, Redis, the frontend (npm) and the backend automatically: bash .\dev.bat # or simply: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
Open Swagger UI at http://127.0.0.1:8000/docs – you’ll see all routes grouped by tags (Auth, Tenancy, Menu, Orders, …).
Test the flow
Register a new user → verify email OTP → login → create a restaurant → add menu items → place an order → see KDS update → generate invoice → check loyalty points.
Each step can be exercised directly from Swagger.
✅ Checklist – What’s Ready for Production
[x] Async FastAPI + PostgreSQL + Redis – fully non‑blocking
[x] Role‑Based Access Control with granular permissions
[x] OTP‑based email/phone verification and password reset (6‑digit numeric codes)
[x] MFA (TOTP) support via Google Authenticator
[x] Multi‑tenant data isolation (restaurant_id foreign key everywhere)
[x] Indian GST calculation (CGST/SGST/IGST) on invoices
[x] Real‑time Kitchen Display via WebSocket + Redis pub/sub
[x] Automatic inventory deduction on order fulfilment
[x] Full audit log on every INSERT/UPDATE/DELETE
[x] Razorpay subscription billing with webhook HMAC verification
[x] Exportable reports (CSV, XLSX, PDF)
[x] Rate limiting on all auth endpoints
[x] Alembic migration history
[x] Unit‑test skeletons (pytest) – ready to expand
📚 Where to Look Next
app/main.py – FastAPI app creation, middleware registration, router inclusion.
modules/auth/service.py – Core auth logic (OTP generation, JWT handling).
modules/tenancy/models.py – Tenant relationship definitions.
modules/kds/router.py – WebSocket endpoint for the kitchen screen.
modules/billing/service.py – GST calculation helper functions.
core/audit.py – How every DB write is automatically recorded.

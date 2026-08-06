import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError

# Import audit listeners so they get registered on startup
import app.core.audit
from app.common.exceptions import AppException, app_exception_handler
from app.core.config import settings
from app.core.context import request_info
from app.core.limiter import limiter
from app.core.redis import close_redis

# Import all models to ensure SQLAlchemy compiles all relationships and FKs
# Import routers
from app.modules.auth.router import router as auth_router
from app.modules.billing.router import router as billing_router
from app.modules.crm.router import router as crm_router
from app.modules.inventory.router import router as inventory_router
from app.modules.kds.router import router as kds_router
from app.modules.menu.router import router as menu_router
from app.modules.operations.router import router as operations_router
from app.modules.orders.router import router as orders_router
from app.modules.reports.router import router as reports_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.tenancy.router import router as tenancy_router

# Set up logging
log_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Sentry (optional observability) ──────────────────────────────────────────
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info("Starting up DineOS application…")

    # ── Startup Health Checks ─────────────────────────────────────────────
    # 1. PostgreSQL connection check
    try:
        from sqlalchemy import text

        from app.core.db import engine
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            pg_version = result.scalar()
            logger.info(f"✅ PostgreSQL connected — {pg_version}")

            # Show which database we're connected to
            result = await conn.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()"))
            row = result.one()
            logger.info(f"   📦 Database: {row[0]} | User: {row[1]} | Host: {row[2]}:{row[3]}")

            # Count tables
            result = await conn.execute(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            table_count = result.scalar()
            logger.info(f"   📊 Tables in schema: {table_count}")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection FAILED: {e}")

    # 2. Redis connection check
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        pong = await redis_client.ping()
        info = await redis_client.info(section="server")
        redis_version = info.get("redis_version", "unknown")
        logger.info(f"✅ Redis connected — v{redis_version} (PING → {'PONG' if pong else 'FAIL'})")

        # Show Redis memory usage
        mem_info = await redis_client.info(section="memory")
        used_memory = mem_info.get("used_memory_human", "N/A")
        logger.info(f"   💾 Memory used: {used_memory}")
    except Exception as e:
        logger.error(f"❌ Redis connection FAILED: {e}")

    # 3. Show app configuration summary
    logger.info(f"🔧 Environment: {settings.APP_ENV}")
    logger.info(f"🔧 CORS Origins: {settings.ALLOWED_ORIGINS}")
    logger.info("🚀 DineOS is ready! API docs → http://127.0.0.1:8000/docs")

    yield

    logger.info("Shutting down DineOS application…")
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 🍽️ DineOS — Restaurant Management SaaS

A **multi-tenant**, production-ready Restaurant Management Platform built with
**FastAPI · PostgreSQL · Redis · Celery · React 18 · TypeScript**.

---

## ⚡ Quick Start — How to Authenticate

> **You must authorize before calling any protected endpoint.**

### Step 1 — Register an Owner account
```
POST /api/v1/auth/register
{ "email": "you@restaurant.com", "password": "yourpassword", "full_name": "Your Name" }
```

### Step 2 — Authorize in Swagger
1. Click the **🔒 Authorize** button (top-right)
2. Enter your **email** in the `username` field and your `password`
3. Leave `client_id` and `client_secret` **blank**
4. Click **Authorize** → all endpoints are now unlocked

### Step 3 — Seed roles *(first time only)*
```
POST /api/v1/auth/seed
```

---

## 🌱 Demo Seed Data & Credentials

To test all modules and workflows end-to-end with realistic Indian restaurant data, you can seed the database using:
```bash
# Run from backend/ directory
python -m app.scripts.seed_demo
```
To wipe and reseed:
```bash
python -m app.scripts.seed_demo --reset
```

### Login Credentials (All passwords: `Password123!`)

| Role | Email | Scope |
|---|---|---|
| **super_admin** | `superadmin@dineos.demo` | Global system control (not attached to a restaurant) |
| **owner** | `owner@spiceroute.demo` | Full restaurant access |
| **manager** | `manager@spiceroute.demo` | Branch management |
| **cashier** | `cashier@spiceroute.demo` | POS & Billing |
| **waiter** | `waiter@spiceroute.demo` | Table orders |
| **kitchen** | `kitchen@spiceroute.demo` | Kitchen KDS ticket handler |

### Preloaded Test Cases
* **Restaurant**: "Spice Route" (GSTIN: `07AABCS1429B1Z0`)
* **Branches**: "Main Street" & "Mall Road"
* **Loyalty Points Test**: "Rohit Mehta" (`+919876543210`) has **250 points** preloaded for immediate redemption tests.
* **Low-Stock Alert**: **Saffron** is seeded at exactly its low-stock threshold (10.000g). Serving any saffron dish will trigger the low-stock notification.

---

## 🗺️ Module Map

| Tag | What it does |
|---|---|
| **Authentication** | Register · Login · Refresh · Logout · Sessions · OTP · Password Reset · MFA |
| **Tenancy** | Create restaurant · Manage branches · Per-tenant settings |
| **Menu** | Categories · Items · Variants · Add-ons · Availability · Branch price overrides |
| **Orders** | Place order · Update status · KOT tickets · Idempotency |
| **KDS** | WebSocket kitchen display — live ticket stream via Redis Pub/Sub |
| **Billing** | Generate invoice · CGST/SGST/IGST calculation · Record payment · Refunds |
| **Inventory** | Ingredients · Units · Stock adjustments · Recipes · Auto-deduction |
| **Operations** | Floors · Table sections · Dining tables · Tips · Staff allocation |
| **CRM** | Customer lookup · Visit tracking · Loyalty points · Feedback |
| **Reports** | Sales · GST (GSTR-1/3B) · Inventory · CSV / XLSX / PDF export |
| **Subscriptions** | Plans · Razorpay checkout · Webhook verification |
| **System** | Audit logs |

---

## 🔄 Typical Workflows

### 🧾 Taking a Dine-In Order (POS Flow)
```
1. POST /menu/categories          → Create category (e.g. "Starters")
2. POST /menu/items               → Add item with price & GST rate
3. POST /orders                   → Place order { order_type: "dine_in", items: [...] }
4. PATCH /orders/{id}/status      → Move: placed → confirmed → preparing → ready → served
5. POST /billing/invoices         → Generate invoice (auto-calculates CGST/SGST)
6. POST /billing/payments         → Record payment (cash / UPI / card / online)
```

### 🏪 Setting Up a New Restaurant
```
1. POST /auth/register            → Create owner account
2. POST /auth/seed                → Seed roles & permissions
3. POST /tenancy/restaurants      → Create restaurant profile
4. POST /tenancy/branches         → Add branch(es)
5. POST /menu/categories          → Build menu
6. POST /operations/floors        → Add floor layout
7. POST /operations/tables        → Add tables to sections
```

### 📦 Inventory & Auto Stock Deduction
```
1. POST /inventory/ingredients    → Add ingredient (e.g. "Tomato", unit: "kg")
2. POST /inventory/recipes        → Link recipe to menu item with quantities
3. POST /inventory/adjust         → Manually adjust stock
   ↓ Automatic:
4. When order status → SERVED     → Stock deducted via recipe quantities
5. GET  /reports/inventory        → View current stock levels & low-stock alerts
```

### 💳 Loyalty & CRM
```
1. GET  /crm/customers?phone=...  → Lookup or auto-create customer by phone
2. POST /billing/payments         → 10% of payment auto-credited as loyalty points
3. POST /crm/loyalty/redeem       → Redeem points against an order
4. POST /crm/feedback             → Record rating + comments
```

### 📊 Reports & Exports
```
GET /reports/sales?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
GET /reports/gst?start_date=...&end_date=...
GET /reports/inventory
GET /reports/sales/export?format=csv      → Download CSV
GET /reports/sales/export?format=xlsx     → Download Excel
GET /reports/sales/export?format=pdf      → Download PDF
```

---

## 🔐 Security Model

| Mechanism | Detail |
|---|---|
| **Passwords** | Argon2id hashing — never stored plain |
| **Tokens** | JWT access (15 min) + refresh (7 days) with `jti` uniqueness |
| **Sessions** | Every login tracked; remote logout supported |
| **MFA** | Optional TOTP (Google Authenticator compatible) |
| **Phone OTP** | 6-digit Redis-backed code, 5-minute expiry |
| **Rate Limiting** | Auth endpoints protected with slowapi |
| **Audit Logs** | Every DB write logged with user + IP |
| **RBAC** | Roles: `super_admin · owner · manager · staff · cashier · customer` |

---

## 🌐 Environment
- **Backend**: `http://127.0.0.1:8000`
- **Frontend**: `http://127.0.0.1:5173`
- **Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
""",
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

os.makedirs("uploads", exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS Middleware — restrictive configuration for security compliance
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Restaurant-ID", "X-Branch-ID", "Accept"],
)

# Register custom exception handler
app.add_exception_handler(AppException, app_exception_handler)



@app.exception_handler(OperationalError)
async def sqlalchemy_operational_error_handler(request: Request, exc: OperationalError):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "SERVICE_UNAVAILABLE", "message": "Database connection failed or is offline."}}
    )

@app.exception_handler(ConnectionRefusedError)
async def connection_refused_handler(request: Request, exc: ConnectionRefusedError):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "SERVICE_UNAVAILABLE", "message": "Backend service connection refused (Database or Redis offline)."}}
    )

# Request context middleware for Audit Logging
@app.middleware("http")
async def add_request_context_middleware(request: Request, call_next):
    user_id = None
    token = None

    # Try Authorization header first
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Check cookie
        token = request.cookies.get("access_token")

    if token:
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            if payload.get("type") == "access":
                user_id = payload.get("sub")
        except Exception:
            pass

    # Don't use stale decoded token user_id on login endpoint
    if request.url.path.endswith("/auth/login"):
        user_id = None
    r_id_str = request.query_params.get("restaurant_id")

    req_data = {
        "user_id": user_id,
        "restaurant_id": r_id_str,
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }

    token_reset = request_info.set(req_data)
    try:
        response = await call_next(request)
        return response
    finally:
        request_info.reset(token_reset)


# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenancy_router, prefix="/api/v1")
app.include_router(menu_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(kds_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(subscriptions_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(crm_router, prefix="/api/v1")



@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "environment": settings.APP_ENV, "version": settings.APP_VERSION}

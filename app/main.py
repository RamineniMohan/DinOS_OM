from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.cart import router as cart_router
from app.api.v1.routers.history import router as history_router
from app.api.v1.routers.kot import router as kot_router
from app.api.v1.routers.order import router as order_router
from app.api.v1.routers.status import router as status_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


# ==========================================
# Database Startup
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


# ==========================================
# FastAPI App
# ==========================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Restaurant POS - Order Management API",
    lifespan=lifespan,
)


# ==========================================
# Root Endpoint
# ==========================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Restaurant POS Order Management API",
        "version": settings.APP_VERSION,
        "status": "Running",
    }


# ==========================================
# Health Check
# ==========================================

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
    }


# ==========================================
# API Routers
# ==========================================

app.include_router(cart_router)
app.include_router(order_router)
app.include_router(kot_router)
app.include_router(status_router)
app.include_router(history_router)
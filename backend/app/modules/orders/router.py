import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginationParams
from app.core.db import get_db
from app.core.deps import get_current_tenant, get_current_user, require_role
from app.modules.orders.schemas import OrderCreate, OrderResponse, OrderStatusUpdate
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    schema: OrderCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "waiter", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Place a new order (dine-in or takeaway)."""
    return await OrderService.create_order(db, current_tenant.id, schema, waiter_id=current_user.id)


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    orders = await OrderService.list_orders(db, current_tenant.id, status_filter, pagination)
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.get_order(db, order_id, current_tenant.id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_status(
    order_id: uuid.UUID,
    schema: OrderStatusUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "waiter", "kitchen", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update order status. Also publishes to Redis for KDS WebSocket subscribers."""
    return await OrderService.update_status(db, order_id, current_tenant.id, schema, changed_by=current_user.id)

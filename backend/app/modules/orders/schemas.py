import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.modules.orders.models import OrderStatus, OrderType


class OrderAddonCreate(BaseModel):
    addon_id: uuid.UUID
    addon_name: str
    price: Decimal


class OrderAddonResponse(BaseModel):
    id: uuid.UUID
    addon_id: uuid.UUID
    addon_name: str
    price: Decimal
    model_config = {'from_attributes': True}


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    item_name: str
    quantity: int
    unit_price: Decimal
    notes: str | None = None
    addons: list[OrderAddonCreate] = []


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    item_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    notes: str | None = None
    addons: list[OrderAddonResponse] = []
    model_config = {'from_attributes': True}


class OrderCreate(BaseModel):
    order_type: OrderType
    branch_id: uuid.UUID | None = None
    table_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    notes: str | None = None
    idempotency_key: str | None = None
    items: list[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: str | None = None


class StatusHistoryResponse(BaseModel):
    id: uuid.UUID
    old_status: str | None = None
    new_status: str
    notes: str | None = None
    created_at: datetime
    model_config = {'from_attributes': True}


class KotTicketResponse(BaseModel):
    id: uuid.UUID
    ticket_number: str
    status: str
    items_json: str
    created_at: datetime
    model_config = {'from_attributes': True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    order_number: str
    order_type: OrderType
    status: OrderStatus
    table_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    notes: str | None = None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    tip_amount: Decimal
    total_amount: Decimal
    inventory_deducted: bool = False
    stock_deduction_warning: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []
    status_history: list[StatusHistoryResponse] = []
    kot_tickets: list[KotTicketResponse] = []
    model_config = {'from_attributes': True}

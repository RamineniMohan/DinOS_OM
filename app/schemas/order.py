from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.core.enums import OrderStatus, KOTStatus


# ==========================================
# Create Order
# ==========================================

class CreateOrderRequest(BaseModel):
    cart_id: UUID


# ==========================================
# Update Order Status
# ==========================================

class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


# ==========================================
# Order Item Response
# ==========================================

class OrderItemResponse(BaseModel):
    id: UUID
    menu_item_id: UUID
    item_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    special_instructions: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# KOT Response
# ==========================================

class KOTResponse(BaseModel):
    id: UUID
    kot_number: str
    status: KOTStatus

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Order Response
# ==========================================

class OrderResponse(BaseModel):
    id: UUID
    order_number: str

    customer_id: Optional[UUID]

    cart_id: UUID

    table_number: Optional[str]

    order_type: str

    status: OrderStatus

    subtotal: Decimal

    tax: Decimal

    discount: Decimal

    total: Decimal

    created_at: datetime

    updated_at: datetime

    items: list[OrderItemResponse] = []

    kot: Optional[KOTResponse] = None

    model_config = ConfigDict(from_attributes=True)
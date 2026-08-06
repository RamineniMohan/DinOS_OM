from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import OrderStatus


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


class OrderStatusResponse(BaseModel):
    id: UUID
    order_number: str
    status: OrderStatus
    updated_at: datetime

    class Config:
        from_attributes = True
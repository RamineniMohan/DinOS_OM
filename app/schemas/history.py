from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import OrderStatus


class OrderHistoryResponse(BaseModel):
    id: UUID
    order_number: str
    table_number: str | None
    total: Decimal
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True
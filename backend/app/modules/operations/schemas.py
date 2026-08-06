import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FloorCreate(BaseModel):
    branch_id: uuid.UUID | None = None
    name: str
    sort_order: int = 0

class FloorResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    model_config = {'from_attributes': True}


class TableSectionCreate(BaseModel):
    floor_id: uuid.UUID
    name: str

class TableSectionResponse(BaseModel):
    id: uuid.UUID
    floor_id: uuid.UUID
    name: str
    is_active: bool
    model_config = {'from_attributes': True}


class DiningTableCreate(BaseModel):
    section_id: uuid.UUID | None = None
    table_number: str
    capacity: int = 4

class DiningTableUpdate(BaseModel):
    capacity: int | None = None
    is_occupied: bool | None = None
    is_active: bool | None = None

class DiningTableResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    section_id: uuid.UUID | None = None
    table_number: str
    capacity: int
    is_occupied: bool
    is_active: bool
    created_at: datetime
    model_config = {'from_attributes': True}


class TipAllocationCreate(BaseModel):
    staff_id: uuid.UUID
    amount: Decimal
    percentage_share: Decimal

class TipAllocationResponse(BaseModel):
    id: uuid.UUID
    tip_id: uuid.UUID
    staff_id: uuid.UUID
    amount: Decimal
    percentage_share: Decimal
    model_config = {'from_attributes': True}

class TipCreate(BaseModel):
    order_id: uuid.UUID
    amount: Decimal
    tip_type: str
    percentage: Decimal | None = None
    allocations: list[TipAllocationCreate] = []

class TipResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    tip_type: str
    percentage: Decimal | None = None
    created_at: datetime
    allocations: list[TipAllocationResponse] = []
    model_config = {'from_attributes': True}

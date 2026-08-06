import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class UnitBase(BaseModel):
    name: str
    abbreviation: str

class UnitCreate(UnitBase):
    pass

class UnitResponse(UnitBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    model_config = {'from_attributes': True}


class IngredientBase(BaseModel):
    name: str
    unit_id: uuid.UUID
    current_stock: Decimal = Decimal('0')
    low_stock_threshold: Decimal = Decimal('0')
    cost_per_unit: Decimal = Decimal('0')

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(BaseModel):
    name: str | None = None
    current_stock: Decimal | None = None
    low_stock_threshold: Decimal | None = None
    cost_per_unit: Decimal | None = None

class IngredientResponse(IngredientBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    unit: UnitResponse | None = None
    is_active: bool
    created_at: datetime
    model_config = {'from_attributes': True}


class StockAdjustment(BaseModel):
    ingredient_id: uuid.UUID
    quantity_change: Decimal
    reason: str
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None

class StockLedgerResponse(BaseModel):
    id: uuid.UUID
    ingredient_id: uuid.UUID
    quantity_change: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    reason: str
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    created_at: datetime
    model_config = {'from_attributes': True}


class RecipeIngredientCreate(BaseModel):
    ingredient_id: uuid.UUID
    quantity: Decimal
    unit_id: uuid.UUID

class RecipeIngredientResponse(RecipeIngredientCreate):
    id: uuid.UUID
    recipe_id: uuid.UUID
    model_config = {'from_attributes': True}

class RecipeCreate(BaseModel):
    menu_item_id: uuid.UUID
    name: str
    yield_quantity: Decimal = Decimal('1.0')
    ingredients: list[RecipeIngredientCreate] = []

class RecipeResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    menu_item_id: uuid.UUID
    name: str
    yield_quantity: Decimal
    ingredients: list[RecipeIngredientResponse] = []
    model_config = {'from_attributes': True}


class VendorCreate(BaseModel):
    name: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None

class VendorUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_active: bool | None = None

class VendorResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool
    created_at: datetime
    model_config = {'from_attributes': True}


class POItemCreate(BaseModel):
    ingredient_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal

class POItemResponse(BaseModel):
    id: uuid.UUID
    ingredient_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    model_config = {'from_attributes': True}

class PurchaseOrderCreate(BaseModel):
    vendor_id: uuid.UUID
    notes: str | None = None
    items: list[POItemCreate]

class PurchaseOrderUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None

class PurchaseOrderResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    vendor_id: uuid.UUID
    status: str
    total_amount: Decimal
    notes: str | None
    created_at: datetime
    items: list[POItemResponse] = []
    model_config = {'from_attributes': True}

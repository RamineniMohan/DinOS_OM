import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ItemVariantBase(BaseModel):
    name: str
    price: Decimal
    is_available: bool = True


class ItemVariantCreate(ItemVariantBase):
    pass


class ItemVariantResponse(ItemVariantBase):
    id: uuid.UUID
    item_id: uuid.UUID
    model_config = {'from_attributes': True}


class ItemAddonBase(BaseModel):
    name: str
    price: Decimal
    is_available: bool = True


class ItemAddonCreate(ItemAddonBase):
    pass


class ItemAddonResponse(ItemAddonBase):
    id: uuid.UUID
    item_id: uuid.UUID
    model_config = {'from_attributes': True}


class MenuItemBase(BaseModel):
    name: str
    description: str | None = None
    base_price: Decimal
    image_url: str | None = None
    is_veg: bool = True
    is_vegan: bool = False
    is_available: bool = True
    hsn_code: str | None = None
    gst_rate: Decimal | None = None
    sort_order: int = 0
    category_id: uuid.UUID


class MenuItemCreate(MenuItemBase):
    variants: list[ItemVariantCreate] = []
    addons: list[ItemAddonCreate] = []


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price: Decimal | None = None
    image_url: str | None = None
    is_veg: bool | None = None
    is_vegan: bool | None = None
    is_available: bool | None = None
    hsn_code: str | None = None
    gst_rate: Decimal | None = None
    sort_order: int | None = None
    category_id: uuid.UUID | None = None


class MenuItemResponse(MenuItemBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    created_at: datetime
    variants: list[ItemVariantResponse] = []
    addons: list[ItemAddonResponse] = []
    model_config = {'from_attributes': True}


class MenuCategoryBase(BaseModel):
    name: str
    description: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    is_active: bool = True


class MenuCategoryCreate(MenuCategoryBase):
    pass


class MenuCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class MenuCategoryResponse(MenuCategoryBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    created_at: datetime
    items: list[MenuItemResponse] = []
    model_config = {'from_attributes': True}


class AvailabilityToggle(BaseModel):
    is_available: bool


class MenuItemBranchPriceCreate(BaseModel):
    menu_item_id: uuid.UUID
    branch_id: uuid.UUID
    price: Decimal


class MenuItemBranchPriceResponse(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID
    branch_id: uuid.UUID
    price: Decimal
    created_at: datetime
    model_config = {'from_attributes': True}


class ComboItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = 1

class ComboItemResponse(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID
    quantity: int
    model_config = {'from_attributes': True}

class ComboCreate(BaseModel):
    name: str
    description: str | None = None
    price: Decimal
    is_active: bool = True
    items: list[ComboItemCreate]

class ComboUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    is_active: bool | None = None

class ComboResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    is_active: bool
    created_at: datetime
    items: list[ComboItemResponse] = []
    model_config = {'from_attributes': True}


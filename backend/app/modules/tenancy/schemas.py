import uuid
from datetime import datetime

from pydantic import BaseModel


class BranchBase(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = 'India'
    pincode: str | None = None
    phone: str | None = None
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class BranchResponse(BranchBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    created_at: datetime

    model_config = {'from_attributes': True}


class RestaurantSettingsBase(BaseModel):
    currency: str = 'INR'
    timezone: str = 'Asia/Kolkata'
    tax_enabled: bool = True
    service_charge_pct: float = 0.0
    gst_number: str | None = None
    fssai_number: str | None = None
    logo_url: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class RestaurantSettingsUpdate(BaseModel):
    currency: str | None = None
    timezone: str | None = None
    tax_enabled: bool | None = None
    service_charge_pct: float | None = None
    gst_number: str | None = None
    fssai_number: str | None = None
    logo_url: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class RestaurantSettingsResponse(RestaurantSettingsBase):
    id: uuid.UUID
    restaurant_id: uuid.UUID

    model_config = {'from_attributes': True}


class RestaurantBase(BaseModel):
    name: str
    slug: str
    plan: str = 'trial'


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class RestaurantResponse(RestaurantBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    settings: RestaurantSettingsResponse | None = None
    branches: list[BranchResponse] = []

    model_config = {'from_attributes': True}

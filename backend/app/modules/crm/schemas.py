import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    restaurant_id: uuid.UUID
    name: str
    phone: str
    email: str | None
    loyalty_points: int
    visits_count: int
    created_at: datetime


class LoyaltyTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    points_change: int
    transaction_type: str
    description: str | None
    created_at: datetime


class RedeemPointsRequest(BaseModel):
    customer_id: uuid.UUID
    points_to_redeem: int
    order_id: uuid.UUID | None = None


class FeedbackCreate(BaseModel):
    order_id: uuid.UUID
    rating: int  # 1-5
    comments: str | None = None
    customer_id: uuid.UUID | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_id: uuid.UUID
    rating: int
    comments: str | None
    created_at: datetime


class MembershipTierCreate(BaseModel):
    name: str
    min_points: int = 0
    discount_percentage: float = 0.0
    benefits: str | None = None

class MembershipTierResponse(MembershipTierCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    restaurant_id: uuid.UUID
    created_at: datetime


class OfferCreate(BaseModel):
    title: str
    description: str | None = None
    discount_type: str
    discount_value: float
    min_order_value: float = 0.0
    valid_from: datetime | None = None
    valid_until: datetime | None = None

class OfferResponse(OfferCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    restaurant_id: uuid.UUID
    is_active: bool
    created_at: datetime


class CouponCreate(BaseModel):
    code: str
    offer_id: uuid.UUID
    max_uses: int | None = None

class CouponResponse(CouponCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    restaurant_id: uuid.UUID
    current_uses: int
    is_active: bool
    created_at: datetime
    offer: OfferResponse | None = None

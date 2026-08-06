import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SubscriptionPlanBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    price_monthly: Decimal
    price_yearly: Decimal
    max_branches: int = 1
    max_users: int = 10
    trial_days: int = 14

class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass
class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: uuid.UUID
    is_active: bool
    razorpay_plan_id_monthly: str | None = None
    razorpay_plan_id_yearly: str | None = None
    created_at: datetime
    model_config = {'from_attributes': True}


class SubscriptionCreate(BaseModel):
    plan_id: uuid.UUID
    razorpay_subscription_id: str | None = None

class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    razorpay_subscription_id: str | None = None
    created_at: datetime
    model_config = {'from_attributes': True}


class RazorpayWebhookPayload(BaseModel):
    event: str
    payload: dict

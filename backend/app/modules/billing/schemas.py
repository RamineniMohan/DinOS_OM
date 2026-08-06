import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.billing.models import GSTType, PaymentMethod, PaymentStatus


class InvoiceItemBase(BaseModel):
    item_name: str
    hsn_code: str | None = None
    quantity: int
    unit_price: Decimal
    gst_rate: Decimal = Decimal('0')
    cgst_amount: Decimal = Decimal('0')
    sgst_amount: Decimal = Decimal('0')
    igst_amount: Decimal = Decimal('0')
    total_amount: Decimal


class InvoiceItemResponse(InvoiceItemBase):
    id: uuid.UUID
    invoice_id: uuid.UUID
    model_config = {'from_attributes': True}


class InvoiceCreate(BaseModel):
    order_id: uuid.UUID
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_gstin: str | None = None
    gst_type: GSTType = GSTType.CGST_SGST
    discount_amount: Decimal = Decimal('0')
    tip_amount: Decimal = Decimal('0')
    idempotency_key: str | None = None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    order_id: uuid.UUID
    invoice_number: str
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_gstin: str | None = None
    subtotal: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal
    discount_amount: Decimal
    tip_amount: Decimal
    total_amount: Decimal
    payment_status: PaymentStatus
    created_at: datetime
    invoice_items: list[InvoiceItemResponse] = []
    model_config = {'from_attributes': True}


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    method: PaymentMethod
    amount: Decimal
    reference_id: str | None = None
    idempotency_key: str | None = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    method: PaymentMethod
    amount: Decimal
    status: PaymentStatus
    reference_id: str | None = None
    created_at: datetime
    model_config = {'from_attributes': True}


class RefundCreate(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    reason: str | None = None


class RefundResponse(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    amount: Decimal
    reason: str | None = None
    status: str
    created_at: datetime
    model_config = {'from_attributes': True}


class GSTRateCreate(BaseModel):
    name: str
    rate: Decimal
    gst_type: GSTType = GSTType.CGST_SGST


class GSTRateResponse(GSTRateCreate):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    is_active: bool
    model_config = {'from_attributes': True}


class HsnCodeCreate(BaseModel):
    code: str
    description: str
    gst_rate: Decimal


class HsnCodeResponse(HsnCodeCreate):
    id: uuid.UUID
    model_config = {'from_attributes': True}

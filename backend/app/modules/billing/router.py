import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_tenant, get_current_user, require_role
from app.modules.billing.schemas import (
    GSTRateCreate,
    GSTRateResponse,
    HsnCodeCreate,
    HsnCodeResponse,
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
)
from app.modules.billing.service import BillingService

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    schema: InvoiceCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Generate invoice for a completed order. Calculates GST automatically."""
    return await BillingService.create_invoice(db, current_tenant.id, schema)


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await BillingService.list_invoices(db, current_tenant.id)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BillingService.get_invoice(db, invoice_id, current_tenant.id)


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    schema: PaymentCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Record a payment against an invoice."""
    return await BillingService.record_payment(db, current_tenant.id, schema)


@router.post("/gst-rates", response_model=GSTRateResponse, status_code=status.HTTP_201_CREATED)
async def create_gst_rate(
    schema: GSTRateCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await BillingService.create_gst_rate(db, current_tenant.id, schema)


@router.get("/gst-rates", response_model=list[GSTRateResponse])
async def list_gst_rates(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BillingService.list_gst_rates(db, current_tenant.id)


@router.post("/hsn-codes", response_model=HsnCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_hsn_code(
    schema: HsnCodeCreate,
    current_user=Depends(require_role("owner", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await BillingService.create_hsn_code(db, schema)


@router.get("/hsn-codes", response_model=list[HsnCodeResponse])
async def list_hsn_codes(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BillingService.list_hsn_codes(db)

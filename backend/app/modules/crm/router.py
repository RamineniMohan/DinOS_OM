import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_tenant, get_tenant_public, require_role
from app.core.limiter import limiter
from app.modules.crm.schemas import (
    CouponCreate,
    CouponResponse,
    CustomerCreate,
    CustomerResponse,
    FeedbackCreate,
    FeedbackResponse,
    MembershipTierCreate,
    MembershipTierResponse,
    OfferCreate,
    OfferResponse,
    RedeemPointsRequest,
)
from app.modules.crm.service import CRMService

router = APIRouter(prefix='/crm', tags=['CRM & Loyalty'])


@router.get('/customers', response_model=list[CustomerResponse])
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.list_customers(db, current_tenant.id, page=page, page_size=page_size)


@router.get('/customers/{customer_id}', response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'cashier', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.get_customer(db, customer_id, current_tenant.id)


@router.post('/customers/lookup', response_model=CustomerResponse)
async def lookup_or_create_customer(
    schema: CustomerCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('cashier', 'manager', 'owner', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    """Look up customer by phone or auto-create."""
    return await CRMService.get_or_create_customer(
        db, current_tenant.id, schema.phone, schema.name, schema.email
    )


@router.post('/loyalty/redeem')
async def redeem_points(
    schema: RedeemPointsRequest,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('cashier', 'manager', 'owner', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    discount = await CRMService.redeem_points(
        db, schema.customer_id, current_tenant.id, schema.points_to_redeem, schema.order_id
    )
    return {'discount_amount': float(discount), 'message': f'Rs.{discount} discount applied'}


@router.post('/feedback', response_model=FeedbackResponse, status_code=201)
@limiter.limit("5/minute")
async def submit_feedback(
    request: Request,
    schema: FeedbackCreate,
    current_tenant=Depends(get_tenant_public),
    db: AsyncSession = Depends(get_db),
):
    """
    Anyone can submit feedback (no auth required for QR-based flows).
    Rate-limited to 5 requests per minute per IP to prevent spam.
    Validates that the order_id belongs to this restaurant before saving.
    """
    return await CRMService.add_feedback(db, current_tenant.id, schema)



@router.get('/feedback', response_model=list[FeedbackResponse])
async def list_feedbacks(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.list_feedbacks(db, current_tenant.id)


@router.post('/membership-tiers', response_model=MembershipTierResponse, status_code=201)
async def create_membership_tier(
    schema: MembershipTierCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.create_membership_tier(db, current_tenant.id, schema)


@router.get('/membership-tiers', response_model=list[MembershipTierResponse])
async def list_membership_tiers(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'cashier', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.list_membership_tiers(db, current_tenant.id)


@router.post('/offers', response_model=OfferResponse, status_code=201)
async def create_offer(
    schema: OfferCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.create_offer(db, current_tenant.id, schema)


@router.get('/offers', response_model=list[OfferResponse])
async def list_offers(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'cashier', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.list_offers(db, current_tenant.id)


@router.post('/coupons', response_model=CouponResponse, status_code=201)
async def create_coupon(
    schema: CouponCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.create_coupon(db, current_tenant.id, schema)


@router.get('/coupons', response_model=list[CouponResponse])
async def list_coupons(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'cashier', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.list_coupons(db, current_tenant.id)

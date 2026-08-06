import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_tenant, require_role
from app.modules.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionResponse,
)
from app.modules.subscriptions.service import SubscriptionService

router = APIRouter(prefix='/subscriptions', tags=['Subscriptions'])


@router.get('/plans', response_model=list[SubscriptionPlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    return await SubscriptionService.list_plans(db)


@router.post('/plans', response_model=SubscriptionPlanResponse, status_code=201)
async def create_plan(
    schema: SubscriptionPlanCreate,
    current_user=Depends(require_role('super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await SubscriptionService.create_plan(db, schema)


@router.post('/', response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    schema: SubscriptionCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await SubscriptionService.create_subscription(db, current_tenant.id, schema)


@router.get('/active', response_model=SubscriptionResponse | None)
async def get_active_subscription(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role('owner', 'manager', 'super_admin')),
    db: AsyncSession = Depends(get_db),
):
    return await SubscriptionService.get_active_subscription(db, current_tenant.id)


@router.post('/webhook/razorpay')
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Razorpay webhook handler with HMAC-SHA256 signature verification.
    Razorpay signs the raw request body using the webhook secret.
    """
    raw_body = await request.body()

    # ── Signature verification ──────────────────────────────────────────
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'MISSING_SIGNATURE', 'message': 'X-Razorpay-Signature header is required'},
        )

    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_razorpay_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'INVALID_SIGNATURE', 'message': 'Webhook signature verification failed'},
        )
    # ── End verification ────────────────────────────────────────────────

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={'code': 'INVALID_PAYLOAD', 'message': 'Invalid JSON body'})

    event = payload.get('event', '')
    result = await SubscriptionService.handle_razorpay_webhook(db, event, payload)
    return result

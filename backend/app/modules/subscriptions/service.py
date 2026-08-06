import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from app.modules.subscriptions.schemas import SubscriptionCreate, SubscriptionPlanCreate


class SubscriptionService:

    @staticmethod
    async def create_plan(db: AsyncSession, schema: SubscriptionPlanCreate) -> SubscriptionPlan:
        plan = SubscriptionPlan(**schema.model_dump())
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def list_plans(db: AsyncSession) -> list[SubscriptionPlan]:
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.is_active).order_by(SubscriptionPlan.price_monthly)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_plan(db: AsyncSession, plan_id: uuid.UUID) -> SubscriptionPlan:
        result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError("Subscription plan not found")
        return plan

    @staticmethod
    async def create_subscription(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: SubscriptionCreate
    ) -> Subscription:
        plan = await SubscriptionService.get_plan(db, schema.plan_id)
        sub = Subscription(
            restaurant_id=restaurant_id,
            plan_id=plan.id,
            status='active',
            razorpay_subscription_id=schema.razorpay_subscription_id,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub

    @staticmethod
    async def get_active_subscription(
        db: AsyncSession, restaurant_id: uuid.UUID
    ) -> Subscription | None:
        result = await db.execute(
            select(Subscription).where(
                Subscription.restaurant_id == restaurant_id,
                Subscription.status == 'active',
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def handle_razorpay_webhook(db: AsyncSession, event: str, payload: dict) -> dict:
        """
        Handle Razorpay webhook events.
        Supported events: subscription.activated, subscription.cancelled, payment.captured
        """
        if event == 'subscription.activated':
            razorpay_sub_id = payload.get('payload', {}).get('subscription', {}).get('entity', {}).get('id')
            if razorpay_sub_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.razorpay_subscription_id == razorpay_sub_id)
                )
                sub = result.scalar_one_or_none()
                if sub:
                    sub.status = 'active'
                    await db.commit()
        elif event == 'subscription.cancelled':
            razorpay_sub_id = payload.get('payload', {}).get('subscription', {}).get('entity', {}).get('id')
            if razorpay_sub_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.razorpay_subscription_id == razorpay_sub_id)
                )
                sub = result.scalar_one_or_none()
                if sub:
                    sub.status = 'cancelled'
                    await db.commit()
        return {'status': 'processed', 'event': event}

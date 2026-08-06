import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import AppException, ConflictError, NotFoundError
from app.modules.crm.models import Coupon, Customer, Feedback, LoyaltyTransaction, MembershipTier, Offer
from app.modules.crm.schemas import CouponCreate, FeedbackCreate, MembershipTierCreate, OfferCreate

POINTS_PER_RUPEE_RATIO = Decimal('0.1')   # earn 0.1 pts per ₹1 spent
POINT_VALUE = Decimal('0.50')             # 1 pt = ₹0.50 discount


class CRMService:

    @staticmethod
    async def get_or_create_customer(
        db: AsyncSession, restaurant_id: uuid.UUID, phone: str,
        name: str = 'Guest', email: str | None = None,
    ) -> Customer:
        result = await db.execute(
            select(Customer).where(Customer.restaurant_id == restaurant_id, Customer.phone == phone)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            customer = Customer(
                restaurant_id=restaurant_id,
                name=name,
                phone=phone,
                email=email,
                loyalty_points=0,
                visits_count=0,
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
        return customer

    @staticmethod
    async def list_customers(
        db: AsyncSession, restaurant_id: uuid.UUID, page: int = 1, page_size: int = 50
    ) -> list[Customer]:
        offset = (page - 1) * page_size
        result = await db.execute(
            select(Customer)
            .where(Customer.restaurant_id == restaurant_id)
            .order_by(Customer.name)
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_customer(
        db: AsyncSession, customer_id: uuid.UUID, restaurant_id: uuid.UUID
    ) -> Customer:
        """Fetch a customer, enforcing tenant isolation."""
        result = await db.execute(
            select(Customer)
            .options(selectinload(Customer.transactions), selectinload(Customer.feedbacks))
            .where(Customer.id == customer_id, Customer.restaurant_id == restaurant_id)
        )
        c = result.scalar_one_or_none()
        if not c:
            raise NotFoundError('Customer not found')
        return c

    @staticmethod
    async def accrue_points(
        db: AsyncSession, customer_id: uuid.UUID, restaurant_id: uuid.UUID,
        amount_paid: Decimal, order_id: uuid.UUID | None = None,
    ) -> LoyaltyTransaction | None:
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.restaurant_id == restaurant_id).with_for_update()
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise NotFoundError('Customer not found')

        points = int(amount_paid * POINTS_PER_RUPEE_RATIO)
        if points <= 0:
            return None

        customer.loyalty_points += points
        # Increment visits_count only for unique orders
        if order_id is not None:
            existing_txn = await db.execute(
                select(LoyaltyTransaction).where(
                    LoyaltyTransaction.customer_id == customer_id,
                    LoyaltyTransaction.order_id == order_id,
                    LoyaltyTransaction.transaction_type == 'accrual',
                )
            )
            if not existing_txn.scalar_one_or_none():
                customer.visits_count += 1
        txn = LoyaltyTransaction(
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            order_id=order_id,
            points_change=points,
            transaction_type='accrual',
            description=f'Earned {points} pts on Rs.{amount_paid} payment',
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)
        return txn

    @staticmethod
    async def redeem_points(
        db: AsyncSession, customer_id: uuid.UUID, restaurant_id: uuid.UUID,
        points_to_redeem: int, order_id: uuid.UUID | None = None,
    ) -> Decimal:
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.restaurant_id == restaurant_id).with_for_update()
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise NotFoundError('Customer not found')
        if customer.loyalty_points < points_to_redeem:
            raise AppException('INSUFFICIENT_POINTS', f'Only {customer.loyalty_points} points available', 400)

        discount = Decimal(points_to_redeem) * POINT_VALUE
        customer.loyalty_points -= points_to_redeem
        txn = LoyaltyTransaction(
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            order_id=order_id,
            points_change=-points_to_redeem,
            transaction_type='redemption',
            description=f'Redeemed {points_to_redeem} pts for Rs.{discount} discount',
        )
        db.add(txn)
        await db.commit()
        return discount

    @staticmethod
    async def add_feedback(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: FeedbackCreate
    ) -> Feedback:
        """
        Save customer feedback.
        Validates that the order_id (if provided) belongs to this restaurant
        to prevent cross-tenant feedback injection.
        """
        if schema.order_id:
            from app.modules.orders.models import Order
            order_check = await db.execute(
                select(Order).where(
                    Order.id == schema.order_id,
                    Order.restaurant_id == restaurant_id,
                )
            )
            if not order_check.scalar_one_or_none():
                raise NotFoundError('Order not found for this restaurant')

        existing = await db.execute(
            select(Feedback).where(
                Feedback.order_id == schema.order_id,
                Feedback.restaurant_id == restaurant_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError('Feedback already submitted for this order')

        if not (1 <= schema.rating <= 5):
            raise AppException('INVALID_RATING', 'Rating must be between 1 and 5', 400)

        fb = Feedback(
            restaurant_id=restaurant_id,
            order_id=schema.order_id,
            customer_id=schema.customer_id,
            rating=schema.rating,
            comments=schema.comments,
        )
        db.add(fb)
        await db.commit()
        await db.refresh(fb)
        return fb

    @staticmethod
    async def list_feedbacks(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Feedback]:
        result = await db.execute(
            select(Feedback)
            .where(Feedback.restaurant_id == restaurant_id)
            .order_by(Feedback.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_membership_tier(db: AsyncSession, restaurant_id: uuid.UUID, schema: MembershipTierCreate) -> MembershipTier:
        tier = MembershipTier(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(tier)
        await db.commit()
        await db.refresh(tier)
        return tier

    @staticmethod
    async def list_membership_tiers(db: AsyncSession, restaurant_id: uuid.UUID) -> list[MembershipTier]:
        result = await db.execute(select(MembershipTier).where(MembershipTier.restaurant_id == restaurant_id).order_by(MembershipTier.min_points))
        return list(result.scalars().all())

    @staticmethod
    async def create_offer(db: AsyncSession, restaurant_id: uuid.UUID, schema: OfferCreate) -> Offer:
        offer = Offer(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(offer)
        await db.commit()
        await db.refresh(offer)
        return offer

    @staticmethod
    async def list_offers(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Offer]:
        result = await db.execute(select(Offer).where(Offer.restaurant_id == restaurant_id).order_by(Offer.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def create_coupon(db: AsyncSession, restaurant_id: uuid.UUID, schema: CouponCreate) -> Coupon:
        # Check offer exists
        offer_check = await db.execute(select(Offer).where(Offer.id == schema.offer_id, Offer.restaurant_id == restaurant_id))
        if not offer_check.scalar_one_or_none():
            raise NotFoundError("Offer not found")

        # Check unique code per restaurant (not globally)
        code_check = await db.execute(select(Coupon).where(
            Coupon.code == schema.code,
            Coupon.restaurant_id == restaurant_id,
        ))
        if code_check.scalar_one_or_none():
            raise ConflictError("Coupon code already exists")

        coupon = Coupon(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(coupon)
        await db.commit()

        result = await db.execute(select(Coupon).options(selectinload(Coupon.offer)).where(Coupon.id == coupon.id))
        return result.scalar_one()

    @staticmethod
    async def list_coupons(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Coupon]:
        result = await db.execute(
            select(Coupon).options(selectinload(Coupon.offer))
            .where(Coupon.restaurant_id == restaurant_id)
            .order_by(Coupon.created_at.desc())
        )
        return list(result.scalars().all())

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.billing.models import (
    GSTRate,
    GSTTransaction,
    GSTType,
    HsnCode,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentStatus,
    Refund,
)
from app.modules.billing.schemas import GSTRateCreate, HsnCodeCreate, InvoiceCreate, PaymentCreate, RefundCreate
from app.modules.orders.models import Order, OrderItem, OrderStatus


class BillingService:

    @staticmethod
    def _generate_invoice_number(restaurant_id: uuid.UUID) -> str:
        now = datetime.now(UTC)
        return f"INV-{now.strftime('%Y%m%d')}-{str(restaurant_id)[:4].upper()}-{str(uuid.uuid4())[:6].upper()}"

    @staticmethod
    async def create_invoice(db: AsyncSession, restaurant_id: uuid.UUID, schema: InvoiceCreate) -> Invoice:
        # Idempotency check — one invoice per order with row locking
        ex = await db.execute(
            select(Invoice).where(Invoice.order_id == schema.order_id).with_for_update()
        )
        if ex.scalar_one_or_none():
            raise ConflictError("Invoice already exists for this order")

        # Load order with items & row lock
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.addons))
            .where(Order.id == schema.order_id, Order.restaurant_id == restaurant_id)
            .with_for_update()
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order not found")

        from app.modules.tenancy.models import Restaurant
        rest_res = await db.execute(
            select(Restaurant).options(selectinload(Restaurant.settings)).where(Restaurant.id == restaurant_id)
        )
        restaurant = rest_res.scalar_one_or_none()

        # Decide GST Type based on state codes in GSTIN.
        # Both GSTINs must be present and non-empty for inter-state detection.
        # Absence of either GSTIN defaults to intra-state (CGST+SGST).
        is_inter_state = False
        customer_gstin = (schema.customer_gstin or "").strip()
        restaurant_gstin = (restaurant.gstin if restaurant else "") or ""
        if customer_gstin and restaurant_gstin and len(customer_gstin) >= 2 and len(restaurant_gstin) >= 2:
            if customer_gstin[:2] != restaurant_gstin[:2]:
                is_inter_state = True

        actual_gst_type = GSTType.IGST if is_inter_state else GSTType.CGST_SGST

        subtotal = Decimal('0')
        cgst_total = Decimal('0')
        sgst_total = Decimal('0')
        igst_total = Decimal('0')
        invoice_items_data = []

        for oi in order.items:
            # Fetch actual GST rate from MenuItem
            from app.modules.menu.models import MenuItem
            item_result = await db.execute(
                select(MenuItem).where(MenuItem.id == oi.menu_item_id, MenuItem.restaurant_id == restaurant_id)
            )
            menu_item = item_result.scalar_one_or_none()

            if menu_item and menu_item.gst_rate is not None:
                gst_rate = menu_item.gst_rate
            elif restaurant and restaurant.settings and restaurant.settings.default_gst_rate is not None:
                gst_rate = Decimal(str(restaurant.settings.default_gst_rate))
            else:
                gst_rate = Decimal('5')

            item_subtotal = oi.total_price
            subtotal += item_subtotal

            if actual_gst_type == GSTType.CGST_SGST:
                half_rate = gst_rate / 2
                cgst = (item_subtotal * half_rate / 100).quantize(Decimal('0.01'))
                sgst = cgst
                igst = Decimal('0')
            else:
                cgst = Decimal('0')
                sgst = Decimal('0')
                igst = (item_subtotal * gst_rate / 100).quantize(Decimal('0.01'))

            cgst_total += cgst
            sgst_total += sgst
            igst_total += igst

            invoice_items_data.append({
                'item_name': oi.item_name,
                'quantity': oi.quantity,
                'unit_price': oi.unit_price,
                'gst_rate': gst_rate,
                'cgst_amount': cgst,
                'sgst_amount': sgst,
                'igst_amount': igst,
                'total_amount': item_subtotal + cgst + sgst + igst,
            })

        total_tax = cgst_total + sgst_total + igst_total

        if schema.discount_amount < 0 or schema.discount_amount > (subtotal + total_tax):
            raise ConflictError("Discount amount must be >= 0 and cannot exceed subtotal + tax")

        total_amount = subtotal + total_tax - schema.discount_amount + schema.tip_amount

        invoice = Invoice(
            restaurant_id=restaurant_id,
            branch_id=order.branch_id,
            order_id=order.id,
            invoice_number=BillingService._generate_invoice_number(restaurant_id),
            customer_name=schema.customer_name or order.customer_name,
            customer_phone=schema.customer_phone or order.customer_phone,
            customer_gstin=schema.customer_gstin,
            subtotal=subtotal,
            cgst_amount=cgst_total,
            sgst_amount=sgst_total,
            igst_amount=igst_total,
            total_tax=total_tax,
            discount_amount=schema.discount_amount,
            tip_amount=schema.tip_amount,
            total_amount=total_amount,
            payment_status=PaymentStatus.PENDING,
            gst_type=actual_gst_type,
        )
        db.add(invoice)
        await db.flush()

        for item_data in invoice_items_data:
            db.add(InvoiceItem(invoice_id=invoice.id, **item_data))

        # Record GST Transaction audit entry
        now = datetime.now(UTC)
        db.add(GSTTransaction(
            restaurant_id=restaurant_id,
            invoice_id=invoice.id,
            taxable_amount=subtotal,
            cgst_amount=cgst_total,
            sgst_amount=sgst_total,
            igst_amount=igst_total,
            total_gst=total_tax,
            period_month=now.month,
            period_year=now.year,
        ))

        # Mark order as billed
        order.status = OrderStatus.BILLED
        await db.commit()
        return await BillingService.get_invoice(db, invoice.id)

    @staticmethod
    async def get_invoice(
        db: AsyncSession,
        invoice_id: uuid.UUID,
        restaurant_id: uuid.UUID | None = None,
        for_update: bool = False,
    ) -> Invoice:
        q = (
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments))
            .where(Invoice.id == invoice_id)
        )
        if restaurant_id is not None:
            q = q.where(Invoice.restaurant_id == restaurant_id)
        if for_update:
            q = q.with_for_update()

        result = await db.execute(q)
        inv = result.scalar_one_or_none()
        if not inv:
            raise NotFoundError("Invoice not found")
        return inv

    @staticmethod
    async def list_invoices(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Invoice]:
        result = await db.execute(
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments))
            .where(Invoice.restaurant_id == restaurant_id)
            .order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def record_payment(db: AsyncSession, restaurant_id: uuid.UUID, schema: PaymentCreate) -> Payment:
        inv = await BillingService.get_invoice(db, schema.invoice_id, restaurant_id, for_update=True)

        existing_payments = sum(p.amount for p in inv.payments if p.status == PaymentStatus.PAID)
        remaining_balance = inv.total_amount - existing_payments

        if schema.amount <= 0:
            raise ConflictError("Payment amount must be greater than 0")

        if schema.amount > remaining_balance:
            raise ConflictError(f"Payment amount ({schema.amount}) exceeds remaining balance ({remaining_balance})")

        payment = Payment(
            invoice_id=inv.id,
            method=schema.method,
            amount=schema.amount,
            status=PaymentStatus.PAID,
            transaction_id=schema.reference_id,
        )
        db.add(payment)

        # Update invoice payment status
        new_total_paid = existing_payments + schema.amount
        if new_total_paid >= inv.total_amount:
            inv.payment_status = PaymentStatus.PAID
        else:
            inv.payment_status = PaymentStatus.PARTIALLY_PAID

        await db.commit()

        # Accrue loyalty points if customer phone exists
        if inv.customer_phone:
            try:
                from app.modules.crm.service import CRMService
                customer = await CRMService.get_or_create_customer(
                    db,
                    restaurant_id=restaurant_id,
                    phone=inv.customer_phone,
                    name=inv.customer_name or "Guest"
                )
                await CRMService.accrue_points(
                    db,
                    customer_id=customer.id,
                    restaurant_id=restaurant_id,
                    amount_paid=schema.amount,
                    order_id=inv.order_id
                )
            except Exception as e:
                # Loyalty failure should not block payment recording
                import logging
                logging.getLogger(__name__).error(f"CRM Accrual failed for invoice {inv.id}: {e}")

        await db.refresh(payment)
        return payment

    @staticmethod
    async def process_refund(db: AsyncSession, restaurant_id: uuid.UUID, schema: RefundCreate) -> Refund:
        result = await db.execute(select(Payment).options(selectinload(Payment.invoice)).where(Payment.id == schema.payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")

        if payment.invoice.restaurant_id != restaurant_id:
            raise NotFoundError("Payment not found")

        if payment.status != PaymentStatus.PAID:
            raise ConflictError("Cannot refund an unpaid or failed payment")

        from app.modules.billing.models import Refund
        refunds_result = await db.execute(select(Refund).where(Refund.payment_id == schema.payment_id))
        existing_refunds = list(refunds_result.scalars().all())
        total_refunded = sum(r.amount for r in existing_refunds if r.status != 'failed')

        if total_refunded + schema.amount > payment.amount:
            raise ConflictError("Refund amount exceeds paid amount")

        refund = Refund(
            payment_id=payment.id,
            amount=schema.amount,
            reason=schema.reason,
            status='completed'
        )
        db.add(refund)

        if total_refunded + schema.amount == payment.amount:
            payment.status = PaymentStatus.REFUNDED

        await db.commit()
        await db.refresh(refund)

        # Deduct loyalty points if applicable
        if payment.invoice.customer_phone:
            try:
                from app.modules.crm.service import CRMService
                customer = await CRMService.get_or_create_customer(
                    db,
                    restaurant_id=restaurant_id,
                    phone=payment.invoice.customer_phone,
                    name=payment.invoice.customer_name or "Guest"
                )

                # Deduct points corresponding to the refund amount
                from app.modules.crm.models import LoyaltyTransaction
                points_to_deduct = int(schema.amount * Decimal('0.1'))
                if points_to_deduct > 0 and customer.loyalty_points > 0:
                    actual_deduction = min(points_to_deduct, customer.loyalty_points)
                    customer.loyalty_points -= actual_deduction
                    txn = LoyaltyTransaction(
                        customer_id=customer.id,
                        restaurant_id=restaurant_id,
                        order_id=payment.invoice.order_id,
                        points_change=-actual_deduction,
                        transaction_type='refund',
                        description=f'Deducted {actual_deduction} pts for Rs.{schema.amount} refund',
                    )
                    db.add(txn)
                    await db.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"CRM deduction failed for refund {refund.id}: {e}")

        return refund

    @staticmethod
    async def create_gst_rate(db: AsyncSession, restaurant_id: uuid.UUID, schema: GSTRateCreate) -> GSTRate:
        rate = GSTRate(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(rate)
        await db.commit()
        await db.refresh(rate)
        return rate

    @staticmethod
    async def list_gst_rates(db: AsyncSession, restaurant_id: uuid.UUID) -> list[GSTRate]:
        result = await db.execute(
            select(GSTRate).where(GSTRate.restaurant_id == restaurant_id, GSTRate.is_active)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_hsn_code(db: AsyncSession, schema: HsnCodeCreate) -> HsnCode:
        existing = await db.execute(select(HsnCode).where(HsnCode.code == schema.code))
        if existing.scalar_one_or_none():
            raise ConflictError(f"HSN code {schema.code} already exists")
        code = HsnCode(**schema.model_dump())
        db.add(code)
        await db.commit()
        await db.refresh(code)
        return code

    @staticmethod
    async def list_hsn_codes(db: AsyncSession) -> list[HsnCode]:
        result = await db.execute(select(HsnCode).order_by(HsnCode.code))
        return list(result.scalars().all())

import json
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import ConflictError, NotFoundError
from app.common.pagination import PaginationParams
from app.modules.orders.models import KotTicket, Order, OrderAddon, OrderItem, OrderStatus, OrderStatusHistory
from app.modules.orders.schemas import OrderCreate, OrderStatusUpdate

logger = logging.getLogger(__name__)

# ── Allowed status transitions ────────────────────────────────────────────────
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED:     {OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED:  {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING:  {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY:      {OrderStatus.SERVED, OrderStatus.BILLED, OrderStatus.CANCELLED},
    OrderStatus.SERVED:     {OrderStatus.BILLED},
    OrderStatus.BILLED:     set(),
    OrderStatus.CANCELLED:  set(),
}


class OrderService:

    @staticmethod
    def _generate_order_number() -> str:
        now = datetime.now(UTC)
        return f"ORD-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    @staticmethod
    async def _load_order(
        db: AsyncSession,
        order_id: uuid.UUID,
        restaurant_id: uuid.UUID | None = None,
    ) -> Order:
        q = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
                selectinload(Order.kot_tickets),
            )
            .where(Order.id == order_id)
        )
        # Enforce tenant isolation on every single-resource lookup
        if restaurant_id is not None:
            q = q.where(Order.restaurant_id == restaurant_id)

        result = await db.execute(q)
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order not found")
        return order

    @staticmethod
    async def create_order(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        schema: OrderCreate,
        waiter_id: uuid.UUID | None = None,
    ) -> Order:
        if schema.idempotency_key:
            existing = await db.execute(
                select(Order).where(
                    Order.idempotency_key == schema.idempotency_key,
                    Order.restaurant_id == restaurant_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError("Duplicate order: idempotency key already used")


        resolved_items = []
        subtotal = Decimal("0")
        tax_amount = Decimal("0")
        from app.modules.menu.models import ItemAddon, ItemVariant, MenuItem, MenuItemBranchPrice

        for it in schema.items:
            menu_item_res = await db.execute(
                select(MenuItem).where(MenuItem.id == it.menu_item_id, MenuItem.restaurant_id == restaurant_id)
            )
            menu_item = menu_item_res.scalar_one_or_none()
            if not menu_item:
                raise NotFoundError("Menu item not found")

            unit_price = menu_item.base_price
            item_name = menu_item.name

            if schema.branch_id:
                bp_res = await db.execute(
                    select(MenuItemBranchPrice).where(
                        MenuItemBranchPrice.menu_item_id == menu_item.id,
                        MenuItemBranchPrice.branch_id == schema.branch_id
                    )
                )
                bp = bp_res.scalar_one_or_none()
                if bp:
                    unit_price = bp.price

            if it.variant_id:
                var_res = await db.execute(
                    select(ItemVariant).where(ItemVariant.id == it.variant_id, ItemVariant.item_id == menu_item.id)
                )
                variant = var_res.scalar_one_or_none()
                if not variant:
                    raise NotFoundError("Variant not found")
                unit_price = variant.price
                item_name = f"{menu_item.name} - {variant.name}"

            resolved_addons = []
            addon_total = Decimal("0")
            for addon_req in it.addons:
                addon_res = await db.execute(
                    select(ItemAddon).where(ItemAddon.id == addon_req.addon_id, ItemAddon.item_id == menu_item.id)
                )
                real_addon = addon_res.scalar_one_or_none()
                if not real_addon:
                    raise NotFoundError("Addon not found")

                resolved_addons.append({
                    "addon_id": real_addon.id,
                    "addon_name": real_addon.name,
                    "price": real_addon.price
                })
                addon_total += real_addon.price

            item_subtotal = (unit_price + addon_total) * it.quantity
            subtotal += item_subtotal
            # Compute approximate GST for order-level tax tracking.
            # Exact per-invoice GST is recomputed at billing time.
            # We use a default 5% estimate here; BillingService overrides with real rates.
            tax_amount += (item_subtotal * Decimal("5") / 100).quantize(Decimal("0.01"))

            resolved_items.append({
                "menu_item_id": it.menu_item_id,
                "variant_id": it.variant_id,
                "item_name": item_name,
                "quantity": it.quantity,
                "unit_price": unit_price,
                "notes": it.notes,
                "addons": resolved_addons
            })

        from sqlalchemy.exc import IntegrityError

        order = Order(
            restaurant_id=restaurant_id,
            branch_id=schema.branch_id,
            order_number=OrderService._generate_order_number(),
            order_type=schema.order_type,
            table_id=schema.table_id,
            waiter_id=waiter_id,
            customer_name=schema.customer_name,
            customer_phone=schema.customer_phone,
            notes=schema.notes,
            idempotency_key=schema.idempotency_key,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=subtotal + tax_amount,
        )
        db.add(order)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise ConflictError("Duplicate order: idempotency key already used")

        kot_items = []
        for rit in resolved_items:
            addon_total = sum(a["price"] for a in rit["addons"])
            total_price = (rit["unit_price"] + addon_total) * rit["quantity"]
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=rit["menu_item_id"],
                variant_id=rit["variant_id"],
                item_name=rit["item_name"],
                quantity=rit["quantity"],
                unit_price=rit["unit_price"],
                total_price=total_price,
                notes=rit["notes"],
            )
            db.add(order_item)
            await db.flush()

            for addon in rit["addons"]:
                db.add(OrderAddon(
                    order_item_id=order_item.id,
                    addon_id=addon["addon_id"],
                    addon_name=addon["addon_name"],
                    price=addon["price"],
                ))

            kot_items.append({'name': rit["item_name"], 'qty': rit["quantity"], 'notes': rit["notes"]})

        # Create KOT ticket
        kot = KotTicket(
            order_id=order.id,
            restaurant_id=restaurant_id,
            branch_id=schema.branch_id,
            ticket_number=f"KOT-{order.order_number}",
            items_json=json.dumps(kot_items),
        )
        db.add(kot)

        # Status history
        db.add(OrderStatusHistory(
            order_id=order.id,
            old_status="placed",
            new_status="placed",
            changed_by=waiter_id,
        ))

        await db.commit()

        # Publish to Redis to notify all connected clients to refetch
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            if redis:
                await redis.publish(
                    f"kds:{restaurant_id}",
                    json.dumps({'type': 'invalidate_orders', 'order_id': str(order.id)})
                )
        except Exception:
            pass

        return await OrderService._load_order(db, order.id, restaurant_id)

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        status_filter: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Order]:
        q = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
                selectinload(Order.kot_tickets),
            )
            .where(Order.restaurant_id == restaurant_id)
        )
        if status_filter:
            q = q.where(Order.status == status_filter)
        q = q.order_by(Order.created_at.desc())
        if pagination:
            q = q.offset(pagination.offset).limit(pagination.page_size)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_order(
        db: AsyncSession,
        order_id: uuid.UUID,
        restaurant_id: uuid.UUID | None = None,
    ) -> Order:
        return await OrderService._load_order(db, order_id, restaurant_id)

    @staticmethod
    async def update_status(
        db: AsyncSession,
        order_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        schema: OrderStatusUpdate,
        changed_by: uuid.UUID | None = None,
    ) -> Order:
        # Load order with a row lock to prevent race conditions during state transitions
        q = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
                selectinload(Order.kot_tickets),
            )
            .where(Order.id == order_id, Order.restaurant_id == restaurant_id)
            .with_for_update()
        )
        result = await db.execute(q)
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order not found")

        current_status = order.status

        # ── Enforce state machine ────────────────────────────────────────────
        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if schema.status not in allowed:
            raise ConflictError(
                f"Cannot transition order from '{current_status.value}' to '{schema.status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        old_status = current_status.value
        order.status = schema.status
        db.add(OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=schema.status.value,
            changed_by=changed_by,
            notes=schema.notes,
        ))
        await db.commit()

        # Auto-deduct stock when order is SERVED — runs after the status commit so a
        # bookkeeping failure never rolls back the SERVED transition itself.
        stock_warning: str | None = None
        if schema.status == OrderStatus.SERVED:
            try:
                await OrderService._deduct_inventory(db, order)
            except Exception as exc:
                logger.error(f"Stock deduction failed for order {order.id}: {exc}")
                stock_warning = (
                    "Order was marked as served, but automatic stock deduction failed. "
                    "Please check and adjust inventory manually for this order."
                )

        # Publish to Redis for KDS and Orders pages
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            if redis:
                await redis.publish(
                    f"kds:{order.restaurant_id}",
                    json.dumps({'type': 'invalidate_orders', 'order_id': str(order.id)})
                )
        except Exception:
            pass  # Redis publish failure should not break the HTTP response

        result = await OrderService._load_order(db, order_id, restaurant_id)
        # Attach transient warning — lives only on this response object, never persisted
        if stock_warning:
            result.stock_deduction_warning = stock_warning  # type: ignore[attr-defined]
        return result

    @staticmethod
    async def _deduct_inventory(db: AsyncSession, order: Order) -> None:
        """
        Deduct ingredient stock for every item in the order using its Recipe.
        Uses SELECT FOR UPDATE to prevent race conditions on concurrent served events.
        Guards against double-deduction via the persisted `inventory_deducted` DB column.
        """
        # Guard: skip if already deducted for this order (durable — survives process restarts)
        if order.inventory_deducted:
            logger.warning(f"Inventory already deducted for order {order.id}, skipping.")
            return

        try:
            from app.modules.inventory.models import Ingredient, Recipe, StockLedger
            for oi in order.items:
                recipe_result = await db.execute(
                    select(Recipe)
                    .options(selectinload(Recipe.ingredients))
                    .where(Recipe.menu_item_id == oi.menu_item_id, Recipe.restaurant_id == order.restaurant_id, Recipe.is_active)
                )
                recipe = recipe_result.scalar_one_or_none()
                if not recipe:
                    continue

                for ri in recipe.ingredients:
                    # SELECT FOR UPDATE — locks the row to prevent concurrent stock corruption
                    ing_result = await db.execute(
                        select(Ingredient)
                        .where(Ingredient.id == ri.ingredient_id, Ingredient.restaurant_id == order.restaurant_id)
                        .with_for_update()
                    )
                    ing = ing_result.scalar_one_or_none()
                    if not ing:
                        continue

                    qty_to_deduct = ri.quantity * oi.quantity
                    qty_before = ing.current_stock

                    # Prevent stock from going negative
                    if qty_before < qty_to_deduct:
                        logger.warning(
                            f"Insufficient stock for ingredient '{ing.name}' "
                            f"(have {qty_before}, need {qty_to_deduct}). Clamping to 0."
                        )
                        qty_to_deduct = qty_before  # clamp — never go below zero

                    qty_after = qty_before - qty_to_deduct
                    ing.current_stock = qty_after

                    db.add(StockLedger(
                        restaurant_id=order.restaurant_id,
                        ingredient_id=ing.id,
                        quantity_change=-qty_to_deduct,
                        quantity_before=qty_before,
                        quantity_after=qty_after,
                        reason='order_served',
                        reference_type='order',
                        reference_id=order.id,
                    ))

                    if qty_after <= ing.low_stock_threshold:
                        try:
                            from app.workers.tasks import notify_low_stock
                            notify_low_stock.delay(str(ing.id), str(order.restaurant_id))
                        except Exception:
                            pass

            # Mark order so we never deduct twice
            order.inventory_deducted = True
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f'Stock deduction failed for order {order.id}: {e}')
            raise

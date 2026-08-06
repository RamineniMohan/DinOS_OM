from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.order_item import OrderItem


class OrderRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # Create Order
    # ==========================================

    async def create_order(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    # ==========================================
    # Create Order Item
    # ==========================================

    async def create_order_item(self, item: OrderItem) -> OrderItem:
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    # ==========================================
    # Get Order By ID
    # ==========================================

    async def get_order_by_id(self, order_id: UUID):

        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.kot),
            )
            .where(Order.id == order_id)
        )

        return result.scalar_one_or_none()

    # ==========================================
    # Get Order By Number
    # ==========================================

    async def get_order_by_number(self, order_number: str):

        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.kot),
            )
            .where(Order.order_number == order_number)
        )

        return result.scalar_one_or_none()

    # ==========================================
    # Get Orders By Status
    # ==========================================

    async def get_orders_by_status(self, status):

        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.kot),
            )
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
        )

        return result.scalars().all()

    # ==========================================
    # Get All Orders
    # ==========================================

    async def get_all_orders(self):

        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.kot),
            )
            .order_by(Order.created_at.desc())
        )

        return result.scalars().all()

    # ==========================================
    # Update Order
    # ==========================================

    async def update_order(self, order: Order):

        await self.db.flush()
        await self.db.refresh(order)

        return order

    # ==========================================
    # Delete Order
    # ==========================================

    async def delete_order(self, order: Order):

        await self.db.delete(order)
        await self.db.flush()
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart
from app.models.cart_item import CartItem


class CartRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------
    # Cart
    # -------------------------

    async def create_cart(self, cart: Cart):
        self.db.add(cart)
        await self.db.commit()
        await self.db.refresh(cart)

        # Reload with items relationship
        return await self.get_cart_by_id(cart.id)

    async def get_cart_by_id(self, cart_id: UUID):
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.id == cart_id)
        )
        return result.scalar_one_or_none()

    async def update_cart(self, cart: Cart):
        await self.db.commit()
        await self.db.refresh(cart)

        return await self.get_cart_by_id(cart.id)

    # -------------------------
    # Cart Items
    # -------------------------

    async def add_item(self, item: CartItem):
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_item(self, item_id: UUID):
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_cart_item(self, cart_id: UUID, menu_item_id: UUID):
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart_id,
                CartItem.menu_item_id == menu_item_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_item(self, item: CartItem):
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_item(self, item: CartItem):
        await self.db.delete(item)
        await self.db.commit()

    async def clear_cart(self, cart_id: UUID):
        await self.db.execute(
            delete(CartItem).where(CartItem.cart_id == cart_id)
        )
        await self.db.commit()
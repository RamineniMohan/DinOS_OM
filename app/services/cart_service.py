from decimal import Decimal
from uuid import UUID

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.repositories.cart_repository import CartRepository
from app.schemas.cart import (
    AddCartItemRequest,
    CreateCartRequest,
    UpdateCartItemRequest,
)


class CartService:

    def __init__(self, repository: CartRepository):
        self.repository = repository

    # ==========================================
    # Create Cart
    # ==========================================

    async def create_cart(self, request: CreateCartRequest):

        cart = Cart(
            customer_id=request.customer_id,
            table_number=request.table_number,
            order_type=request.order_type.lower(),
            subtotal=Decimal("0.00"),
            tax=Decimal("0.00"),
            discount=Decimal("0.00"),
            total=Decimal("0.00"),
        )

        return await self.repository.create_cart(cart)

    # ==========================================
    # Get Cart
    # ==========================================

    async def get_cart(self, cart_id: UUID):

        cart = await self.repository.get_cart_by_id(cart_id)

        if not cart:
            raise ValueError("Cart not found")

        return cart

    # ==========================================
    # Add Item
    # ==========================================

    async def add_item(
        self,
        cart_id: UUID,
        request: AddCartItemRequest,
    ):

        cart = await self.repository.get_cart_by_id(cart_id)

        if not cart:
            raise ValueError("Cart not found")

        existing_item = await self.repository.get_cart_item(
            cart_id,
            request.menu_item_id,
        )

        if existing_item:

            existing_item.quantity += request.quantity
            existing_item.total_price = (
                existing_item.unit_price * existing_item.quantity
            )

            await self.repository.update_item(existing_item)

        else:

            item = CartItem(
                cart_id=cart_id,
                menu_item_id=request.menu_item_id,
                item_name=request.item_name,
                quantity=request.quantity,
                unit_price=request.unit_price,
                total_price=request.unit_price * request.quantity,
                special_instructions=request.special_instructions,
            )

            await self.repository.add_item(item)

        return await self.recalculate_cart(cart_id)

    # ==========================================
    # Update Item Quantity
    # ==========================================

    async def update_item(
        self,
        item_id: UUID,
        request: UpdateCartItemRequest,
    ):

        item = await self.repository.get_item(item_id)

        if not item:
            raise ValueError("Item not found")

        item.quantity = request.quantity
        item.total_price = item.unit_price * item.quantity

        await self.repository.update_item(item)

        return await self.recalculate_cart(item.cart_id)

    # ==========================================
    # Remove Item
    # ==========================================

    async def remove_item(
        self,
        item_id: UUID,
    ):

        item = await self.repository.get_item(item_id)

        if not item:
            raise ValueError("Item not found")

        cart_id = item.cart_id

        await self.repository.delete_item(item)

        return await self.recalculate_cart(cart_id)

    # ==========================================
    # Clear Cart
    # ==========================================

    async def clear_cart(
        self,
        cart_id: UUID,
    ):

        cart = await self.repository.get_cart_by_id(cart_id)

        if not cart:
            raise ValueError("Cart not found")

        await self.repository.clear_cart(cart_id)

        cart.subtotal = Decimal("0.00")
        cart.tax = Decimal("0.00")
        cart.discount = Decimal("0.00")
        cart.total = Decimal("0.00")

        return await self.repository.update_cart(cart)

    # ==========================================
    # Recalculate Cart
    # ==========================================

    async def recalculate_cart(
        self,
        cart_id: UUID,
    ):

        cart = await self.repository.get_cart_by_id(cart_id)

        if not cart:
            raise ValueError("Cart not found")

        subtotal = Decimal("0.00")

        for item in cart.items:
            subtotal += Decimal(item.total_price)

        cart.subtotal = subtotal

        cart.tax = subtotal * Decimal("0.10")

        cart.total = (
            cart.subtotal
            + cart.tax
            - cart.discount
        )

        await self.repository.update_cart(cart)

        return await self.repository.get_cart_by_id(cart_id)
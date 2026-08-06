from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CartStatus, KOTStatus, OrderStatus
from app.models.kot import KOT
from app.models.order import Order
from app.models.order_item import OrderItem
from app.repositories.cart_repository import CartRepository
from app.repositories.kot_repository import KOTRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.order import CreateOrderRequest, UpdateOrderStatusRequest
from app.utils.kot_number import generate_kot_number
from app.utils.order_number import generate_order_number


class OrderService:

    def __init__(
        self,
        db: AsyncSession,
        cart_repository: CartRepository,
        order_repository: OrderRepository,
        kot_repository: KOTRepository | None = None,
    ):
        self.db = db
        self.cart_repository = cart_repository
        self.order_repository = order_repository
        self.kot_repository = kot_repository or KOTRepository(db)

    # ==========================================
    # Create Order
    # ==========================================

    async def create_order(self, request: CreateOrderRequest):

        cart = await self.cart_repository.get_cart_by_id(request.cart_id)

        if cart is None:
            raise ValueError("Cart not found.")

        if cart.status == CartStatus.CHECKED_OUT:
            raise ValueError("Cart already checked out.")

        if cart.status == CartStatus.CANCELLED:
            raise ValueError("Cart is cancelled.")

        if len(cart.items) == 0:
            raise ValueError("Cart is empty.")

        while True:
            order_number = generate_order_number()
            existing_order = await self.order_repository.get_order_by_number(order_number)
            if existing_order is None:
                break

        order = Order(
            order_number=order_number,
            cart_id=cart.id,
            customer_id=cart.customer_id,
            table_number=cart.table_number,
            order_type=cart.order_type,
            status=OrderStatus.PENDING,
            subtotal=cart.subtotal,
            tax=cart.tax,
            discount=cart.discount,
            total=cart.total,
        )

        order = await self.order_repository.create_order(order)

        for item in cart.items:

            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                special_instructions=item.special_instructions,
            )

            await self.order_repository.create_order_item(order_item)

        kot = KOT(
            kot_number=generate_kot_number(),
            order_id=order.id,
            status=KOTStatus.PENDING,
        )
        created_kot = await self.kot_repository.create_kot(kot)
        order.kot = created_kot
        created_kot.order = order

        cart.status = CartStatus.CHECKED_OUT

        await self.cart_repository.update_cart(cart)

        await self.db.commit()

        return await self.order_repository.get_order_by_id(order.id)

    # ==========================================
    # Get Order
    # ==========================================

    async def get_order(self, order_id: UUID):

        order = await self.order_repository.get_order_by_id(order_id)

        if order is None:
            raise ValueError("Order not found.")

        return order

    # ==========================================
    # Get All Orders
    # ==========================================

    async def get_all_orders(self):

        return await self.order_repository.get_all_orders()

    # ==========================================
    # Update Order Status
    # ==========================================

    async def update_order_status(
        self,
        order_id: UUID,
        request: UpdateOrderStatusRequest,
    ):

        order = await self.order_repository.get_order_by_id(order_id)

        if order is None:
            raise ValueError("Order not found.")

        order.status = request.status

        await self.order_repository.update_order(order)

        await self.db.commit()

        return order

    # ==========================================
    # Cancel Order
    # ==========================================

    async def cancel_order(self, order_id: UUID):

        order = await self.order_repository.get_order_by_id(order_id)

        if order is None:
            raise ValueError("Order not found.")

        order.status = OrderStatus.CANCELLED

        await self.order_repository.update_order(order)

        await self.db.commit()

        return order
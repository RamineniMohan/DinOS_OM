import asyncio
from decimal import Decimal
from uuid import uuid4
from unittest import TestCase

from app.core.enums import CartStatus
from app.schemas.order import CreateOrderRequest
from app.services.order_service import OrderService
from app.utils.order_number import generate_order_number


class DummyDB:
    async def commit(self):
        return None

    def add(self, item):
        return None


class DummyCartRepository:
    def __init__(self, cart):
        self.cart = cart
        self.updated_cart = None

    async def get_cart_by_id(self, cart_id):
        return self.cart

    async def update_cart(self, cart):
        self.updated_cart = cart


class DummyOrderRepository:
    def __init__(self):
        self.created_items = []
        self.created_order = None

    async def get_order_by_number(self, order_number):
        return None

    async def create_order(self, order):
        self.created_order = order
        order.id = uuid4()
        return order

    async def create_order_item(self, order_item):
        self.created_items.append(order_item)
        return order_item

    async def get_order_by_id(self, order_id):
        return self.created_order

    async def get_all_orders(self):
        return []

    async def update_order(self, order):
        return order


class DummyKOTRepository:
    def __init__(self):
        self.created_kot = None

    async def create_kot(self, kot):
        self.created_kot = kot
        kot.id = uuid4()
        return kot


class TestOrderService(TestCase):
    def test_generate_order_number_is_unique_per_day(self):
        first = generate_order_number()
        second = generate_order_number()

        self.assertNotEqual(first, second)

    def test_create_order_persists_special_instructions_and_creates_kot(self):
        async def run_test():
            cart = type(
                "Cart",
                (),
                {
                    "id": uuid4(),
                    "customer_id": uuid4(),
                    "table_number": "5",
                    "order_type": "dine_in",
                    "status": CartStatus.ACTIVE,
                    "subtotal": Decimal("10.00"),
                    "tax": Decimal("1.00"),
                    "discount": Decimal("0.00"),
                    "total": Decimal("11.00"),
                    "items": [
                        type(
                            "CartItem",
                            (),
                            {
                                "menu_item_id": uuid4(),
                                "item_name": "Burger",
                                "quantity": 2,
                                "unit_price": Decimal("5.00"),
                                "total_price": Decimal("10.00"),
                                "special_instructions": "Extra sauce",
                            },
                        )()
                    ],
                },
            )()

            service = OrderService(
                db=DummyDB(),
                cart_repository=DummyCartRepository(cart),
                order_repository=DummyOrderRepository(),
                kot_repository=DummyKOTRepository(),
            )

            request = CreateOrderRequest(cart_id=cart.id)

            await service.create_order(request)

            self.assertEqual(
                service.order_repository.created_items[0].special_instructions,
                "Extra sauce",
            )
            self.assertIsNotNone(service.kot_repository.created_kot)
            self.assertEqual(
                service.kot_repository.created_kot.order_id,
                service.order_repository.created_order.id,
            )

        asyncio.run(run_test())

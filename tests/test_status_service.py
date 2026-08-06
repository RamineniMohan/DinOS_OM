from uuid import uuid4
from unittest import TestCase

from app.core.enums import OrderStatus
from app.services.status_service import StatusService


class DummyOrderRepository:
    def __init__(self, order):
        self.order = order
        self.updated_order = None

    async def get_order_by_id(self, order_id):
        return self.order

    async def update_order(self, order):
        self.updated_order = order
        return order


class TestStatusService(TestCase):
    def test_ready_to_completed_transition_is_allowed(self):
        order = type("Order", (), {"status": OrderStatus.READY, "id": uuid4()})()
        repository = DummyOrderRepository(order)
        service = StatusService(repository)

        updated = __import__("asyncio").run(
            service.update_status(order.id, OrderStatus.COMPLETED)
        )

        self.assertEqual(updated.status, OrderStatus.COMPLETED)

    def test_pending_to_preparing_is_allowed(self):
        order = type("Order", (), {"status": OrderStatus.PENDING, "id": uuid4()})()
        repository = DummyOrderRepository(order)
        service = StatusService(repository)

        updated = __import__("asyncio").run(
            service.update_status(order.id, OrderStatus.PREPARING)
        )

        self.assertEqual(updated.status, OrderStatus.PREPARING)

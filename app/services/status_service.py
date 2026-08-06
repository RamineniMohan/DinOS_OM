from uuid import UUID

from app.core.enums import OrderStatus
from app.repositories.order_repository import OrderRepository


class StatusService:

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    async def get_status(self, order_id: UUID):

        order = await self.repository.get_order_by_id(order_id)

        if not order:
            raise ValueError("Order not found")

        return order

    async def update_status(
        self,
        order_id: UUID,
        status: OrderStatus,
    ):

        order = await self.repository.get_order_by_id(order_id)

        if not order:
            raise ValueError("Order not found")

        if status == order.status:
            return order

        if status not in OrderStatus:
            raise ValueError("Invalid status value")

        order.status = status

        return await self.repository.update_order(order)
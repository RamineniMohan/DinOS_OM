from app.core.enums import OrderStatus
from app.repositories.order_repository import OrderRepository


class HistoryService:

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    async def get_history(self):
        return await self.repository.get_all_orders()

    async def completed_orders(self):
        return await self.repository.get_orders_by_status(
            OrderStatus.COMPLETED
        )

    async def cancelled_orders(self):
        return await self.repository.get_orders_by_status(
            OrderStatus.CANCELLED
        )
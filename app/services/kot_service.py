from uuid import UUID

from app.core.enums import KOTStatus
from app.models.kot import KOT
from app.repositories.kot_repository import KOTRepository
from app.schemas.kot import UpdateKOTStatusRequest
from app.utils.kot_number import generate_kot_number


class KOTService:

    def __init__(self, repository: KOTRepository):
        self.repository = repository

    async def create_kot(self, order_id: UUID):

        existing = await self.repository.get_by_order(order_id)

        if existing:
            return existing

        kot = KOT(
            kot_number=generate_kot_number(),
            order_id=order_id,
            status=KOTStatus.PENDING,
        )

        return await self.repository.create_kot(kot)

    async def get_kot(self, kot_id: UUID):

        kot = await self.repository.get_kot(kot_id)

        if not kot:
            raise ValueError("KOT not found")

        return kot

    async def get_all(self):
        return await self.repository.get_all()

    async def update_status(
        self,
        kot_id: UUID,
        request: UpdateKOTStatusRequest,
    ):

        kot = await self.repository.get_kot(kot_id)

        if not kot:
            raise ValueError("KOT not found")

        kot.status = request.status

        return await self.repository.update(kot)
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.kot import KOT


class KOTRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_kot(self, kot: KOT):
        self.db.add(kot)
        await self.db.flush()
        await self.db.refresh(kot)
        return kot

    async def get_kot(self, kot_id: UUID):

        result = await self.db.execute(
            select(KOT)
            .options(selectinload(KOT.order))
            .where(KOT.id == kot_id)
        )

        return result.scalar_one_or_none()

    async def get_by_order(self, order_id: UUID):

        result = await self.db.execute(
            select(KOT)
            .where(KOT.order_id == order_id)
        )

        return result.scalar_one_or_none()

    async def get_all(self):

        result = await self.db.execute(
            select(KOT)
            .options(selectinload(KOT.order))
            .order_by(KOT.created_at.desc())
        )

        return result.scalars().all()

    async def update(self, kot: KOT):
        await self.db.flush()
        await self.db.refresh(kot)
        return kot
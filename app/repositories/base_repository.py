from typing import Generic, Type, TypeVar
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository with common CRUD operations.
    """


    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession,
    ):
        self.model = model
        self.db = db

    # ==========================================
    # Create
    # ==========================================

    async def create(
        self,
        obj: ModelType,
    ) -> ModelType:

        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)

        return obj

    # ==========================================
    # Get By ID
    # ==========================================

    async def get_by_id(
        self,
        obj_id: UUID,
    ) -> ModelType | None:

        result = await self.db.execute(
            select(self.model).where(
                self.model.id == obj_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================
    # Get All
    # ==========================================

    async def get_all(self):

        result = await self.db.execute(
            select(self.model)
        )

        return result.scalars().all()

    # ==========================================
    # Update
    # ==========================================

    async def update(
        self,
        obj: ModelType,
    ) -> ModelType:

        await self.db.flush()
        await self.db.refresh(obj)

        return obj

    # ==========================================
    # Delete
    # ==========================================

    async def delete(
        self,
        obj: ModelType,
    ):

        await self.db.delete(obj)
        await self.db.flush()
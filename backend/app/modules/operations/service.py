import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.operations.models import DiningTable, Floor, TableSection, Tip, TipAllocation
from app.modules.operations.schemas import (
    DiningTableCreate,
    DiningTableUpdate,
    FloorCreate,
    TableSectionCreate,
    TipCreate,
)


class OperationsService:

    @staticmethod
    async def create_floor(db: AsyncSession, restaurant_id: uuid.UUID, schema: FloorCreate) -> Floor:
        floor = Floor(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(floor)
        await db.commit()
        await db.refresh(floor)
        return floor

    @staticmethod
    async def list_floors(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Floor]:
        result = await db.execute(
            select(Floor)
            .where(Floor.restaurant_id == restaurant_id)
            .order_by(Floor.sort_order, Floor.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_section(db: AsyncSession, restaurant_id: uuid.UUID, schema: TableSectionCreate) -> TableSection:
        # Verify floor exists
        floor_ex = await db.execute(select(Floor).where(Floor.id == schema.floor_id))
        floor = floor_ex.scalar_one_or_none()
        if not floor or floor.restaurant_id != restaurant_id:
            raise NotFoundError("Floor not found")

        section = TableSection(**schema.model_dump())
        db.add(section)
        await db.commit()
        await db.refresh(section)
        return section

    @staticmethod
    async def list_sections(db: AsyncSession, floor_id: uuid.UUID, restaurant_id: uuid.UUID) -> list[TableSection]:
        result = await db.execute(
            select(TableSection)
            .join(Floor, TableSection.floor_id == Floor.id)
            .where(TableSection.floor_id == floor_id, Floor.restaurant_id == restaurant_id)
            .order_by(TableSection.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_table(db: AsyncSession, restaurant_id: uuid.UUID, schema: DiningTableCreate) -> DiningTable:
        # Verify section if specified
        if schema.section_id:
            sec_ex = await db.execute(
                select(TableSection)
                .join(Floor, TableSection.floor_id == Floor.id)
                .where(TableSection.id == schema.section_id, Floor.restaurant_id == restaurant_id)
            )
            if not sec_ex.scalar_one_or_none():
                raise NotFoundError("Table section not found")

        table = DiningTable(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(table)
        await db.commit()
        await db.refresh(table)
        return table

    @staticmethod
    async def list_tables(db: AsyncSession, restaurant_id: uuid.UUID, section_id: uuid.UUID | None = None) -> list[DiningTable]:
        q = select(DiningTable).where(DiningTable.restaurant_id == restaurant_id, DiningTable.is_active)
        if section_id:
            q = q.where(DiningTable.section_id == section_id)
        result = await db.execute(q.order_by(DiningTable.table_number))
        return list(result.scalars().all())

    @staticmethod
    async def update_table(db: AsyncSession, table_id: uuid.UUID, restaurant_id: uuid.UUID, schema: DiningTableUpdate) -> DiningTable:
        result = await db.execute(select(DiningTable).where(DiningTable.id == table_id, DiningTable.restaurant_id == restaurant_id))
        table = result.scalar_one_or_none()
        if not table:
            raise NotFoundError("Table not found")
        for k, v in schema.model_dump(exclude_unset=True).items():
            setattr(table, k, v)
        await db.commit()
        await db.refresh(table)
        return table

    @staticmethod
    async def create_tip(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: TipCreate
    ) -> Tip:
        # Check if tip already exists for this order
        ex = await db.execute(select(Tip).where(Tip.order_id == schema.order_id))
        if ex.scalar_one_or_none():
            raise ConflictError("Tip has already been registered for this order")

        tip = Tip(
            restaurant_id=restaurant_id,
            order_id=schema.order_id,
            amount=schema.amount,
            tip_type=schema.tip_type,
            percentage=schema.percentage,
        )
        db.add(tip)
        await db.flush()

        for alloc in schema.allocations:
            db.add(TipAllocation(
                tip_id=tip.id,
                staff_id=alloc.staff_id,
                amount=alloc.amount,
                percentage_share=alloc.percentage_share,
            ))

        await db.commit()
        return await OperationsService.get_tip(db, tip.id)

    @staticmethod
    async def get_tip(db: AsyncSession, tip_id: uuid.UUID) -> Tip:
        result = await db.execute(
            select(Tip)
            .options(selectinload(Tip.allocations))
            .where(Tip.id == tip_id)
        )
        tip = result.scalar_one_or_none()
        if not tip:
            raise NotFoundError("Tip not found")
        return tip

    @staticmethod
    async def list_tips(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Tip]:
        result = await db.execute(
            select(Tip)
            .options(selectinload(Tip.allocations))
            .where(Tip.restaurant_id == restaurant_id)
            .order_by(Tip.created_at.desc())
        )
        return list(result.scalars().all())

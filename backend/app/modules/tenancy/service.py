import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.tenancy.models import Branch, Restaurant, RestaurantSettings
from app.modules.tenancy.schemas import (
    BranchCreate,
    BranchUpdate,
    RestaurantCreate,
    RestaurantSettingsUpdate,
    RestaurantUpdate,
)


class TenancyService:

    @staticmethod
    async def create_restaurant(db: AsyncSession, schema: RestaurantCreate, owner_id: uuid.UUID) -> Restaurant:
        # Check slug uniqueness
        existing = await db.execute(select(Restaurant).where(Restaurant.slug == schema.slug))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Restaurant slug '{schema.slug}' already exists")

        restaurant = Restaurant(
            name=schema.name,
            slug=schema.slug,
        )
        db.add(restaurant)
        await db.flush()

        from app.modules.auth.models import User
        result = await db.execute(select(User).where(User.id == owner_id))
        user = result.scalar_one_or_none()
        if user:
            user.restaurant_id = restaurant.id

        # Create default settings
        settings = RestaurantSettings(restaurant_id=restaurant.id)
        db.add(settings)

        # Create default branch
        branch = Branch(
            restaurant_id=restaurant.id,
            name=f"{schema.name} — Main Branch",
        )
        db.add(branch)

        await db.commit()
        return await TenancyService.get_restaurant(db, restaurant.id)

    @staticmethod
    async def get_restaurant(db: AsyncSession, restaurant_id: uuid.UUID) -> Restaurant:
        result = await db.execute(
            select(Restaurant)
            .options(
                selectinload(Restaurant.settings),
                selectinload(Restaurant.branches),
            )
            .where(Restaurant.id == restaurant_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundError("Restaurant not found")
        return r

    @staticmethod
    async def list_restaurants(db: AsyncSession) -> list[Restaurant]:
        result = await db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.settings), selectinload(Restaurant.branches))
            .order_by(Restaurant.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_restaurant(db: AsyncSession, restaurant_id: uuid.UUID, schema: RestaurantUpdate) -> Restaurant:
        r = await TenancyService.get_restaurant(db, restaurant_id)
        for field, value in schema.model_dump(exclude_unset=True).items():
            setattr(r, field, value)
        await db.commit()
        return await TenancyService.get_restaurant(db, restaurant_id)

    @staticmethod
    async def create_branch(db: AsyncSession, restaurant_id: uuid.UUID, schema: BranchCreate) -> Branch:
        data = schema.model_dump()
        valid_keys = {"name", "address", "phone", "is_active", "is_default"}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        branch = Branch(restaurant_id=restaurant_id, **filtered_data)
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        return branch

    @staticmethod
    async def list_branches(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Branch]:
        result = await db.execute(
            select(Branch).where(Branch.restaurant_id == restaurant_id).order_by(Branch.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_branch(db: AsyncSession, branch_id: uuid.UUID, schema: BranchUpdate) -> Branch:
        result = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = result.scalar_one_or_none()
        if not branch:
            raise NotFoundError("Branch not found")
        data = schema.model_dump(exclude_unset=True)
        valid_keys = {"name", "address", "phone", "is_active", "is_default"}
        for field, value in data.items():
            if field in valid_keys:
                setattr(branch, field, value)
        await db.commit()
        await db.refresh(branch)
        return branch

    @staticmethod
    async def get_or_create_settings(db: AsyncSession, restaurant_id: uuid.UUID) -> RestaurantSettings:
        result = await db.execute(
            select(RestaurantSettings).where(RestaurantSettings.restaurant_id == restaurant_id)
        )
        s = result.scalar_one_or_none()
        if not s:
            s = RestaurantSettings(restaurant_id=restaurant_id)
            db.add(s)
            await db.commit()
            await db.refresh(s)
        return s

    @staticmethod
    async def update_settings(db: AsyncSession, restaurant_id: uuid.UUID, schema: RestaurantSettingsUpdate) -> RestaurantSettings:
        s = await TenancyService.get_or_create_settings(db, restaurant_id)
        for field, value in schema.model_dump(exclude_unset=True).items():
            setattr(s, field, value)
        await db.commit()
        await db.refresh(s)
        return s

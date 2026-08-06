import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import NotFoundError
from app.modules.menu.models import (
    ItemAddon,
    ItemVariant,
    MenuCategory,
    MenuCombo,
    MenuComboItem,
    MenuItem,
    MenuItemBranchPrice,
)
from app.modules.menu.schemas import (
    AvailabilityToggle,
    ComboCreate,
    ComboUpdate,
    ItemAddonCreate,
    ItemVariantCreate,
    MenuCategoryCreate,
    MenuCategoryUpdate,
    MenuItemBranchPriceCreate,
    MenuItemCreate,
    MenuItemUpdate,
)


class MenuService:

    @staticmethod
    async def _load_category(
        db: AsyncSession,
        category_id: uuid.UUID,
        restaurant_id: uuid.UUID | None = None,
    ) -> MenuCategory:
        q = (
            select(MenuCategory)
            .options(
                selectinload(MenuCategory.items).selectinload(MenuItem.variants),
                selectinload(MenuCategory.items).selectinload(MenuItem.addons),
            )
            .where(MenuCategory.id == category_id)
        )
        if restaurant_id is not None:
            q = q.where(MenuCategory.restaurant_id == restaurant_id)
        result = await db.execute(q)
        cat = result.scalar_one_or_none()
        if not cat:
            raise NotFoundError("Menu category not found")
        return cat

    @staticmethod
    async def create_category(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: MenuCategoryCreate
    ) -> MenuCategory:
        cat = MenuCategory(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(cat)
        await db.commit()
        return await MenuService._load_category(db, cat.id, restaurant_id)

    @staticmethod
    async def list_categories(db: AsyncSession, restaurant_id: uuid.UUID) -> list[MenuCategory]:
        result = await db.execute(
            select(MenuCategory)
            .options(
                selectinload(MenuCategory.items).selectinload(MenuItem.variants),
                selectinload(MenuCategory.items).selectinload(MenuItem.addons),
            )
            .where(MenuCategory.restaurant_id == restaurant_id)
            .order_by(MenuCategory.sort_order, MenuCategory.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_category(
        db: AsyncSession,
        category_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        schema: MenuCategoryUpdate,
    ) -> MenuCategory:
        cat = await MenuService._load_category(db, category_id, restaurant_id)
        for k, v in schema.model_dump(exclude_unset=True).items():
            setattr(cat, k, v)
        await db.commit()
        return await MenuService._load_category(db, category_id, restaurant_id)

    @staticmethod
    async def delete_category(
        db: AsyncSession, category_id: uuid.UUID, restaurant_id: uuid.UUID
    ) -> None:
        cat = await MenuService._load_category(db, category_id, restaurant_id)
        await db.delete(cat)
        await db.commit()

    @staticmethod
    async def _load_item(
        db: AsyncSession,
        item_id: uuid.UUID,
        restaurant_id: uuid.UUID | None = None,
    ) -> MenuItem:
        q = (
            select(MenuItem)
            .options(selectinload(MenuItem.variants), selectinload(MenuItem.addons))
            .where(MenuItem.id == item_id)
        )
        if restaurant_id is not None:
            q = q.where(MenuItem.restaurant_id == restaurant_id)
        result = await db.execute(q)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Menu item not found")
        return item

    @staticmethod
    async def upload_item_image(
        db: AsyncSession, item_id: uuid.UUID, restaurant_id: uuid.UUID, image_url: str
    ) -> MenuItem:
        item = await MenuService._load_item(db, item_id, restaurant_id)
        item.image_url = image_url
        await db.commit()
        return await MenuService._load_item(db, item_id, restaurant_id)

    @staticmethod
    async def create_item(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: MenuItemCreate
    ) -> MenuItem:
        variants_data = schema.variants
        addons_data = schema.addons
        item_data = schema.model_dump(exclude={'variants', 'addons'})
        item = MenuItem(restaurant_id=restaurant_id, **item_data)
        db.add(item)
        await db.flush()

        for v in variants_data:
            db.add(ItemVariant(item_id=item.id, **v.model_dump()))
        for a in addons_data:
            db.add(ItemAddon(item_id=item.id, **a.model_dump()))

        await db.commit()
        return await MenuService._load_item(db, item.id, restaurant_id)

    @staticmethod
    async def list_items(
        db: AsyncSession, restaurant_id: uuid.UUID, category_id: uuid.UUID = None
    ) -> list[MenuItem]:
        q = (
            select(MenuItem)
            .options(selectinload(MenuItem.variants), selectinload(MenuItem.addons))
            .where(MenuItem.restaurant_id == restaurant_id)
        )
        if category_id:
            q = q.where(MenuItem.category_id == category_id)
        result = await db.execute(q.order_by(MenuItem.sort_order, MenuItem.name))
        return list(result.scalars().all())

    @staticmethod
    async def update_item(
        db: AsyncSession,
        item_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        schema: MenuItemUpdate,
    ) -> MenuItem:
        item = await MenuService._load_item(db, item_id, restaurant_id)
        for k, v in schema.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await db.commit()
        return await MenuService._load_item(db, item_id, restaurant_id)

    @staticmethod
    async def delete_item(
        db: AsyncSession, item_id: uuid.UUID, restaurant_id: uuid.UUID
    ) -> None:
        item = await MenuService._load_item(db, item_id, restaurant_id)
        await db.delete(item)
        await db.commit()

    @staticmethod
    async def toggle_availability(
        db: AsyncSession,
        item_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        toggle: AvailabilityToggle,
    ) -> MenuItem:
        item = await MenuService._load_item(db, item_id, restaurant_id)
        item.is_available = toggle.is_available
        await db.commit()
        return await MenuService._load_item(db, item_id, restaurant_id)

    @staticmethod
    async def add_variant(
        db: AsyncSession,
        item_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        schema: ItemVariantCreate,
    ) -> MenuItem:
        await MenuService._load_item(db, item_id, restaurant_id)
        db.add(ItemVariant(item_id=item_id, **schema.model_dump()))
        await db.commit()
        return await MenuService._load_item(db, item_id, restaurant_id)

    @staticmethod
    async def add_addon(
        db: AsyncSession,
        item_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        schema: ItemAddonCreate,
    ) -> MenuItem:
        await MenuService._load_item(db, item_id, restaurant_id)
        db.add(ItemAddon(item_id=item_id, **schema.model_dump()))
        await db.commit()
        return await MenuService._load_item(db, item_id, restaurant_id)

    @staticmethod
    async def set_branch_price(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        schema: MenuItemBranchPriceCreate,
    ) -> MenuItemBranchPrice:
        from app.common.exceptions import NotFoundError
        from app.modules.tenancy.models import Branch

        # Verify the menu item belongs to this restaurant
        await MenuService._load_item(db, schema.menu_item_id, restaurant_id)

        # Verify the branch belongs to this restaurant
        branch_result = await db.execute(
            select(Branch).where(
                Branch.id == schema.branch_id,
                Branch.restaurant_id == restaurant_id,
            )
        )
        if not branch_result.scalar_one_or_none():
            raise NotFoundError("Branch not found or does not belong to this restaurant")

        result = await db.execute(
            select(MenuItemBranchPrice).where(
                MenuItemBranchPrice.menu_item_id == schema.menu_item_id,
                MenuItemBranchPrice.branch_id == schema.branch_id,
            )
        )
        bp = result.scalar_one_or_none()
        if bp:
            bp.price = schema.price
        else:
            bp = MenuItemBranchPrice(**schema.model_dump())
            db.add(bp)
        await db.commit()

        result = await db.execute(
            select(MenuItemBranchPrice).where(MenuItemBranchPrice.id == bp.id)
        )
        return result.scalar_one()

    @staticmethod
    async def get_branch_prices(
        db: AsyncSession, branch_id: uuid.UUID, restaurant_id: uuid.UUID
    ) -> list[MenuItemBranchPrice]:
        # Join through MenuItem to enforce restaurant isolation
        result = await db.execute(
            select(MenuItemBranchPrice)
            .join(MenuItem, MenuItemBranchPrice.menu_item_id == MenuItem.id)
            .where(
                MenuItemBranchPrice.branch_id == branch_id,
                MenuItem.restaurant_id == restaurant_id,
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def _load_combo(
        db: AsyncSession,
        combo_id: uuid.UUID,
        restaurant_id: uuid.UUID | None = None,
    ) -> MenuCombo:
        q = select(MenuCombo).options(selectinload(MenuCombo.items)).where(MenuCombo.id == combo_id)
        if restaurant_id is not None:
            q = q.where(MenuCombo.restaurant_id == restaurant_id)
        result = await db.execute(q)
        combo = result.scalar_one_or_none()
        if not combo:
            raise NotFoundError("Menu combo not found")
        return combo

    @staticmethod
    async def create_combo(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: ComboCreate
    ) -> MenuCombo:
        items_data = schema.items
        combo_data = schema.model_dump(exclude={'items'})
        combo = MenuCombo(restaurant_id=restaurant_id, **combo_data)
        db.add(combo)
        await db.flush()

        for item in items_data:
            db.add(MenuComboItem(combo_id=combo.id, **item.model_dump()))

        await db.commit()
        return await MenuService._load_combo(db, combo.id, restaurant_id)

    @staticmethod
    async def list_combos(db: AsyncSession, restaurant_id: uuid.UUID) -> list[MenuCombo]:
        result = await db.execute(
            select(MenuCombo)
            .options(selectinload(MenuCombo.items))
            .where(MenuCombo.restaurant_id == restaurant_id)
            .order_by(MenuCombo.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_combo(
        db: AsyncSession,
        combo_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        schema: ComboUpdate,
    ) -> MenuCombo:
        combo = await MenuService._load_combo(db, combo_id, restaurant_id)

        update_data = schema.model_dump(exclude_unset=True, exclude={'items'})
        for k, v in update_data.items():
            setattr(combo, k, v)

        if schema.items is not None:
            # Recreate combo items
            await db.execute(
                MenuComboItem.__table__.delete().where(MenuComboItem.combo_id == combo.id)
            )
            for item in schema.items:
                db.add(MenuComboItem(combo_id=combo.id, **item.model_dump()))

        await db.commit()
        return await MenuService._load_combo(db, combo.id, restaurant_id)

    @staticmethod
    async def delete_combo(
        db: AsyncSession, combo_id: uuid.UUID, restaurant_id: uuid.UUID
    ) -> None:
        combo = await MenuService._load_combo(db, combo_id, restaurant_id)
        await db.delete(combo)
        await db.commit()

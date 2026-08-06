import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.inventory.models import (
    Ingredient,
    PurchaseOrder,
    PurchaseOrderItem,
    Recipe,
    RecipeIngredient,
    StockLedger,
    Unit,
    Vendor,
)
from app.modules.inventory.schemas import (
    IngredientCreate,
    IngredientUpdate,
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    RecipeCreate,
    StockAdjustment,
    UnitCreate,
    VendorCreate,
    VendorUpdate,
)


class InventoryService:

    @staticmethod
    async def create_unit(db: AsyncSession, restaurant_id: uuid.UUID, schema: UnitCreate) -> Unit:
        # Check if unit name already exists
        existing = await db.execute(select(Unit).where(Unit.name == schema.name, Unit.restaurant_id == restaurant_id))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Unit name '{schema.name}' already exists")
        unit = Unit(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(unit)
        await db.commit()
        await db.refresh(unit)
        return unit

    @staticmethod
    async def list_units(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Unit]:
        result = await db.execute(select(Unit).where(Unit.restaurant_id == restaurant_id).order_by(Unit.name))
        return list(result.scalars().all())

    @staticmethod
    async def create_ingredient(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: IngredientCreate
    ) -> Ingredient:
        # Verify unit exists
        unit_result = await db.execute(
            select(Unit).where(Unit.id == schema.unit_id, Unit.restaurant_id == restaurant_id)
        )
        if not unit_result.scalar_one_or_none():
            raise NotFoundError("Unit not found")

        ingredient = Ingredient(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(ingredient)
        await db.commit()
        await db.refresh(ingredient)
        return ingredient

    @staticmethod
    async def list_ingredients(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Ingredient]:
        result = await db.execute(
            select(Ingredient)
            .options(joinedload(Ingredient.unit))
            .where(Ingredient.restaurant_id == restaurant_id)
            .order_by(Ingredient.name)
        )
        return list(result.scalars().unique().all())

    @staticmethod
    async def get_ingredient(db: AsyncSession, ingredient_id: uuid.UUID, restaurant_id: uuid.UUID) -> Ingredient:
        result = await db.execute(
            select(Ingredient)
            .options(selectinload(Ingredient.unit))
            .where(Ingredient.id == ingredient_id, Ingredient.restaurant_id == restaurant_id)
        )
        ing = result.scalar_one_or_none()
        if not ing:
            raise NotFoundError("Ingredient not found")
        return ing

    @staticmethod
    async def update_ingredient(
        db: AsyncSession, ingredient_id: uuid.UUID, restaurant_id: uuid.UUID, schema: IngredientUpdate
    ) -> Ingredient:
        result = await db.execute(
            select(Ingredient)
            .options(selectinload(Ingredient.unit))
            .where(Ingredient.id == ingredient_id, Ingredient.restaurant_id == restaurant_id)
        )
        ing = result.scalar_one_or_none()
        if not ing:
            raise NotFoundError("Ingredient not found")
        for k, v in schema.model_dump(exclude_unset=True).items():
            setattr(ing, k, v)
        await db.commit()
        await db.refresh(ing)
        return ing

    @staticmethod
    async def adjust_stock(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: StockAdjustment, user_id: uuid.UUID
    ) -> StockLedger:
        result = await db.execute(
            select(Ingredient).where(
                Ingredient.id == schema.ingredient_id,
                Ingredient.restaurant_id == restaurant_id,
            )
        )
        ing = result.scalar_one_or_none()
        if not ing:
            raise NotFoundError("Ingredient not found")

        qty_before = ing.current_stock
        qty_after = qty_before + schema.quantity_change
        if qty_after < 0:
            from app.common.exceptions import ConflictError
            raise ConflictError(
                f"Cannot reduce stock below 0 for '{ing.name}' "
                f"(current: {qty_before}, change: {schema.quantity_change})"
            )
        ing.current_stock = qty_after

        ledger = StockLedger(
            restaurant_id=restaurant_id,
            ingredient_id=schema.ingredient_id,
            quantity_change=schema.quantity_change,
            quantity_before=qty_before,
            quantity_after=qty_after,
            reason=schema.reason,
            reference_type=schema.reference_type,
            reference_id=schema.reference_id,
            created_by=user_id,
        )
        db.add(ledger)
        await db.commit()

        # Load relationships for response schema if needed
        result_ledger = await db.execute(
            select(StockLedger)
            .options(selectinload(StockLedger.ingredient))
            .where(StockLedger.id == ledger.id)
        )
        return result_ledger.scalar_one()

    @staticmethod
    async def list_stock_ledger(
        db: AsyncSession, restaurant_id: uuid.UUID, ingredient_id: uuid.UUID | None = None
    ) -> list[StockLedger]:
        q = select(StockLedger).where(StockLedger.restaurant_id == restaurant_id)
        if ingredient_id:
            q = q.where(StockLedger.ingredient_id == ingredient_id)
        result = await db.execute(q.order_by(StockLedger.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def create_recipe(
        db: AsyncSession, restaurant_id: uuid.UUID, schema: RecipeCreate
    ) -> Recipe:
        from app.modules.menu.models import MenuItem

        # Verify menu item belongs to the restaurant
        menu_item_ex = await db.execute(
            select(MenuItem).where(MenuItem.id == schema.menu_item_id, MenuItem.restaurant_id == restaurant_id)
        )
        if not menu_item_ex.scalar_one_or_none():
            raise NotFoundError("Menu item not found")

        # Check if recipe already exists for this menu item in this restaurant
        existing = await db.execute(select(Recipe).where(
            Recipe.menu_item_id == schema.menu_item_id,
            Recipe.restaurant_id == restaurant_id,
        ))
        if existing.scalar_one_or_none():
            raise ConflictError("Recipe already exists for this menu item")

        recipe = Recipe(
            restaurant_id=restaurant_id,
            menu_item_id=schema.menu_item_id,
            name=schema.name,
            yield_quantity=schema.yield_quantity,
        )
        db.add(recipe)
        await db.flush()

        for ri in schema.ingredients:
            # Verify ingredient & unit exists
            ing_ex = await db.execute(
                select(Ingredient).where(Ingredient.id == ri.ingredient_id, Ingredient.restaurant_id == restaurant_id)
            )
            if not ing_ex.scalar_one_or_none():
                raise NotFoundError(f"Ingredient {ri.ingredient_id} not found")
            unit_ex = await db.execute(
                select(Unit).where(Unit.id == ri.unit_id, Unit.restaurant_id == restaurant_id)
            )
            if not unit_ex.scalar_one_or_none():
                raise NotFoundError(f"Unit {ri.unit_id} not found")

            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ri.ingredient_id,
                quantity=ri.quantity,
                unit_id=ri.unit_id,
            ))
        await db.commit()
        return await InventoryService.get_recipe(db, recipe.id, restaurant_id)

    @staticmethod
    async def get_recipe(db: AsyncSession, recipe_id: uuid.UUID, restaurant_id: uuid.UUID) -> Recipe:
        result = await db.execute(
            select(Recipe)
            .options(selectinload(Recipe.ingredients))
            .where(Recipe.id == recipe_id, Recipe.restaurant_id == restaurant_id)
        )
        recipe = result.scalar_one_or_none()
        if not recipe:
            raise NotFoundError("Recipe not found")
        return recipe

    @staticmethod
    async def list_recipes(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Recipe]:
        result = await db.execute(
            select(Recipe)
            .options(selectinload(Recipe.ingredients))
            .where(Recipe.restaurant_id == restaurant_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_vendor(db: AsyncSession, restaurant_id: uuid.UUID, schema: VendorCreate) -> Vendor:
        vendor = Vendor(restaurant_id=restaurant_id, **schema.model_dump())
        db.add(vendor)
        await db.commit()
        await db.refresh(vendor)
        return vendor

    @staticmethod
    async def list_vendors(db: AsyncSession, restaurant_id: uuid.UUID) -> list[Vendor]:
        result = await db.execute(select(Vendor).where(Vendor.restaurant_id == restaurant_id).order_by(Vendor.name))
        return list(result.scalars().all())

    @staticmethod
    async def update_vendor(db: AsyncSession, vendor_id: uuid.UUID, restaurant_id: uuid.UUID, schema: VendorUpdate) -> Vendor:
        result = await db.execute(select(Vendor).where(Vendor.id == vendor_id, Vendor.restaurant_id == restaurant_id))
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise NotFoundError('Vendor not found')
        for k, v in schema.model_dump(exclude_unset=True).items():
            setattr(vendor, k, v)
        await db.commit()
        await db.refresh(vendor)
        return vendor

    @staticmethod
    async def create_purchase_order(db: AsyncSession, restaurant_id: uuid.UUID, schema: PurchaseOrderCreate) -> PurchaseOrder:
        # Validate vendor belongs to this tenant
        vendor_check = await db.execute(
            select(Vendor).where(Vendor.id == schema.vendor_id, Vendor.restaurant_id == restaurant_id)
        )
        if not vendor_check.scalar_one_or_none():
            raise NotFoundError("Vendor not found")
        items_data = schema.items
        total = sum(i.quantity * i.unit_price for i in items_data)
        po = PurchaseOrder(restaurant_id=restaurant_id, vendor_id=schema.vendor_id, notes=schema.notes, total_amount=total)
        db.add(po)
        await db.flush()
        for item in items_data:
            db.add(PurchaseOrderItem(order_id=po.id, **item.model_dump()))
        await db.commit()
        result = await db.execute(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po.id))
        return result.scalar_one()

    @staticmethod
    async def list_purchase_orders(db: AsyncSession, restaurant_id: uuid.UUID) -> list[PurchaseOrder]:
        result = await db.execute(
            select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
            .where(PurchaseOrder.restaurant_id == restaurant_id)
            .order_by(PurchaseOrder.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_purchase_order(db: AsyncSession, po_id: uuid.UUID, restaurant_id: uuid.UUID, schema: PurchaseOrderUpdate) -> PurchaseOrder:
        result = await db.execute(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id, PurchaseOrder.restaurant_id == restaurant_id))
        po = result.scalar_one_or_none()
        if not po:
            raise NotFoundError('Purchase order not found')
        for k, v in schema.model_dump(exclude_unset=True).items():
            setattr(po, k, v)
        await db.commit()
        return po

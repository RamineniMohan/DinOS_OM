import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_tenant, get_current_user, require_role
from app.modules.inventory.schemas import (
    IngredientCreate,
    IngredientResponse,
    IngredientUpdate,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    RecipeCreate,
    RecipeResponse,
    StockAdjustment,
    StockLedgerResponse,
    UnitCreate,
    UnitResponse,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    schema: UnitCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.create_unit(db, current_tenant.id, schema)


@router.get("/units", response_model=list[UnitResponse])
async def list_units(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.list_units(db, current_tenant.id)


@router.post("/ingredients", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    schema: IngredientCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.create_ingredient(db, current_tenant.id, schema)


@router.get("/ingredients", response_model=list[IngredientResponse])
async def list_ingredients(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.list_ingredients(db, current_tenant.id)


@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.get_ingredient(db, ingredient_id, current_tenant.id)


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient(
    ingredient_id: uuid.UUID,
    schema: IngredientUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.update_ingredient(db, ingredient_id, current_tenant.id, schema)


@router.post("/stock/adjust", response_model=StockLedgerResponse, status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    schema: StockAdjustment,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Manual stock adjustment (positive = restock, negative = wastage)."""
    return await InventoryService.adjust_stock(db, current_tenant.id, schema, current_user.id)


@router.get("/stock/ledger", response_model=list[StockLedgerResponse])
async def list_stock_ledger(
    ingredient_id: uuid.UUID | None = Query(None),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.list_stock_ledger(db, current_tenant.id, ingredient_id)


@router.post("/recipes", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    schema: RecipeCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.create_recipe(db, current_tenant.id, schema)


@router.get("/recipes", response_model=list[RecipeResponse])
async def list_recipes(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.list_recipes(db, current_tenant.id)


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.get_recipe(db, recipe_id, current_tenant.id)


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    schema: VendorCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.create_vendor(db, current_tenant.id, schema)


@router.get("/vendors", response_model=list[VendorResponse])
async def list_vendors(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.list_vendors(db, current_tenant.id)


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: uuid.UUID,
    schema: VendorUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.update_vendor(db, vendor_id, current_tenant.id, schema)


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    schema: PurchaseOrderCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.create_purchase_order(db, current_tenant.id, schema)


@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse])
async def list_purchase_orders(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.list_purchase_orders(db, current_tenant.id)


@router.patch("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: uuid.UUID,
    schema: PurchaseOrderUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await InventoryService.update_purchase_order(db, po_id, current_tenant.id, schema)

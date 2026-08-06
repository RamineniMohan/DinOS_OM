import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.storage import save_image_upload
from app.core.db import get_db
from app.core.deps import get_current_tenant, get_current_user, require_role
from app.modules.menu.schemas import (
    AvailabilityToggle,
    ComboCreate,
    ComboResponse,
    ComboUpdate,
    ItemAddonCreate,
    ItemVariantCreate,
    MenuCategoryCreate,
    MenuCategoryResponse,
    MenuCategoryUpdate,
    MenuItemBranchPriceCreate,
    MenuItemBranchPriceResponse,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
)
from app.modules.menu.service import MenuService

router = APIRouter(prefix="/menu", tags=["Menu"])


@router.post("/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    schema: MenuCategoryCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.create_category(db, current_tenant.id, schema)


@router.get("/categories", response_model=list[MenuCategoryResponse])
async def list_categories(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.list_categories(db, current_tenant.id)


@router.patch("/categories/{category_id}", response_model=MenuCategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    schema: MenuCategoryUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.update_category(db, category_id, current_tenant.id, schema)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await MenuService.delete_category(db, category_id, current_tenant.id)


@router.post("/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    schema: MenuItemCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.create_item(db, current_tenant.id, schema)


@router.get("/items", response_model=list[MenuItemResponse])
async def list_items(
    category_id: uuid.UUID | None = None,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.list_items(db, current_tenant.id, category_id)


@router.patch("/items/{item_id}", response_model=MenuItemResponse)
async def update_item(
    item_id: uuid.UUID,
    schema: MenuItemUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.update_item(db, item_id, current_tenant.id, schema)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await MenuService.delete_item(db, item_id, current_tenant.id)


@router.post("/items/{item_id}/image", response_model=MenuItemResponse)
async def upload_item_image(
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image for a menu item (Cloudinary or local storage fallback)."""
    image_url = await save_image_upload(file, folder="menu_items")
    return await MenuService.upload_item_image(db, item_id, current_tenant.id, image_url)


@router.patch("/items/{item_id}/availability", response_model=MenuItemResponse)
async def toggle_availability(
    item_id: uuid.UUID,
    toggle: AvailabilityToggle,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.toggle_availability(db, item_id, current_tenant.id, toggle)


@router.post("/items/{item_id}/variants", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def add_variant(
    item_id: uuid.UUID,
    schema: ItemVariantCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.add_variant(db, item_id, current_tenant.id, schema)


@router.post("/items/{item_id}/addons", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def add_addon(
    item_id: uuid.UUID,
    schema: ItemAddonCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.add_addon(db, item_id, current_tenant.id, schema)


@router.post("/branch-prices", response_model=MenuItemBranchPriceResponse, status_code=status.HTTP_201_CREATED)
async def set_branch_price(
    schema: MenuItemBranchPriceCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Set or update menu item price for a specific branch."""
    return await MenuService.set_branch_price(db, current_tenant.id, schema)


@router.get("/branch-prices/{branch_id}", response_model=list[MenuItemBranchPriceResponse])
async def get_branch_prices(
    branch_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all custom branch pricing overrides for a given branch."""
    return await MenuService.get_branch_prices(db, branch_id, current_tenant.id)


@router.post("/combos", response_model=ComboResponse, status_code=status.HTTP_201_CREATED)
async def create_combo(
    schema: ComboCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.create_combo(db, current_tenant.id, schema)


@router.get("/combos", response_model=list[ComboResponse])
async def list_combos(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.list_combos(db, current_tenant.id)


@router.patch("/combos/{combo_id}", response_model=ComboResponse)
async def update_combo(
    combo_id: uuid.UUID,
    schema: ComboUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await MenuService.update_combo(db, combo_id, current_tenant.id, schema)


@router.delete("/combos/{combo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_combo(
    combo_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await MenuService.delete_combo(db, combo_id, current_tenant.id)

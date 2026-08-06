import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_tenant, get_current_user, require_role
from app.modules.tenancy.schemas import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    RestaurantCreate,
    RestaurantResponse,
    RestaurantSettingsResponse,
    RestaurantSettingsUpdate,
    RestaurantUpdate,
)
from app.modules.tenancy.service import TenancyService

router = APIRouter(prefix="/restaurants", tags=["Tenancy"])


@router.post("", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    schema: RestaurantCreate,
    current_user=Depends(require_role("owner", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new restaurant tenant. Also creates a default branch and settings."""
    return await TenancyService.create_restaurant(db, schema, current_user.id)


@router.get("", response_model=list[RestaurantResponse])
async def list_restaurants(
    current_user=Depends(require_role("owner", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all restaurants (super_admin sees all; owner sees theirs)."""
    user_roles = {r.name for r in current_user.roles}
    if "super_admin" in user_roles:
        return await TenancyService.list_restaurants(db)

    if current_user.restaurant_id:
        try:
            restaurant = await TenancyService.get_restaurant(db, current_user.restaurant_id)
            return [restaurant]
        except Exception:
            return []
    return []


@router.get("/me", response_model=RestaurantResponse)
async def get_restaurant(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.get_restaurant(db, current_tenant.id)


@router.patch("/me", response_model=RestaurantResponse)
async def update_restaurant(
    schema: RestaurantUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.update_restaurant(db, current_tenant.id, schema)


@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant_by_id(
    restaurant_id: uuid.UUID,
    schema: RestaurantUpdate,
    current_user=Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update any restaurant (super_admin only). Allows activating/deactivating tenants."""
    return await TenancyService.update_restaurant(db, restaurant_id, schema)



@router.get("/settings", response_model=RestaurantSettingsResponse)
async def get_settings(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.get_or_create_settings(db, current_tenant.id)


@router.patch("/settings", response_model=RestaurantSettingsResponse)
async def update_settings(
    schema: RestaurantSettingsUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.update_settings(db, current_tenant.id, schema)


@router.post("/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    schema: BranchCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.create_branch(db, current_tenant.id, schema)


@router.get("/branches", response_model=list[BranchResponse])
async def list_branches(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.list_branches(db, current_tenant.id)


@router.patch("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: uuid.UUID,
    schema: BranchUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await TenancyService.update_branch(db, branch_id, schema)

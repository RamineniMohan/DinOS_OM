import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_tenant, get_current_user, require_role
from app.modules.operations.schemas import (
    DiningTableCreate,
    DiningTableResponse,
    DiningTableUpdate,
    FloorCreate,
    FloorResponse,
    TableSectionCreate,
    TableSectionResponse,
    TipCreate,
    TipResponse,
)
from app.modules.operations.service import OperationsService

router = APIRouter(prefix="/operations", tags=["Operations"])


@router.post("/floors", response_model=FloorResponse, status_code=status.HTTP_201_CREATED)
async def create_floor(
    schema: FloorCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.create_floor(db, current_tenant.id, schema)


@router.get("/floors", response_model=list[FloorResponse])
async def list_floors(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.list_floors(db, current_tenant.id)


@router.post("/sections", response_model=TableSectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    schema: TableSectionCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.create_section(db, current_tenant.id, schema)


@router.get("/sections", response_model=list[TableSectionResponse])
async def list_sections(
    floor_id: uuid.UUID,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.list_sections(db, floor_id, current_tenant.id)


@router.post("/tables", response_model=DiningTableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    schema: DiningTableCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.create_table(db, current_tenant.id, schema)


@router.get("/tables", response_model=list[DiningTableResponse])
async def list_tables(
    section_id: uuid.UUID | None = Query(None),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.list_tables(db, current_tenant.id, section_id)


@router.patch("/tables/{table_id}", response_model=DiningTableResponse)
async def update_table(
    table_id: uuid.UUID,
    schema: DiningTableUpdate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.update_table(db, table_id, current_tenant.id, schema)


@router.post("/tips", response_model=TipResponse, status_code=status.HTTP_201_CREATED)
async def create_tip(
    schema: TipCreate,
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "cashier", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.create_tip(db, current_tenant.id, schema)


@router.get("/tips", response_model=list[TipResponse])
async def list_tips(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role("owner", "manager", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsService.list_tips(db, current_tenant.id)

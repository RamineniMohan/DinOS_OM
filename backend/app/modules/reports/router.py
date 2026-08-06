import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_tenant, require_role
from app.modules.reports.schemas import DateRangeParams, GSTReport, InventoryReport, SalesReport
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["Reports"])

_ROLES = ("owner", "manager", "super_admin")


@router.get("/sales", response_model=SalesReport)
async def sales_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    return await ReportsService.sales_report(db, params)


@router.get("/sales/csv")
async def sales_report_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    csv_content = await ReportsService.sales_report_csv(db, params)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={'Content-Disposition': f'attachment; filename="sales_{start_date}_{end_date}.csv"'}
    )


@router.get("/sales/xlsx")
async def sales_report_xlsx(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    xlsx_bytes = await ReportsService.sales_report_xlsx(db, params)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={'Content-Disposition': f'attachment; filename="sales_{start_date}_{end_date}.xlsx"'}
    )


@router.get("/sales/pdf")
async def sales_report_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    pdf_bytes = await ReportsService.sales_report_pdf(db, params)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={'Content-Disposition': f'attachment; filename="sales_{start_date}_{end_date}.pdf"'}
    )


@router.get("/gst", response_model=GSTReport)
async def gst_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    return await ReportsService.gst_report(db, params)


@router.get("/gst/csv")
async def gst_report_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    csv_content = await ReportsService.gst_report_csv(db, params)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={'Content-Disposition': f'attachment; filename="gst_{start_date}_{end_date}.csv"'}
    )


@router.get("/gst/xlsx")
async def gst_report_xlsx(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    xlsx_bytes = await ReportsService.gst_report_xlsx(db, params)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={'Content-Disposition': f'attachment; filename="gst_{start_date}_{end_date}.xlsx"'}
    )


@router.get("/gst/pdf")
async def gst_report_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    params = DateRangeParams(restaurant_id=current_tenant.id, start_date=start_date, end_date=end_date)
    pdf_bytes = await ReportsService.gst_report_pdf(db, params)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={'Content-Disposition': f'attachment; filename="gst_{start_date}_{end_date}.pdf"'}
    )


@router.get("/inventory", response_model=InventoryReport)
async def inventory_report(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    return await ReportsService.inventory_report(db, current_tenant.id)


@router.get("/inventory/csv")
async def inventory_report_csv(
    current_tenant=Depends(get_current_tenant),
    current_user=Depends(require_role(*_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    csv_content = await ReportsService.inventory_report_csv(db, current_tenant.id)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={'Content-Disposition': 'attachment; filename="inventory_report.csv"'}
    )

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator


class DateRangeParams(BaseModel):
    start_date: date
    end_date: date
    restaurant_id: uuid.UUID
    branch_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeParams":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if (self.end_date - self.start_date).days > 366:
            raise ValueError("Date range cannot exceed 366 days")
        return self


class SalesReportRow(BaseModel):
    date: date
    order_count: int
    total_revenue: Decimal
    total_tax: Decimal
    average_order_value: Decimal


class SalesReport(BaseModel):
    restaurant_id: uuid.UUID
    start_date: date
    end_date: date
    total_orders: int
    total_revenue: Decimal
    total_tax: Decimal
    rows: list[SalesReportRow]


class GSTReportRow(BaseModel):
    invoice_number: str
    date: datetime
    customer_name: str | None
    customer_gstin: str | None
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total_tax: Decimal
    total_amount: Decimal


class GSTReport(BaseModel):
    restaurant_id: uuid.UUID
    start_date: date
    end_date: date
    rows: list[GSTReportRow]


class InventoryReportRow(BaseModel):
    ingredient_name: str
    unit: str
    current_stock: Decimal
    low_stock_threshold: Decimal
    is_low_stock: bool


class InventoryReport(BaseModel):
    restaurant_id: uuid.UUID
    rows: list[InventoryReportRow]

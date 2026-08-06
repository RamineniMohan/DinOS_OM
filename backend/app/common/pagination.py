from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    data: list[T]
    meta: PaginationMeta


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(items: list[Any], total: int, page: int, page_size: int) -> dict:
    """Build a paginated response envelope."""
    return {
        "data": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, -(-total // page_size)),  # ceiling division
        },
    }

paginated_response = paginate


def get_offset(page: int, page_size: int) -> int:
    """Calculate SQL offset from page number and page size."""
    return (page - 1) * page_size

"""Reusable pagination, filtering, and query helpers."""

from typing import TypeVar, Generic, List, Optional, Sequence
from pydantic import BaseModel
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 25
    sort_by: Optional[str] = None
    sort_order: str = "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int

    @classmethod
    def create(cls, items: Sequence, total: int, params: PaginationParams):
        return cls(
            items=items,
            total=total,
            page=params.page,
            per_page=params.per_page,
            total_pages=max(1, -(-total // params.per_page)),  # ceil division
        )


async def paginate(db: AsyncSession, query: Select, params: PaginationParams):
    """Execute a query with pagination, return (items, total_count)."""
    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch page
    paginated_q = query.offset(params.offset).limit(params.per_page)
    result = await db.execute(paginated_q)
    items = result.scalars().all()

    return items, total

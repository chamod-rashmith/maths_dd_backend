"""Shared response schemas for offset-based collection pagination."""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

ItemT = TypeVar("ItemT")


class PaginationMetadata(BaseModel):
    """Metadata required by clients to render and continue a collection query."""

    page: int = Field(..., ge=1, description="Current 1-indexed page number")
    page_size: int = Field(..., ge=1, description="Maximum number of items per page")
    total: int = Field(..., ge=0, description="Total number of matching records across all pages")
    total_pages: int = Field(0, ge=0, description="Total number of pages available")
    has_next: bool = Field(..., description="Whether a subsequent page exists")
    has_prev: bool = Field(False, description="Whether a preceding page exists")

    @classmethod
    def from_offset(cls, *, total: int, limit: int, offset: int, items_count: int | None = None) -> "PaginationMetadata":
        """Constructs consistent pagination metadata from offset and limit parameters."""
        page_size = max(1, limit)
        page = (offset // page_size) + 1
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        effective_count = items_count if items_count is not None else page_size
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=(offset + effective_count) < total,
            has_prev=offset > 0,
        )


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Standard envelope for paginated collection responses."""

    items: list[ItemT]
    pagination: PaginationMetadata

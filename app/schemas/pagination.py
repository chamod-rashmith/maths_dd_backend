"""Shared response schemas for offset-based collection pagination."""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

ItemT = TypeVar("ItemT")


class PaginationMetadata(BaseModel):
    """Metadata required by clients to render and continue a collection query."""

    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    has_next: bool


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Standard envelope for paginated collection responses."""

    items: list[ItemT]
    pagination: PaginationMetadata

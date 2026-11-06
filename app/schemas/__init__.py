"""Pydantic request and response DTO schemas."""

from app.schemas.common import (
    BaseSchema,
    BookmarkToggleResponse,
    DeleteResponse,
    ErrorDetail,
    ErrorResponse,
    MaintenanceExpirationResponse,
    WebhookAckResponse,
)
from app.schemas.pagination import PaginatedResponse, PaginationMetadata

__all__ = [
    "BaseSchema",
    "BookmarkToggleResponse",
    "DeleteResponse",
    "ErrorDetail",
    "ErrorResponse",
    "MaintenanceExpirationResponse",
    "PaginatedResponse",
    "PaginationMetadata",
    "WebhookAckResponse",
]

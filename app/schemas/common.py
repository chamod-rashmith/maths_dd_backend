"""
Common shared DTO response schemas for standard operations, error envelopes, and maintenance routines.
Ensures every API endpoint has a strict, documented OpenAPI response schema.
"""

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Canonical base schema enabling attribute-based validation and field population."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ErrorDetail(BaseSchema):
    """Structured machine-readable and human-readable error detail."""

    code: str = Field(..., description="Stable machine-readable error code (e.g. 'NOT_FOUND', 'FORBIDDEN')")
    message: str | list[dict] = Field(..., description="Human-readable error description or validation errors")
    request_id: str = Field(..., description="Unique request correlation ID for log tracing")


class ErrorResponse(BaseSchema):
    """Standardized global API error envelope."""

    error: ErrorDetail
    detail: str | list[dict] = Field(..., description="Legacy-compatible top-level error detail")


class DeleteResponse(BaseSchema):
    """Standardized response returned when an entity is deleted or soft-deleted."""

    status: str = Field("success", description="Operation status ('success')")
    deleted_id: str = Field(..., description="Identifier of the deleted resource")
    message: str | None = Field(None, description="Optional confirmation message")


class BookmarkToggleResponse(BaseSchema):
    """Response returned when starring/bookmarking or unstarring a question."""

    question_id: str = Field(..., description="Identifier of the target question")
    is_bookmarked: bool = Field(..., description="Updated bookmark status for the authenticated user")


class WebhookAckResponse(BaseSchema):
    """Acknowledgement response for server-to-server webhook receivers (e.g. RevenueCat)."""

    status: str = Field(..., description="Processing status ('success' or 'already_processed')")
    event_id: str = Field(..., description="Unique webhook event identifier")
    type: str | None = Field(None, description="Processed webhook event type")


class MaintenanceExpirationResponse(BaseSchema):
    """Response returned by scheduled subscription expiration maintenance tasks."""

    status: str = Field("success", description="Execution status")
    expired_count: int = Field(..., ge=0, description="Number of stale active subscriptions transitioned to EXPIRED")
    timestamp: str = Field(..., description="ISO-8601 UTC execution timestamp")

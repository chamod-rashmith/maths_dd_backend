"""
Global FastAPI Exception Handlers mapping pure DomainExceptions to structured HTTP responses.
Prevents leaking internal stack traces or raw SQL errors to clients.
"""

import logging
from typing import Any
from uuid import uuid4
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import (
    AuthenticationError,
    DatabaseOperationError,
    DomainException,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationDomainError,
)

logger = logging.getLogger("maths_dd.exceptions")


def _request_id(request: Request) -> str:
    """Returns the request ID assigned by the application middleware."""
    return getattr(request.state, "request_id", str(uuid4()))


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: Any,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Builds the stable API error envelope while preserving legacy `detail`."""
    payload = {
        "error": {
            "code": code,
            "message": jsonable_encoder(message),
            "request_id": _request_id(request),
        },
        "detail": jsonable_encoder(message),
    }
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global domain and unhandled exception handlers on the FastAPI app."""

    @app.exception_handler(EntityNotFoundError)
    async def handle_not_found(
        request: Request, exc: EntityNotFoundError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=exc.message,
        )

    @app.exception_handler(ValidationDomainError)
    async def handle_validation_error(
        request: Request, exc: ValidationDomainError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=exc.message,
        )

    @app.exception_handler(AuthenticationError)
    async def handle_authentication_error(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_REQUIRED",
            message=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(PermissionDeniedError)
    async def handle_permission_denied(
        request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=exc.message,
        )

    @app.exception_handler(DatabaseOperationError)
    async def handle_database_error(
        request: Request, exc: DatabaseOperationError
    ) -> JSONResponse:
        logger.error("Database operation failed: %s", exc.message)
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message="A database error occurred while processing the request.",
        )

    @app.exception_handler(DomainException)
    async def handle_generic_domain_error(
        request: Request, exc: DomainException
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message=exc.message,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="REQUEST_VALIDATION_ERROR",
            message=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error: %s", exc)
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred while processing the request.",
        )

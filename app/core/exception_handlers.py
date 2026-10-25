"""
Global FastAPI Exception Handlers mapping pure DomainExceptions to structured HTTP responses.
Prevents leaking internal stack traces or raw SQL errors to clients.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AuthenticationError,
    DatabaseOperationError,
    DomainException,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationDomainError,
)

logger = logging.getLogger("maths_dd.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global domain and unhandled exception handlers on the FastAPI app."""

    @app.exception_handler(EntityNotFoundError)
    async def handle_not_found(
        _request: Request, exc: EntityNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message},
        )

    @app.exception_handler(ValidationDomainError)
    async def handle_validation_error(
        _request: Request, exc: ValidationDomainError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

    @app.exception_handler(AuthenticationError)
    async def handle_authentication_error(
        _request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(PermissionDeniedError)
    async def handle_permission_denied(
        _request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message},
        )

    @app.exception_handler(DatabaseOperationError)
    async def handle_database_error(
        _request: Request, exc: DatabaseOperationError
    ) -> JSONResponse:
        logger.error("Database operation failed: %s", exc.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred while processing the request."},
        )

    @app.exception_handler(DomainException)
    async def handle_generic_domain_error(
        _request: Request, exc: DomainException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

"""
Domain-specific Exceptions (Pure Python, decoupled from HTTP status codes).
Mapped to HTTP responses globally in `app/core/exception_handlers.py`.
"""


class DomainException(Exception):
    """Base class for all domain and application layer exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainException):
    """Raised when a requested domain entity does not exist."""


class ValidationDomainError(DomainException):
    """Raised when domain invariants or business validation rules fail."""


class AuthenticationError(DomainException):
    """Raised when authentication credentials or tokens are missing or invalid."""


class PermissionDeniedError(DomainException):
    """Raised when an authenticated user lacks sufficient role privileges."""


class DatabaseOperationError(DomainException):
    """Raised when an underlying persistence operation fails."""

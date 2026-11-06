"""Reusable authenticated encryption helpers for sensitive database fields."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _cipher() -> Fernet:
    """Build the cipher from the deployment-provided key."""
    key = settings.DATA_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "DATA_ENCRYPTION_KEY must be configured before encrypting sensitive data."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "DATA_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def encrypt_field(value: str | None) -> str | None:
    """Encrypt a sensitive string before storing it in the database."""
    if value is None or not value.strip():
        return value
    return _cipher().encrypt(value.strip().encode("utf-8")).decode("ascii")


def decrypt_field(value: str | None) -> str | None:
    """
    Decrypt a sensitive string retrieved from the database.

    Returning an unchanged value supports a one-time migration from legacy
    plaintext rows; new writes are always encrypted.
    """
    if value is None or not value.strip():
        return value
    # Legacy plaintext values do not have the Fernet token prefix.
    if not value.startswith("gAAAA"):
        return value
    try:
        return _cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return value

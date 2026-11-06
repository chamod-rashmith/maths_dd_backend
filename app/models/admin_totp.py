"""
SQLAlchemy 2.0 ORM model for Admin TOTP Credentials & Recovery Codes (`admin_totp_credentials`).
Stores AES/Fernet encrypted Base32 TOTP secrets and salted PBKDF2-HMAC-SHA256 hashed single-use recovery codes.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdminTotpCredential(Base):
    """
    Stores RFC 6238 TOTP configuration for privileged users (ADMIN, EDITOR, ACCOUNT_AUDIT).
    - `encrypted_secret`: Fernet/AES encrypted Base32 secret (never stored in plaintext).
    - `recovery_codes_hash`: JSON array of salted PBKDF2-HMAC-SHA256 hashes for 8 single-use backup codes.
    """

    __tablename__ = "admin_totp_credentials"

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_codes_hash: Mapped[str] = mapped_column(
        Text,
        default="[]",
        server_default=text("'[]'"),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AdminTotpCredential(user_id='{self.user_id}', is_enabled={self.is_enabled})>"

"""
SQLAlchemy 2.0 ORM model for Users (Identity & Auth Profile).
Gamification and high-frequency study telemetry are isolated in `UserStats`.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, Date, DateTime, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user_stats import UserStats


class User(Base):
    __tablename__ = "users"

    uid: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="USER", server_default=text("'USER'"), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    school_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stream: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    attempt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    premium_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
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

    stats: Mapped[Optional["UserStats"]] = relationship(
        "UserStats",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<User(uid='{self.uid}', email='{self.email}', name='{self.name}')>"

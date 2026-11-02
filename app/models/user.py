"""
SQLAlchemy 2.0 ORM model for Users (Identity & Auth Profile).
Gamification is isolated in `UserStats`, Subscriptions in `UserSubscription`, and regional data references `District`.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user_stats import UserStats
    from app.models.subscription import UserSubscription
    from app.models.district import District


class User(Base):
    __tablename__ = "users"

    uid: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="USER", server_default=text("'USER'"), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    school_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    district_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("districts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stream: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    attempt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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

    district: Mapped[Optional["District"]] = relationship(
        "District",
        back_populates="users",
        lazy="joined",
    )

    stats: Mapped[Optional["UserStats"]] = relationship(
        "UserStats",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )

    subscriptions: Mapped[List["UserSubscription"]] = relationship(
        "UserSubscription",
        foreign_keys="UserSubscription.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(UserSubscription.created_at)",
        lazy="selectin",
    )

    @property
    def is_premium(self) -> bool:
        """Dynamically evaluate if user has active premium access."""
        if self.role == "ADMIN":
            return True
        if not self.subscriptions:
            return False
        return any(sub.is_currently_active() for sub in self.subscriptions)

    @property
    def active_subscription(self) -> Optional["UserSubscription"]:
        """Returns the most recent active subscription if available."""
        if not self.subscriptions:
            return None
        for sub in self.subscriptions:
            if sub.is_currently_active():
                return sub
        return None

    def __repr__(self) -> str:
        return f"<User(uid='{self.uid}', email='{self.email}', name='{self.name}')>"

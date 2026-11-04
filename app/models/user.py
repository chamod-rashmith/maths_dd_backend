"""
SQLAlchemy 2.0 ORM model for Users (Identity & Auth Profile).

===============================================================================
පරිශීලක අනන්‍යතාවය සහ ගිණුම් කළමනාකරණය (User Identity & Profile):
-------------------------------------------------------------------------------
1. මූලික Auth අනන්‍යතාවය (`uid`, `email`, `name`, `role`, `avatar_url`).
2. ශාස්ත්‍රීය දත්ත (`StudentProfile`) 1-to-1 සම්බන්ධතාවය හරහා Domain 1 යටතේ
   සාමාන්‍යකරණය (Normalized 3NF) කර ඇත:
   - Target A/L Year (`exam_year`)
   - Exam Sitting Attempt (`attempt_number`: 1st, 2nd, 3rd shy)
   - Z-Score Exam District (`exam_district_id`)
3. Gamification දත්ත `UserStats` සමඟද, Subscriptions `UserSubscription` සමඟද
   ආරක්ෂිතව හුදකලා (Decoupled) කර ඇත.
===============================================================================
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user_stats import UserStats
    from app.models.student_profile import StudentProfile
    from app.models.subscription import UserSubscription
    from app.models.district import District


class User(Base):
    """
    Core User entity managing authentication, credentials, and authorization roles.
    Academic profiling attributes are normalized in the 1-to-1 `StudentProfile` entity.
    """

    __tablename__ = "users"

    uid: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="USER", server_default=text("'USER'"), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Legacy direct columns retained for backward compatibility with external integrations
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

    # -------------------------------------------------------------------------
    # Normalized Relationships (සාමාන්‍යකරණය කරන ලද සබඳතා)
    # -------------------------------------------------------------------------
    # 1. District reference (පදිංචි දිස්ත්‍රික්කය)
    district: Mapped[Optional["District"]] = relationship(
        "District",
        foreign_keys=[district_id],
        back_populates="users",
        lazy="joined",
    )

    # 2. Normalized Academic Student Profile (A/L විභාග ශාස්ත්‍රීය පැතිකඩ)
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        "StudentProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )

    # 3. Gamification stats projection (ලකුණු, Streaks, XP)
    stats: Mapped[Optional["UserStats"]] = relationship(
        "UserStats",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )

    # 4. Subscription records (වාරික සහ බැංකු ගෙවීම්)
    subscriptions: Mapped[List["UserSubscription"]] = relationship(
        "UserSubscription",
        foreign_keys="UserSubscription.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(UserSubscription.created_at)",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Dynamic Properties & Normalized Proxies
    # -------------------------------------------------------------------------
    @property
    def exam_year(self) -> Optional[int]:
        """Target G.C.E. A/L exam year from normalized StudentProfile."""
        return self.student_profile.exam_year if self.student_profile else None

    @property
    def attempt_number(self) -> Optional[int]:
        """Exam attempt count (1, 2, or 3) from normalized StudentProfile."""
        return self.student_profile.attempt_number if self.student_profile else None

    @property
    def exam_district_id(self) -> Optional[int]:
        """Z-Score exam district ID from normalized StudentProfile or fallback district_id."""
        if self.student_profile and self.student_profile.exam_district_id is not None:
            return self.student_profile.exam_district_id
        return self.district_id

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

"""
SQLAlchemy 2.0 ORM model for Users.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    uid: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="USER", nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    school_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stream: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    attempt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    questions_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    premium_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_solved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_study_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes User entity into a dictionary contract."""
        return {
            "uid": self.uid,
            "email": self.email,
            "name": self.name,
            "telephone_no": self.telephone_no,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "school_name": self.school_name,
            "district": self.district,
            "stream": self.stream,
            "grade": self.grade,
            "attempt": self.attempt,
            "xp": self.xp,
            "streak_count": self.streak_count,
            "accuracy_rate": self.accuracy_rate,
            "questions_solved": self.questions_solved,
            "is_premium": self.is_premium,
            "premium_expiry": self.premium_expiry,
            "current_streak_days": self.current_streak_days,
            "longest_streak_days": self.longest_streak_days,
            "total_solved_count": self.total_solved_count,
            "total_study_time_seconds": self.total_study_time_seconds,
            "last_active_date": self.last_active_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return f"<User(uid='{self.uid}', email='{self.email}', name='{self.name}')>"

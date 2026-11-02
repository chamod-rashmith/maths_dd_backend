"""
SQLAlchemy 2.0 ORM model for User Stats & Gamification Telemetry.
Decoupled 1:1 table from users to isolate high-frequency write operations.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    total_solved_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    total_study_time_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    accuracy_rate: Mapped[float] = mapped_column(Float, default=0.0, server_default=text("0.0"), nullable=False)
    last_active_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="stats")

    def __repr__(self) -> str:
        return f"<UserStats(user_id='{self.user_id}', xp={self.xp}, streak={self.current_streak_days}, solved={self.total_solved_count})>"

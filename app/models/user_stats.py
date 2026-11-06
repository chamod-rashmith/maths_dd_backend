"""
SQLAlchemy 2.0 ORM model for User Stats & Gamification Telemetry.
මෙම මොඩියුලය මඟින් ශිෂ්‍යයාගේ සමස්ත අධ්‍යයන දත්ත, Streaks, සහ XP පිළිබඳ Read-Model (CQRS Projection) කළමනාකරණය කරයි.

Design Principles:
1. Isolated High-Frequency Table:
   - Separated from the `users` authentication table to prevent database row-locking contention.
2. Accurate Projection:
   - `xp` reflects the verified total sum of immutable `XpTransaction` entries.
   - `total_study_time_seconds` stores the accurate cumulative study duration across all practice sessions.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserStats(Base):
    """
    ශිෂ්‍යයාගේ සමස්ත සංඛ්‍යාලේඛන සහ Gamification තොරතුරු (User Stats Summary Projection).
    වේගවත් විමසුම් සඳහා (Fast Queries) මෙහි දත්ත cache කර ඇත.
    """

    __tablename__ = "user_stats"
    __table_args__ = (
        Index("idx_user_stats_leaderboard_xp", "xp", "total_solved_count", "current_streak_days"),
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )

    # Projected total XP (Sum of xp_transactions.amount)
    xp: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="සමස්ත අත්දැකීම් ලකුණු (Total XP from XpTransaction ledger)",
    )

    # Current continuous daily practice streak
    current_streak_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="වත්මන් අඛණ්ඩ දින ගණන (Current Streak)",
    )

    # All-time longest continuous daily practice streak
    longest_streak_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="මෙතෙක් ලබාගත් වැඩිම අඛණ්ඩ දින ගණන (Longest Streak)",
    )

    # Total distinct questions solved
    total_solved_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="විසඳූ සමස්ත ප්‍රශ්න ගණන",
    )

    # True cumulative study time across all attempts in seconds
    total_study_time_seconds: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="අධ්‍යයනය සඳහා වැය කළ මුළු කාලය (තත්පර වලින් - Cumulative across all sessions)",
    )

    # Percentage accuracy rate (0.0 to 100.0)
    accuracy_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default=text("0.0"),
        nullable=False,
        comment="නිරවද්‍යතා ප්‍රතිශතය",
    )

    # Last active calendar date (Asia/Colombo timezone)
    last_active_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="අවසන් වරට ක්‍රියාකාරී වූ දිනය",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="stats")

    def __repr__(self) -> str:
        return (
            f"<UserStats(user_id='{self.user_id}', xp={self.xp}, streak={self.current_streak_days}, "
            f"solved={self.total_solved_count}, time={self.total_study_time_seconds}s)>"
        )

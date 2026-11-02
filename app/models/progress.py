"""
SQLAlchemy 2.0 ORM models for Student Progress, Question Attempts, and Activity Heatmap.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.question import Question


class UserQuestionAttempt(Base):
    __tablename__ = "user_question_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_attempt"),
        Index("idx_attempt_user_question", "user_id", "question_id"),
        Index("idx_attempt_user_date", "user_id", "completed_date"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.uid", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    target_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    was_overtime: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"), nullable=False)
    is_daily_question: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    completed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    confidence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    student_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    # Relationships
    question: Mapped["Question"] = relationship("Question", lazy="joined")
    user: Mapped["User"] = relationship("User")


class UserDailyActivity(Base):
    __tablename__ = "user_daily_activities"
    __table_args__ = (
        UniqueConstraint("user_id", "date_key", name="uq_user_daily_activity"),
        Index("idx_daily_activity_user_date", "user_id", "date_key"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.uid", ondelete="CASCADE"), nullable=False, index=True
    )
    date_key: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    questions_solved_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    total_time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    daily_challenge_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
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

    user: Mapped["User"] = relationship("User")

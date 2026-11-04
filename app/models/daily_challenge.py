"""
SQLAlchemy 2.0 ORM models for Daily Challenge Sets and Multi-Question Junctions.

Architecture & Business Context:
- A Daily Challenge represents a structured daily workout (Day 1, Day 2... Day N).
- Instead of coupling a single question to a date, a Daily Challenge can contain multiple
  questions (e.g. 1 question, 4 questions [2 Short + 2 Essay], or 8-10 Marathon questions).
- The junction table `daily_challenge_questions` normalizes the relationship, preserving
  canonical section ordering (SHORT vs ESSAY) and mark allocations per challenge.
"""

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.question import Question
    from app.models.subject import Subject


class DailyChallenge(Base):
    """
    Represents a full daily workout set for students.
    
    Fields:
    - id: Unique UUIDv4 identifier
    - day_number: Sequential challenge series index (Day 1, Day 2, Day 3...)
    - scheduled_date: Calendar date when this challenge is scheduled (in Asia/Colombo)
    - title: Human-readable challenge title (e.g. 'Day 14 - Combined Maths Challenge')
    - description: Optional guidance or instructions for students
    - target_duration_seconds: Recommended workout time (e.g. 3600 for 1 hour)
    - total_marks: Aggregate total marks for this daily challenge set
    - is_published: Whether the challenge is active and accessible to students
    """

    __tablename__ = "daily_challenges"
    __table_args__ = (
        Index("idx_daily_challenges_day_date", "day_number", "scheduled_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    day_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        nullable=False,
    )
    scheduled_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    subject_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=3600,
        server_default=text("3600"),
        nullable=False,
    )
    total_marks: Mapped[int] = mapped_column(
        Integer,
        default=100,
        server_default=text("100"),
        nullable=False,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
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

    # Relationships
    subject: Mapped[Optional["Subject"]] = relationship("Subject")
    challenge_questions: Mapped[List["DailyChallengeQuestion"]] = relationship(
        "DailyChallengeQuestion",
        back_populates="challenge",
        cascade="all, delete-orphan",
        order_by="DailyChallengeQuestion.order_index",
    )

    def __repr__(self) -> str:
        return f"<DailyChallenge(day_number={self.day_number}, title='{self.title}', date={self.scheduled_date})>"


class DailyChallengeQuestion(Base):
    """
    Junction mapping questions into a Daily Challenge pack with specific order and section.

    Fields:
    - id: Unique UUIDv4 identifier
    - daily_challenge_id: Reference to parent DailyChallenge
    - question_id: Reference to Question in questions table
    - order_index: Presentation order within the daily workout (1, 2, 3...)
    - section: Question section category ('SHORT' or 'ESSAY')
    - allocated_marks: Marks allocated for this question within this challenge
    - is_mandatory: Whether completing this question is required for streak completion
    """

    __tablename__ = "daily_challenge_questions"
    __table_args__ = (
        UniqueConstraint("daily_challenge_id", "question_id", name="uq_challenge_question"),
        UniqueConstraint("daily_challenge_id", "order_index", name="uq_challenge_order"),
        Index("idx_dc_question_lookup", "daily_challenge_id", "order_index"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    daily_challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("daily_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    section: Mapped[str] = mapped_column(
        String(50),
        default="SHORT",
        server_default=text("'SHORT'"),
        nullable=False,
    )
    allocated_marks: Mapped[int] = mapped_column(
        Integer,
        default=25,
        server_default=text("25"),
        nullable=False,
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
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

    # Relationships
    challenge: Mapped["DailyChallenge"] = relationship(
        "DailyChallenge",
        back_populates="challenge_questions",
    )
    question: Mapped["Question"] = relationship("Question")

    def __repr__(self) -> str:
        return f"<DailyChallengeQuestion(challenge_id='{self.daily_challenge_id}', question_id='{self.question_id}', order={self.order_index})>"

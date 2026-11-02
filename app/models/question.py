"""
SQLAlchemy 2.0 ORM model for Questions.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.lesson import SyllabusLesson
    from app.models.marking_scheme import MarkingScheme


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default="", nullable=True)
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("syllabus_lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(50), default="SHORT", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="MEDIUM", nullable=False)
    schedule: Mapped[str] = mapped_column(String(50), default="REGULAR", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="PAST_PAPER", nullable=False)
    source_details: Mapped[Optional[str]] = mapped_column(Text, default="", nullable=True)
    allocated_marks: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
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

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="questions")
    lesson: Mapped[Optional["SyllabusLesson"]] = relationship("SyllabusLesson", back_populates="questions")
    marking_schemes: Mapped[List["MarkingScheme"]] = relationship(
        "MarkingScheme",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="MarkingScheme.order_index",
    )

    __table_args__ = (
        Index("idx_questions_subject_lesson", "subject_id", "lesson_id", "is_published"),
        Index("idx_questions_scheduled_date", "scheduled_date"),
    )

    
    def __repr__(self) -> str:
        return f"<Question(id='{self.id}', title='{self.title}', subject_id='{self.subject_id}')>"

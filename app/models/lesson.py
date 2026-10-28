"""
SQLAlchemy 2.0 ORM model for Syllabus Lessons.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.question import Question
    from app.models.study_note import StudyNote


class SyllabusLesson(Base):
    __tablename__ = "syllabus_lessons"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sinhala_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    premium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    subject: Mapped["Subject"] = relationship("Subject", back_populates="lessons")
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="lesson",
    )
    study_notes: Mapped[List["StudyNote"]] = relationship(
        "StudyNote",
        back_populates="lesson",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes SyllabusLesson entity into a dictionary contract."""
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "title": self.title,
            "sinhala_title": self.sinhala_title,
            "order_index": self.order_index,
            "description": self.description,
            "question_count": self.question_count,
            "premium_count": self.premium_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return f"<SyllabusLesson(id='{self.id}', title='{self.title}', subject_id='{self.subject_id}')>"

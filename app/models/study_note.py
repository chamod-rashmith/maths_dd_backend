"""
SQLAlchemy 2.0 ORM model for Study Notes.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.lesson import SyllabusLesson


class StudyNote(Base):
    __tablename__ = "study_notes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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
    subject: Mapped["Subject"] = relationship("Subject", back_populates="study_notes")
    lesson: Mapped[Optional["SyllabusLesson"]] = relationship("SyllabusLesson", back_populates="study_notes")

    __table_args__ = (
        Index("idx_study_notes_subject_order", "subject_id", "order_index", "created_at"),
        Index("idx_study_notes_subject_lesson", "subject_id", "lesson_id", "order_index"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes StudyNote entity into a dictionary contract."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "subject_id": self.subject_id,
            "lesson_id": self.lesson_id,
            "content_text": self.content_text,
            "pdf_url": self.pdf_url,
            "is_premium": self.is_premium,
            "order_index": self.order_index,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return f"<StudyNote(id='{self.id}', title='{self.title}', subject_id='{self.subject_id}')>"

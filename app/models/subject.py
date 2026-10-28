"""
SQLAlchemy 2.0 ORM model for Subjects.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.lesson import SyllabusLesson
    from app.models.question import Question
    from app.models.study_note import StudyNote


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sinhala_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    lessons: Mapped[List["SyllabusLesson"]] = relationship(
        "SyllabusLesson",
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="SyllabusLesson.order_index",
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    study_notes: Mapped[List["StudyNote"]] = relationship(
        "StudyNote",
        back_populates="subject",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Subject entity into a dictionary contract."""
        return {
            "id": self.id,
            "name": self.name,
            "sinhala_name": self.sinhala_name,
            "code": self.code,
            "order_index": self.order_index,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return f"<Subject(id='{self.id}', code='{self.code}', name='{self.name}')>"

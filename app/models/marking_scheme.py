"""
SQLAlchemy 2.0 ORM model for Marking Schemes.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.question import Question


class MarkingScheme(Base):
    __tablename__ = "marking_schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        default="Official Marking Scheme",
        nullable=False,
    )
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_marks: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_premium_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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
    question: Mapped["Question"] = relationship("Question", back_populates="marking_schemes")

    __table_args__ = (
        Index("idx_marking_schemes_question_id", "question_id", "order_index"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes MarkingScheme entity into a dictionary contract."""
        return {
            "id": str(self.id),
            "question_id": self.question_id,
            "title": self.title,
            "content_text": self.content_text,
            "pdf_url": self.pdf_url,
            "total_marks": self.total_marks,
            "is_official": self.is_official,
            "is_premium_only": self.is_premium_only,
            "order_index": self.order_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self) -> str:
        return f"<MarkingScheme(id='{self.id}', question_id='{self.question_id}', title='{self.title}')>"

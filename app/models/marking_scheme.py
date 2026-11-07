"""
SQLAlchemy 2.0 ORM model for Official Marking Schemes (`marking_schemes`).
Supports both Markdown + LaTeX (`content_text`) and PDF (`pdf_url`) solutions.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.question import Question


class MarkingScheme(Base):
    """
    ප්‍රශ්නයක නිල ලකුණු දීමේ පටිපාටිය (Official Marking Scheme).
    Markdown + LaTeX (`content_text`) හෝ PDF (`pdf_url`) මඟින් සම්පූර්ණ විසඳුම ගබඩා කරයි.
    """

    __tablename__ = "marking_schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="ලකුණු දීමේ පටිපාටියේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    question_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="අදාළ ප්‍රශ්නයේ හැඳුනුම් අංකය (FK to questions.id)",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        default="Official Marking Scheme",
        server_default=text("'Official Marking Scheme'"),
        nullable=False,
        comment="මාතෘකාව (e.g. 'නිල ලකුණු දීමේ පටිපාටිය')",
    )

    description_si: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="ලකුණු දීමේ ක්‍රමවේදය පිළිබඳ කෙටි හැඳින්වීම (Sinhala Description)",
    )

    content_text: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default=text("''"),
        nullable=False,
        comment="සම්පූර්ණ ලකුණු දීමේ පටිපාටියේ Markdown/LaTeX පෙළ",
    )

    pdf_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="PDF ලේඛනයක් ඇත්නම් ඒ සඳහා වන URL එක",
    )

    total_marks: Mapped[int] = mapped_column(
        Integer,
        default=25,
        server_default=text("25"),
        nullable=False,
        comment="ප්‍රශ්නයට හිමි මුළු ලකුණු ප්‍රමාණය",
    )

    is_official: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        comment="විභාග දෙපාර්තමේන්තුවේ නිල පටිපාටියක්ද යන්න",
    )

    is_premium_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="Premium සාමාජිකයන්ට පමණක් සීමා වේද යන්න",
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
        comment="ප්‍රදර්ශනය කරන අනුපිළිවෙල",
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
    question: Mapped["Question"] = relationship("Question", back_populates="marking_schemes")

    __table_args__ = (
        Index("idx_marking_schemes_question_id", "question_id", "order_index"),
    )

    @property
    def content_type(self) -> str:
        """Resolves 'pdf' when pdf_url is present, otherwise 'markdown'."""
        if self.pdf_url and self.pdf_url.strip():
            return "pdf"
        return "markdown"

    def __repr__(self) -> str:
        return f"<MarkingScheme(id='{self.id}', question_id='{self.question_id}', title='{self.title}')>"

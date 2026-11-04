"""
SQLAlchemy 2.0 ORM model for Exam Papers (Past A/L Papers, Model Papers, and Provincial Tests).
මෙම මොඩියුලය මඟින් අ.පො.ස. උසස් පෙළ පසුගිය විභාග ප්‍රශ්න පත්‍ර (Past Papers) සහ ආදර්ශ ප්‍රශ්න පත්‍ර (Model Papers)
සම්බන්ධ සියලුම දත්ත ව්‍යුහයන් පූර්ණ සාමාන්‍යකරණයෙන් (3NF) කළමනාකරණය කරයි.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.question import Question


class ExamPaper(Base):
    """
    විභාග ප්‍රශ්න පත්‍ර වාර්තාව (A/L Exam Paper Entity).
    උදාහරණ: 2023 අ.පො.ස. උසස් පෙළ සංයුක්ත ගණිතය I කොටස.
    """

    __tablename__ = "exam_papers"

    # UUID Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="විභාග ප්‍රශ්න පත්‍රයේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    # Subject Foreign Key (e.g. Combined Maths, Physics)
    subject_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="අදාළ විෂය (FK to subjects.id)",
    )

    # Exam paper type: AL_GOVT, MODEL, PROVINCIAL, SCHOOL
    type: Mapped[str] = mapped_column(
        String(32),
        default="AL_GOVT",
        server_default=text("'AL_GOVT'"),
        nullable=False,
        index=True,
        comment="ප්‍රශ්න පත්‍ර වර්ගය (AL_GOVT, MODEL, PROVINCIAL)",
    )

    # Target examination year (e.g. 2023, 2024)
    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="විභාග වර්ෂය (e.g. 2023, 2024)",
    )

    # Paper part / section: PART_I (Short), PART_II_A, PART_II_B, FULL
    part: Mapped[str] = mapped_column(
        String(32),
        default="PART_I",
        server_default=text("'PART_I'"),
        nullable=False,
        comment="ප්‍රශ්න පත්‍ර කොටස (PART_I, PART_II_A, PART_II_B, FULL)",
    )

    # Localized Sinhala title for display (e.g. "2023 අ.පො.ස. උසස් පෙළ සංයුක්ත ගණිතය I")
    title_si: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ප්‍රශ්න පත්‍රයේ සිංහල නම",
    )

    # Optional English title
    title_en: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ප්‍රශ්න පත්‍රයේ ඉංග්‍රීසි නම",
    )

    # Original official PDF question paper link
    source_pdf_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="ප්‍රශ්න පත්‍රයේ නිල PDF ලේඛනයේ URL එක",
    )

    # Publication visibility
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        comment="සිසුන්ට ප්‍රදර්ශනය කරන්නේද යන්න",
    )

    # Audit Timestamps
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
    subject: Mapped["Subject"] = relationship("Subject", lazy="joined")
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="exam_paper",
    )

    __table_args__ = (
        Index("idx_exam_papers_subject_year", "subject_id", "year", "type"),
    )

    def __repr__(self) -> str:
        return f"<ExamPaper(id='{self.id}', title_si='{self.title_si}', year={self.year}, type='{self.type}')>"

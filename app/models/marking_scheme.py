"""
SQLAlchemy 2.0 ORM model for Marking Schemes and Marking Scheme Steps.

===============================================================================
විභාග ලකුණු දීමේ පටිපාටිය සහ පියවර සාමාන්‍යකරණය (Marking Schemes & Rubric Steps):
-------------------------------------------------------------------------------
1. `MarkingScheme`: Header entity representing the marking scheme for a question.
   Uses UUID primary key aligned with native PostgreSQL UUID type.
2. `MarkingSchemeStep`: 3NF Step-by-Step marking rubric item:
   - `marking_scheme_id`: Foreign key (UUID) to `marking_schemes.id` (CASCADE delete).
   - `step_number`: Sequence number of the step (1, 2, 3...).
   - `step_type`: METHOD (M1), ACCURACY (A1), FINAL (B1), BONUS.
   - `description_si`: Step solution in Sinhala + LaTeX mathematical notations.
   - `allocated_marks`: Marks granted for this specific step.
   - `annotation`: Examiner guidance or alternative method notes.
===============================================================================
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.question import Question


class MarkingScheme(Base):
    """
    ප්‍රශ්නයක නිල ලකුණු දීමේ පටිපාටිය (Official Marking Scheme Header).
    සම්පූර්ණ ලකුණු ප්‍රමාණය, විවරණය, සහ පියවරෙන් පියවර විග්‍රහය (MarkingSchemeStep) සමඟ සම්බන්ධ වේ.
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
    steps: Mapped[List["MarkingSchemeStep"]] = relationship(
        "MarkingSchemeStep",
        back_populates="marking_scheme",
        cascade="all, delete-orphan",
        order_by="MarkingSchemeStep.order_index",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_marking_schemes_question_id", "question_id", "order_index"),
    )

    def __repr__(self) -> str:
        return f"<MarkingScheme(id='{self.id}', question_id='{self.question_id}', title='{self.title}')>"


class MarkingSchemeStep(Base):
    """
    ලකුණු දීමේ පටිපාටියේ තනි පියවරක් (Step-by-Step Marking Rubric Entity - 3NF).
    උසස් පෙළ විභාග වල ක්‍රමයට අනුව ක්‍රමයට ලකුණු (Method Marks - M1),
    නිවැරදි අගයට ලකුණු (Accuracy Marks - A1), සහ අවසන් පිළිතුරට ලකුණු (B1) වෙන් වෙන්ව නිරූපණය කරයි.
    """

    __tablename__ = "marking_scheme_steps"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="පියවරේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    marking_scheme_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("marking_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="අදාළ Marking Scheme එකෙහි ID (FK to marking_schemes.id)",
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
        comment="පියවර අංකය (e.g. 1, 2, 3...)",
    )

    # Step type: METHOD (M1), ACCURACY (A1), FINAL (B1), BONUS
    step_type: Mapped[str] = mapped_column(
        String(32),
        default="METHOD",
        server_default=text("'METHOD'"),
        nullable=False,
        comment="ලකුණු වර්ගය (METHOD - ක්‍රමයට, ACCURACY - නිවැරදි අගයට, FINAL - අවසන් පිළිතුරට)",
    )

    # Detailed solution step in Sinhala + LaTeX
    description_si: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="පියවරේ ගණිතමය විසඳුම (Sinhala + LaTeX math expression)",
    )

    # Marks allocated for this step
    allocated_marks: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
        comment="මෙම පියවර සඳහා හිමිවන ලකුණු ප්‍රමාණය",
    )

    # Examiner guidance or alternative solution note
    annotation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="පරීක්ෂක සටහන් හෝ විකල්ප ක්‍රම (Examiner Notes / Alternatives)",
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

    # Relationships
    marking_scheme: Mapped["MarkingScheme"] = relationship(
        "MarkingScheme",
        back_populates="steps",
    )

    __table_args__ = (
        Index("idx_marking_steps_scheme_order", "marking_scheme_id", "order_index"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarkingSchemeStep(id='{self.id}', step_no={self.step_number}, "
            f"type='{self.step_type}', marks={self.allocated_marks})>"
        )

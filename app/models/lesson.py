"""
SQLAlchemy 2.0 ORM model for Syllabus Lessons.

===============================================================================
විෂය නිර්දේශයේ පාඩම් සහ උප-පාඩම් ධුරාවලිය (Curriculum & Syllabus Hierarchy):
-------------------------------------------------------------------------------
G.C.E. A/L Combined Mathematics (Pure Maths / Applied Maths) හෝ Physics
විෂය නිර්දේශයේ පාඩම් ප්‍රධාන කාණ්ඩ (Main Units/Chapters) සහ ඒ යටතේ පවතින
උප-පාඩම් (Sub-lessons / Subtopics) ලෙස ශ්‍රේණිගතව (Hierarchical) බෙදී පවතී.

උදාහරණ:
- Main Unit (parent_lesson_id = None):
    ID: "les_trig", Title: "ත්‍රිකෝණමිතිය", Order: 5
    - Sub-lesson 1 (parent_lesson_id = "les_trig"):
        ID: "les_trig_01", Title: "ත්‍රිකෝණමිතික අනුපාත හා සර්වසාම්‍ය", Order: 1
    - Sub-lesson 2 (parent_lesson_id = "les_trig"):
        ID: "les_trig_02", Title: "ත්‍රිකෝණමිතික සමීකරණ හා සාමාන්‍ය විසඳුම්", Order: 2
    - Sub-lesson 3 (parent_lesson_id = "les_trig"):
        ID: "les_trig_03", Title: "ත්‍රිකෝණ විසඳීම (Sine / Cosine නීති)", Order: 3

මේ සඳහා `parent_lesson_id` ස්වයං-සම්බන්ධී විදේශ යතුර (Self-referential Foreign Key)
භාවිතා කර ඇති අතර, CASCADE delete මගින් ප්‍රධාන පාඩම මකා දැමුවහොත් ඒ යටතේ ඇති
සියලු උප-පාඩම්ද ආරක්ෂිතව ඉවත් කෙරේ.
===============================================================================
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.question import Question
    from app.models.study_note import StudyNote


class SyllabusLesson(Base):
    """
    Syllabus Lesson model representing both Main Units and Sub-lessons.

    Attributes:
        id: Unique UUID identifier for the lesson.
        subject_id: Foreign key to the parent `Subject` UUID.
        parent_lesson_id: Self-referential FK to `syllabus_lessons.id`.
                          - None: Indicates a top-level Unit / Main Lesson.
                          - Not None: Indicates a Sub-lesson belonging to a parent unit.
        title: Lesson title in English.
        sinhala_title: Lesson title in Sinhala (ප්‍රධාන භාෂාවෙන් පාඩමේ නම).
        order_index: Sort order within the subject or within the parent unit (1, 2, 3...).
        description: Detailed summary or learning outcomes of this lesson.
        question_count: Denormalized/cached count of associated questions.
        premium_count: Denormalized/cached count of premium questions.
        created_at: Timestamp when record was inserted (UTC).
        updated_at: Timestamp when record was last modified (UTC).
    """

    __tablename__ = "syllabus_lessons"

    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Hierarchical Sub-lessons (ස්වයං-සම්බන්ධිත උප පාඩම් ධුරාවලිය)
    # -------------------------------------------------------------------------
    # parent_lesson_id: ප්‍රධාන Unit/පාඩම සඳහා None වේ. උප-පාඩමක් (Sub-lesson/Subtopic) නම් අදාළ
    # ප්‍රධාන පාඩමේ id එක මෙහි විදේශ යතුරක් (Foreign Key) ලෙස ගබඩා වේ.
    # Enables Units -> Sub-lessons grouping (e.g. 05. ත්‍රිකෝණමිතිය -> 5.1 අනුපාත).
    parent_lesson_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        ForeignKey("syllabus_lessons.id", ondelete="CASCADE"),
        nullable=True,
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

    # -------------------------------------------------------------------------
    # SQLAlchemy ORM Relationships
    # -------------------------------------------------------------------------
    # 1. Subject relationship (පාඩම අයත් විෂය)
    subject: Mapped["Subject"] = relationship("Subject", back_populates="lessons")

    # 2. Self-referential hierarchy relationships (ප්‍රධාන පාඩම සහ උප පාඩම් අතර සබඳතාව)
    # parent_lesson: උප පාඩමක ප්‍රධාන පාඩම වෙත යොමු කෙරේ (Many-to-One self reference)
    parent_lesson: Mapped[Optional["SyllabusLesson"]] = relationship(
        "SyllabusLesson",
        remote_side=[id],
        back_populates="sub_lessons",
    )
    # sub_lessons: ප්‍රධාන පාඩමකට අදාළ සියලු උප පාඩම් ලැයිස්තුව (One-to-Many self reference)
    sub_lessons: Mapped[List["SyllabusLesson"]] = relationship(
        "SyllabusLesson",
        back_populates="parent_lesson",
        cascade="all, delete-orphan",
        order_by="SyllabusLesson.order_index",
    )

    # 3. Content relationships (පාඩමට අදාළ ප්‍රශ්න සහ Study Notes)
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="lesson",
    )
    study_notes: Mapped[List["StudyNote"]] = relationship(
        "StudyNote",
        back_populates="lesson",
    )

    def __repr__(self) -> str:
        parent_info = f", parent='{self.parent_lesson_id}'" if self.parent_lesson_id else ""
        return (
            f"<SyllabusLesson(id='{self.id}', title='{self.title}', "
            f"subject_id='{self.subject_id}'{parent_info})>"
        )

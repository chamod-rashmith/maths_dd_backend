"""
SQLAlchemy 2.0 ORM model for Student Academic Profiles (Domain 1).

===============================================================================
සිසුන්ගේ ශාස්ත්‍රීය පැතිකඩ සාමාන්‍යකරණය (Student Profiles Normalization):
-------------------------------------------------------------------------------
1NF/3NF මූලධර්ම අනුව, සාමාන්‍ය පරිශීලක අනන්‍යතාවය (User Identity & Auth) සහ
A/L විභාගයට අදාළ ශාස්ත්‍රීය දත්ත (Academic Exam Metadata) වෙන් කර ඇත.

ප්‍රධාන ක්ෂේත්‍ර (Core Normalized Fields):
- `user_id`: PK & FK to `users.uid` (One-to-One Cascade relationship).
- `exam_year`: ඉලක්කගත උසස් පෙළ විභාග වර්ෂය (Target A/L Year - 2025, 2026, 2027, etc.).
- `attempt_number`: විභාග වාරය (Exam Attempt: 1 = 1st shy, 2 = 2nd shy, 3 = 3rd shy).
- `exam_district_id`: විශ්වවිද්‍යාල Z-Score ගණනය කරන නිල විභාග දිස්ත්‍රික්කය
  (Official Z-Score calculation district FK to `districts.id`).
- `school_name`: පාසල (School attended).
- `stream`: විෂය ධාරාව (PHYSICAL_SCIENCE, BIO_SCIENCE, etc.).
- `medium`: මාධ්‍යය (SINHALA, ENGLISH, TAMIL).
===============================================================================
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.district import District
    from app.models.user import User


class StudentProfile(Base):
    """
    Dedicated 1-to-1 extension entity for student academic profile attributes.

    Attributes:
        user_id: Primary key and foreign key to `users.uid`.
        exam_year: Target G.C.E. A/L exam year (2025-2040).
        attempt_number: Sitting attempt (1, 2, or 3).
        exam_district_id: Official district for Z-Score rank and cutoff.
        school_name: Name of school or private candidate.
        stream: Study stream (PHYSICAL_SCIENCE, BIO_SCIENCE, etc.).
        medium: Instruction/exam medium (SINHALA, ENGLISH, TAMIL).
        created_at: Record creation timestamp in UTC.
        updated_at: Record last modification timestamp in UTC.
    """

    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint(
            "attempt_number IS NULL OR (attempt_number >= 1 AND attempt_number <= 3)",
            name="chk_student_profiles_attempt_number",
        ),
        CheckConstraint(
            "exam_year IS NULL OR (exam_year >= 2020 AND exam_year <= 2040)",
            name="chk_student_profiles_exam_year",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Primary Key and Foreign Key linking directly to users.uid",
    )

    # -------------------------------------------------------------------------
    # Target Examination Metadata (ඉලක්කගත A/L විභාග විස්තර)
    # -------------------------------------------------------------------------
    exam_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Target G.C.E. A/L Examination Year (e.g. 2025, 2026, 2027)",
    )

    attempt_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Exam sitting attempt: 1 (1st shy), 2 (2nd shy), 3 (3rd shy)",
    )

    # -------------------------------------------------------------------------
    # Regional Z-Score District (Z-Score දිස්ත්‍රික්කය)
    # -------------------------------------------------------------------------
    exam_district_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("districts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Official Sri Lankan District (1-25) used for Z-Score calculation",
    )

    school_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of attending school or tuition institute",
    )

    stream: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="G.C.E. A/L Subject Stream (e.g. PHYSICAL_SCIENCE, BIO_SCIENCE)",
    )

    medium: Mapped[Optional[str]] = mapped_column(
        String(20),
        default="SINHALA",
        server_default=text("'SINHALA'"),
        nullable=True,
        comment="Examination medium: SINHALA, ENGLISH, or TAMIL",
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

    # -------------------------------------------------------------------------
    # ORM Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship(
        "User",
        back_populates="student_profile",
    )

    exam_district: Mapped[Optional["District"]] = relationship(
        "District",
        foreign_keys=[exam_district_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<StudentProfile(user_id='{self.user_id}', exam_year={self.exam_year}, "
            f"attempt={self.attempt_number}, exam_district_id={self.exam_district_id})>"
        )

"""
SQLAlchemy 2.0 ORM models for Study Notes, Study Note Votes, and Study Note Bookmarks.
Includes soft-delete support (`is_deleted`) to preserve curriculum references,
and strict 3NF normalized tables for per-user votes (`study_note_votes`) and bookmarks (`study_note_bookmarks`).
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.lesson import SyllabusLesson
    from app.models.user import User


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
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    upvote_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="සටහනට ලැබී ඇති සමස්ත Upvotes (+1) ගණන",
    )
    downvote_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="සටහනට ලැබී ඇති සමස්ත Downvotes (-1) ගණන",
    )
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
        Index("idx_study_notes_subject_lesson", "subject_id", "lesson_id", "order_index", "is_deleted"),
        Index("idx_study_notes_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<StudyNote(id='{self.id}', title='{self.title}', subject_id='{self.subject_id}')>"


class StudyNoteVote(Base):
    """
    ශිෂ්‍යයෙකු විසින් Theory සටහනකට ලබා දුන් මනාපය (Normalized 3NF Vote Record).
    Reddit/StackOverflow ආකෘතියට අනුව:
      `1`  = Upvote (Like)
      `-1` = Downvote (Dislike)
    මනාපය ඉවත් කළ විට (`0`) මෙම වගුවෙන් අදාළ පේළිය ඉවත් (DELETE) කරනු ලැබේ.
    """

    __tablename__ = "study_note_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "note_id", name="uq_study_note_votes_user_note"),
        CheckConstraint("vote_type IN (1, -1)", name="ck_study_note_votes_valid_type"),
        Index("idx_study_note_votes_user_note", "user_id", "note_id"),
        Index("idx_study_note_votes_note_type", "note_id", "vote_type"),
    )

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="අනන්‍ය හැඳුනුම් අංකය ({user_id}_{note_id})",
    )
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )
    note_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("study_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Theory සටහනේ හැඳුනුම් අංකය",
    )
    vote_type: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="මනාප වර්ගය: 1 (Upvote) හෝ -1 (Downvote)",
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

    note: Mapped["StudyNote"] = relationship("StudyNote")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<StudyNoteVote(user='{self.user_id}', note='{self.note_id}', vote={self.vote_type})>"


class StudyNoteBookmark(Base):
    """
    ශිෂ්‍යයෙකු විසින් පසුව බැලීම සඳහා සුරකින ලද Theory සටහන් (Normalized 3NF Saved / Bookmarked Notes).
    Bookmark ඉවත් කළ විට මෙම වගුවෙන් අදාළ පේළිය ඉවත් (DELETE) කරනු ලැබේ.
    """

    __tablename__ = "study_note_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "note_id", name="uq_study_note_bookmarks_user_note"),
        Index("idx_study_note_bookmarks_user_note", "user_id", "note_id"),
        Index("idx_study_note_bookmarks_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="අනන්‍ය හැඳුනුම් අංකය ({user_id}_{note_id})",
    )
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )
    note_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("study_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Theory සටහනේ හැඳුනුම් අංකය",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    note: Mapped["StudyNote"] = relationship("StudyNote")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<StudyNoteBookmark(user='{self.user_id}', note='{self.note_id}')>"


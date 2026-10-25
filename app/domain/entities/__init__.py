"""
Pure Domain Entities (Framework-agnostic immutable dataclasses).
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class UserEntity:
    """Domain entity representing an authenticated user profile and telemetry stats."""

    uid: str
    email: str
    name: str
    telephone_no: Optional[str] = None
    role: str = "USER"
    avatar_url: Optional[str] = None
    school_name: Optional[str] = None
    district: Optional[str] = None
    stream: Optional[str] = None
    grade: Optional[str] = None
    attempt: Optional[str] = None
    is_premium: bool = False
    current_streak_days: int = 0
    longest_streak_days: int = 0
    total_solved_count: int = 0
    total_study_time_seconds: int = 0
    last_active_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class SubjectEntity:
    """Domain entity representing a curriculum subject."""

    id: str
    name: str
    code: str
    order_index: int = 1
    sinhala_name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class LessonEntity:
    """Domain entity representing a syllabus lesson unit."""

    id: str
    subject_id: str
    title: str
    order_index: int = 1
    sinhala_title: Optional[str] = None
    description: Optional[str] = None
    question_count: int = 0
    premium_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class QuestionSummaryEntity:
    """Domain entity representing a question summary in catalog listings."""

    id: str
    title: str
    subject_id: str
    type: str
    difficulty: str
    schedule: str
    source: str
    allocated_marks: int
    is_published: bool
    created_at: datetime
    subject_name: Optional[str] = None
    lesson_title: Optional[str] = None


@dataclass(frozen=True)
class QuestionWithSolutionEntity:
    """Domain entity representing a newly created question and its official marking scheme."""

    question: Dict[str, Any]
    marking_scheme: Dict[str, Any]


@dataclass(frozen=True)
class StudyNoteEntity:
    """Domain entity representing a study note."""

    id: str
    title: str
    subject_id: str
    content_text: str = ""
    description: Optional[str] = None
    lesson_id: Optional[str] = None
    pdf_url: Optional[str] = None
    is_premium: bool = False
    order_index: int = 0
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    subject_name: Optional[str] = None
    subject_sinhala_name: Optional[str] = None
    lesson_title: Optional[str] = None
    lesson_sinhala_title: Optional[str] = None

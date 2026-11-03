"""
Pydantic DTO schemas for Questions and Marking Schemes.
Enforces type-safe domain Enums for Type, Difficulty, Schedule, and Source,
lightweight Summary responses for catalog listings, dynamic Multi-Question Daily Challenge Pack schemas,
and on-demand Detail/Solution schemas.
Omits internal database timestamps for security and minimal bandwidth payload.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    QuestionDifficulty,
    QuestionSchedule,
    QuestionSource,
    QuestionType,
)


class QuestionCreate(BaseModel):
    """Request schema for creating or updating a mathematical question and its marking scheme."""

    id: Optional[str] = None
    custom_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[str] = None
    content_text: Optional[str] = ""
    content_url: Optional[str] = None
    solution_text: Optional[str] = ""
    solution_pdf_url: Optional[str] = None
    solution_title: str = "Official Marking Scheme"
    question_type: QuestionType = QuestionType.SHORT
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
    schedule: QuestionSchedule = QuestionSchedule.REGULAR
    source: QuestionSource = QuestionSource.PAST_PAPER
    source_details: Optional[str] = ""
    allocated_marks: int = 25
    is_premium: bool = False
    is_published: bool = True
    scheduled_date: Optional[str] = None
    day_number: Optional[int] = None


class QuestionSummaryResponse(BaseModel):
    """
    Lightweight summary representation of a question in catalog/lesson list views.
    Omits heavy problem content_text, solution payloads, and internal timestamps.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = ""
    subject_id: str
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    lesson_id: Optional[str] = None
    lesson_title: Optional[str] = None
    lesson_sinhala_title: Optional[str] = None
    content_type: str = "markdown"
    type: QuestionType
    difficulty: QuestionDifficulty
    schedule: QuestionSchedule = QuestionSchedule.REGULAR
    source: QuestionSource
    source_details: Optional[str] = ""
    allocated_marks: int = 25
    is_premium: bool = False
    is_published: bool = True
    scheduled_date: Optional[date] = None
    day_number: Optional[int] = None
    has_marking_scheme: bool = True


class MarkingSchemeResponse(BaseModel):
    """Detailed representation of a question's official marking scheme / worked solution."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    title: str = "Official Marking Scheme"
    content_text: Optional[str] = ""
    pdf_url: Optional[str] = None
    content_type: str = "markdown"
    total_marks: int = 25
    is_official: bool = True
    is_premium_only: bool = False
    order_index: int = 1


class QuestionDetailResponse(BaseModel):
    """
    Full detail representation of a single question, hydrated with inline LaTeX/Markdown
    or a short-lived signed Cloud Storage URL.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = ""
    subject_id: str
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    lesson_id: Optional[str] = None
    lesson_title: Optional[str] = None
    lesson_sinhala_title: Optional[str] = None
    content_text: Optional[str] = ""
    content_url: Optional[str] = None
    content_type: str = "markdown"
    type: QuestionType
    difficulty: QuestionDifficulty
    schedule: QuestionSchedule = QuestionSchedule.REGULAR
    source: QuestionSource
    source_details: Optional[str] = ""
    allocated_marks: int = 25
    is_premium: bool = False
    is_published: bool = True
    scheduled_date: Optional[date] = None
    day_number: Optional[int] = None
    has_marking_scheme: bool = True


class DailyChallengePackResponse(BaseModel):
    """
    Composite response returning the complete dynamic N-question challenge pack for a target day/date.
    Adaptable to any number of questions (e.g. 1, 4, or 8 questions for Marathon practice).
    """

    day_number: Optional[int] = None
    scheduled_date: Optional[date] = None
    total_questions: int = 0
    total_marks: int = 0
    questions: List[QuestionDetailResponse] = []


class DailySeriesDaySummaryResponse(BaseModel):
    """
    Lightweight summary of a single daily challenge in the Day 1..N series catalog.
    Enables students to browse all days chronologically and practice historical challenges.
    """

    day_number: int
    scheduled_date: Optional[date] = None
    title: str = ""
    total_questions: int = 0
    total_marks: int = 0
    is_unlocked: bool = True


class QuestionWithSolutionResponse(BaseModel):
    """Composite response returned upon creating or updating a question and its marking scheme."""

    question: Dict[str, Any]
    marking_scheme: Optional[Dict[str, Any]] = None

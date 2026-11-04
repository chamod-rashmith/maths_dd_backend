"""
Pydantic DTO schemas for Questions, Marking Schemes, Marking Steps, and Exam Papers.
Enforces type-safe domain Enums for Type, Difficulty, Schedule, and Source,
lightweight Summary responses for catalog listings, dynamic Multi-Question Daily Challenge Pack schemas,
and on-demand Detail/Solution schemas with 3NF step rubrics.
Omits internal database timestamps (created_at, updated_at, deleted_at) for security and minimal bandwidth payload.
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


class ExamPaperResponse(BaseModel):
    """විභාග ප්‍රශ්න පත්‍ර විස්තරය (A/L Exam Paper Catalog DTO)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="ප්‍රශ්න පත්‍රයේ ID")
    subject_id: str = Field(..., description="විෂය ID")
    type: str = Field("AL_GOVT", description="වර්ගය (AL_GOVT, MODEL, PROVINCIAL)")
    year: int = Field(..., description="විභාග වර්ෂය (e.g. 2023, 2024)")
    part: str = Field("PART_I", description="කොටස (PART_I, PART_II_A, PART_II_B, FULL)")
    title_si: str = Field(..., description="සිංහල මාතෘකාව")
    title_en: Optional[str] = Field(None, description="ඉංග්‍රීසි මාතෘකාව")
    source_pdf_url: Optional[str] = Field(None, description="නිල ප්‍රශ්න පත්‍ර PDF URL")


class MarkingSchemeStepResponse(BaseModel):
    """ලකුණු දීමේ පටිපාටියේ තනි පියවරක් (Step-by-Step Marking Rubric DTO)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="පියවරේ ID")
    step_number: int = Field(1, description="පියවර අංකය")
    step_type: str = Field("METHOD", description="ලකුණු වර්ගය (METHOD, ACCURACY, FINAL, BONUS)")
    description_si: str = Field(..., description="පියවරේ ගණිතමය විසඳුම (Sinhala + LaTeX)")
    allocated_marks: int = Field(1, description="හිමිවන ලකුණු ගණන")
    annotation: Optional[str] = Field(None, description="පරීක්ෂක සටහන් / විකල්ප ක්‍රම")
    order_index: int = Field(1, description="ප්‍රදර්ශන අනුපිළිවෙල")


class MarkingSchemeResponse(BaseModel):
    """Detailed representation of a question's official marking scheme / worked solution with 3NF step rubrics."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    title: str = "Official Marking Scheme"
    description_si: Optional[str] = None
    content_text: Optional[str] = ""
    pdf_url: Optional[str] = None
    content_type: str = "markdown"
    total_marks: int = 25
    is_official: bool = True
    is_premium_only: bool = False
    order_index: int = 1
    steps: List[MarkingSchemeStepResponse] = Field(default_factory=list, description="පියවරෙන් පියවර ලකුණු බෙදී යන ආකාරය")


class QuestionCreate(BaseModel):
    """Request schema for creating or updating a mathematical question and its marking scheme."""

    id: Optional[str] = None
    custom_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[str] = None
    exam_paper_id: Optional[str] = None
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
    exam_paper_id: Optional[str] = None
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
    exam_paper_id: Optional[str] = None
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

    day_number: int = 1
    challenge_title: str = "Daily Challenge Pack"
    scheduled_date: Optional[date] = None
    total_questions: int = 0
    total_marks: int = 0
    questions: List[QuestionDetailResponse] = []


class DailySeriesDaySummaryResponse(BaseModel):
    """
    Lightweight summary of a single daily challenge in the Day 1..N series catalog.
    Enables students to browse all days in reverse-chronological order (Tomorrow/Today first, older past days below).
    """

    day_number: int
    scheduled_date: Optional[date] = None
    title: str = ""
    total_questions: int = 0
    short_questions_count: int = 0
    essay_questions_count: int = 0
    total_marks: int = 0
    target_duration_seconds: int = 3600
    is_unlocked: bool = True
    unlocks_at: Optional[str] = None


class QuestionWithSolutionResponse(BaseModel):
    """Composite response returned upon creating or updating a question and its marking scheme."""

    question: Dict[str, Any]
    marking_scheme: Optional[Dict[str, Any]] = None

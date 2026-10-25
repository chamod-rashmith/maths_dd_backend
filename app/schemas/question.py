"""
Pydantic DTO schemas for Questions and Marking Schemes.
Enforces type-safe domain Enums for Type, Difficulty, Schedule, and Source.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.domain.enums import (
    QuestionDifficulty,
    QuestionType,
    QuestionSchedule,
    QuestionSource,
)


class QuestionCreate(BaseModel):
    """Request schema for creating a mathematical question and its marking scheme."""

    title: str = Field(..., min_length=1, max_length=255)
    custom_id: Optional[str] = None
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[str] = None
    content_text: str = Field(..., min_length=1)
    solution_text: str = Field(..., min_length=1)
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


class QuestionSummaryResponse(BaseModel):
    """Summary representation of a question in list/recent views."""

    id: str
    title: str
    subject_id: str
    type: QuestionType
    difficulty: QuestionDifficulty
    schedule: QuestionSchedule
    source: QuestionSource
    allocated_marks: int
    is_published: bool
    created_at: datetime
    subject_name: Optional[str] = None
    lesson_title: Optional[str] = None


class QuestionWithSolutionResponse(BaseModel):
    """Composite response returned upon creating a question and its marking scheme."""

    question: Dict[str, Any]
    marking_scheme: Dict[str, Any]

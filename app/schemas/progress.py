"""
Pydantic v2 schemas for Student Progress Tracking, Question Attempts, and Activity Heatmaps.
Enforces type safety and seamless camelCase serialization matching Flutter client models.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseProgressSchema(BaseModel):
    """Base schema configuring camelCase alias serialization and ORM mode."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class CompletedQuestionRecordSchema(BaseProgressSchema):
    """Schema representing a student's completed question attempt."""

    question_id: str
    title: str
    subject: str = "pureMaths"
    lesson_id: Optional[str] = None
    question_type: str = "short"
    is_daily_question: bool = False
    time_spent_seconds: int = 0
    target_duration_seconds: int = 0
    was_overtime: bool = False
    attempt_count: int = 1
    completed_date_key: str
    completed_at: datetime
    is_bookmarked: bool = False
    confidence: Optional[str] = None
    student_notes: Optional[str] = None


class DailyActivityBucketSchema(BaseProgressSchema):
    """Schema representing daily aggregated study metrics for activity heatmaps."""

    date_key: str
    questions_solved_count: int = 0
    total_time_spent_seconds: int = 0
    daily_challenge_completed: bool = False
    question_ids: List[str] = Field(default_factory=list)


class UserProgressSummaryResponse(BaseProgressSchema):
    """Full aggregated progress summary schema returned to Flutter mobile app."""

    completed_questions: Dict[str, CompletedQuestionRecordSchema] = Field(
        default_factory=dict
    )
    daily_activity: Dict[str, DailyActivityBucketSchema] = Field(
        default_factory=dict
    )
    solved_count_by_lesson: Dict[str, int] = Field(default_factory=dict)
    solved_count_by_subject: Dict[str, int] = Field(default_factory=dict)
    total_questions_solved: int = 0
    total_time_spent_seconds: int = 0
    current_streak_days: int = 0
    longest_streak_days: int = 0
    last_active_date_key: Optional[str] = None


class MarkQuestionCompletedRequest(BaseProgressSchema):
    """Request payload for recording or updating a question completion attempt."""

    question_id: str
    time_spent_seconds: int = 0
    target_duration_seconds: int = 0
    was_overtime: bool = False
    is_daily_question: bool = False
    confidence: Optional[str] = None
    student_notes: Optional[str] = None
    is_bookmarked: Optional[bool] = None


class ToggleBookmarkRequest(BaseProgressSchema):
    """Request payload for starring/bookmarking a question."""

    is_bookmarked: bool

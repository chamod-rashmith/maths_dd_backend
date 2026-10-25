"""
Pydantic DTO schemas for Curriculum (Subjects & Syllabus Lessons).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    """Request schema to create or update a curriculum subject."""

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    sinhala_name: Optional[str] = ""
    code: str = Field(..., min_length=1, max_length=50)
    order_index: int = 1
    description: Optional[str] = ""


class SubjectResponse(BaseModel):
    """Response schema for a curriculum subject."""

    id: str
    name: str
    sinhala_name: Optional[str] = None
    code: str
    order_index: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LessonCreate(BaseModel):
    """Request schema to create or update a syllabus lesson."""

    id: Optional[str] = None
    subject_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    sinhala_title: Optional[str] = ""
    order_index: int = 1
    description: Optional[str] = ""


class LessonResponse(BaseModel):
    """Response schema for a syllabus lesson."""

    id: str
    subject_id: str
    title: str
    sinhala_title: Optional[str] = None
    order_index: int
    description: Optional[str] = None
    question_count: Optional[int] = 0
    premium_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

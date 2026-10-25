"""
Pydantic DTO schemas for Study Notes.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudyNoteCreateOrUpdate(BaseModel):
    """Request schema for creating or updating a study note."""

    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[str] = None
    content_text: Optional[str] = ""
    description: Optional[str] = ""
    pdf_url: Optional[str] = None
    is_premium: bool = False
    order_index: int = 0
    author: Optional[str] = ""


class StudyNoteResponse(BaseModel):
    """Response schema for a study note."""

    id: str
    title: str
    description: Optional[str] = None
    subject_id: str
    lesson_id: Optional[str] = None
    content_text: str
    pdf_url: Optional[str] = None
    is_premium: bool
    order_index: int
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    subject_name: Optional[str] = None
    subject_sinhala_name: Optional[str] = None
    lesson_title: Optional[str] = None
    lesson_sinhala_title: Optional[str] = None

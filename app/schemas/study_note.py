"""
Pydantic DTO schemas for Study Notes.
Enforces mutual exclusivity: either `pdf_url` OR `content_text` (never both).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator

from app.domain.exceptions import ValidationDomainError


class StudyNoteCreateOrUpdate(BaseModel):
    """Request schema for creating or updating a study note."""

    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[str] = None
    content_text: Optional[str] = None
    description: Optional[str] = ""
    pdf_url: Optional[str] = None
    is_premium: bool = False
    order_index: int = 0
    author: Optional[str] = ""

    @model_validator(mode="after")
    def validate_content_mutual_exclusivity(self) -> "StudyNoteCreateOrUpdate":
        has_pdf = bool(self.pdf_url and self.pdf_url.strip())
        has_text = bool(self.content_text and self.content_text.strip())

        if has_pdf and has_text:
            raise ValidationDomainError(
                "A study note must have either 'pdf_url' OR 'content_text', not both."
            )
        if not has_pdf and not has_text:
            raise ValidationDomainError(
                "A study note must have at least one content payload ('pdf_url' or 'content_text')."
            )
        return self


class StudyNoteResponse(BaseModel):
    """Response schema for a study note. Guarantees returning ONLY pdf_url OR content_text."""

    id: str
    title: str
    description: Optional[str] = None
    subject_id: str
    lesson_id: Optional[str] = None
    content_text: Optional[str] = None
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

    @model_validator(mode="before")
    @classmethod
    def enforce_single_content(cls, data: dict) -> dict:
        """Enforces that return payload has ONLY pdf_url OR content_text (never both)."""
        if isinstance(data, dict):
            item = dict(data)
            has_pdf = bool(item.get("pdf_url") and str(item.get("pdf_url")).strip())

            if has_pdf:
                item["pdf_url"] = str(item["pdf_url"]).strip()
                item["content_text"] = None
            else:
                item["pdf_url"] = None
                item["content_text"] = item.get("content_text") or ""
            return item
        return data

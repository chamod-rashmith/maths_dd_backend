"""
Pydantic DTO schemas for Study Notes.
Enforces lightweight Summary for listings and mutually exclusive Content for detail view.
Supports cloud storage paths with on-demand short-lived signed URLs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator

from app.domain.exceptions import ValidationDomainError


class StudyNoteCreateOrUpdate(BaseModel):
    """
    Request schema for creating or updating a study note.
    Supports either storage path/url (pdf_path / pdf_url) OR markdown (content_text).
    """

    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: Optional[str] = None
    content_text: Optional[str] = None
    description: Optional[str] = ""
    # Can accept either storage relative path (e.g. 'notes/pure/induction.pdf') or full url
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
                "A study note must have either 'pdf_url' (storage path) OR 'content_text', not both."
            )
        if not has_pdf and not has_text:
            raise ValidationDomainError(
                "A study note must have at least one content payload ('pdf_url' or 'content_text')."
            )
        return self


class StudyNoteSummaryResponse(BaseModel):
    """
    Lightweight summary for Study Notes Catalog / List view.
    Excludes heavy content_text and pdf_url payloads for maximum bandwidth and UI performance.
    """

    id: str
    title: str
    description: Optional[str] = None
    subject_id: str
    lesson_id: Optional[str] = None
    content_type: str = "markdown"  # 'pdf' or 'markdown'
    is_premium: bool = False
    order_index: int = 0
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    subject_name: Optional[str] = None
    subject_sinhala_name: Optional[str] = None
    lesson_title: Optional[str] = None
    lesson_sinhala_title: Optional[str] = None


class StudyNoteDetailResponse(BaseModel):
    """
    Detailed representation of a single Study Note.
    Loaded on-demand when user opens the note.
    Guarantees ONLY signed pdf_url OR content_text (never both).
    """

    id: str
    title: str
    description: Optional[str] = None
    subject_id: str
    lesson_id: Optional[str] = None
    content_text: Optional[str] = None
    pdf_url: Optional[str] = None
    content_type: str = "markdown"  # 'pdf' or 'markdown'
    is_premium: bool = False
    order_index: int = 0
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
        """Enforces that detail payload contains ONLY signed pdf_url OR content_text (never both)."""
        if isinstance(data, dict):
            item = dict(data)
            has_pdf = bool(item.get("pdf_url") and str(item.get("pdf_url")).strip())

            if has_pdf:
                item["pdf_url"] = str(item["pdf_url"]).strip()
                item["content_text"] = None
                item["content_type"] = "pdf"
            else:
                item["pdf_url"] = None
                item["content_text"] = item.get("content_text") or ""
                item["content_type"] = "markdown"
            return item
        return data

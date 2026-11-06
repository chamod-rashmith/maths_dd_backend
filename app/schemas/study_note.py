"""
Pydantic DTO schemas for Study Notes.
Enforces lightweight Summary for listings, DRY inheritance for detail view with mutually exclusive Content,
and strict server-side Premium Gating (`is_locked`) without leaking full notes to free users.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ContentType
from app.domain.exceptions import ValidationDomainError


class StudyNoteCreateOrUpdate(BaseModel):
    """
    Request schema for creating or updating a study note.
    Supports either storage path/url (pdf_url) OR markdown (content_text).
    """

    id: str | None = None
    title: str = Field(..., min_length=1, max_length=255)
    subject_id: str = Field(..., min_length=1, max_length=100)
    lesson_id: str | None = None
    content_text: str | None = None
    description: str | None = ""
    pdf_url: str | None = None
    is_premium: bool = False
    order_index: int = 0
    author: str | None = ""

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
    Excludes heavy content_text and pdf_url payloads and internal timestamps.
    `is_locked` indicates whether this note is gated behind premium subscription for the current user.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    subject_id: str
    lesson_id: str | None = None
    content_type: ContentType | str = ContentType.MARKDOWN  # 'pdf' or 'markdown'
    is_premium: bool = False
    is_locked: bool = False
    order_index: int = 0
    author: str | None = None
    subject_name: str | None = None
    subject_sinhala_name: str | None = None
    lesson_title: str | None = None
    lesson_sinhala_title: str | None = None


class StudyNoteDetailResponse(StudyNoteSummaryResponse):
    """
    Detailed representation of a single Study Note, inheriting all summary fields.
    Loaded on-demand when user opens the note.
    Guarantees ONLY signed pdf_url OR content_text (never both).
    Delivered ONLY to authenticated users with valid permissions.
    """

    content_text: str | None = None
    pdf_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def enforce_single_content(cls, data: dict) -> dict:
        """Enforces that detail payload contains ONLY signed pdf_url OR content_text (never both)."""
        if isinstance(data, dict):
            raw_pdf = data.get("pdf_url")
            raw_text = data.get("content_text")
            has_pdf = bool(raw_pdf and str(raw_pdf).strip())
            has_text = bool(raw_text and str(raw_text).strip())

            if has_pdf:
                data["content_text"] = None
                if not data.get("content_type"):
                    data["content_type"] = ContentType.PDF.value
            elif not has_text:
                data["content_text"] = None
        return data

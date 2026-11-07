"""
Pydantic DTO schemas for Study Notes.
Enforces lightweight Summary for listings, DRY inheritance for detail view with mutually exclusive Content,
and strict server-side Premium Gating (`is_locked`) without leaking full notes to free users.
Includes Reddit/StackOverflow-style integer voting (`1`, `-1`, `0`) and bookmark state (`is_bookmarked`).
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    Lightweight summary for Study Notes Catalog / List view (`GET /api/v1/study-notes`).
    Excludes heavy `content_text` and `pdf_url` payloads and internal timestamps.

    ===========================================================================
    FRONTEND DEVELOPER GUIDE (ලැයිස්තු පෙනුම / Card UI සඳහා උපදෙස්):
    ---------------------------------------------------------------------------
    1. `is_locked` (bool):
       - `true`  -> Show Premium Lock icon 🔒 (User cannot open note until subscribed).
       - `false` -> Unlocked, user can open note.
    2. `upvote_count` (int) & `downvote_count` (int):
       - Total likes (👍) and dislikes (👎) on this note across all students.
    3. `user_vote` (int - Reddit/StackOverflow style):
       - `1`  -> Current logged-in user has UPVOTED (Liked 👍) this note (highlight Like button).
       - `-1` -> Current logged-in user has DOWNVOTED (Disliked 👎) this note (highlight Dislike button).
       - `0`  -> Current logged-in user has NOT voted on this note (neutral state).
    4. `is_bookmarked` (bool):
       - `true`  -> Current logged-in user has SAVED (Bookmarked 🔖) this note (highlight Bookmark icon).
       - `false` -> Not bookmarked by current user.
    ===========================================================================
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
    author: str | None = None
    subject_sinhala_name: str | None = None
    lesson_sinhala_title: str | None = None

    # --- Voting & Bookmarking State for Frontend UI ---
    upvote_count: int = Field(
        default=0,
        ge=0,
        description="Total number of Upvotes (Likes 👍) received by this study note.",
    )
    downvote_count: int = Field(
        default=0,
        ge=0,
        description="Total number of Downvotes (Dislikes 👎) received by this study note.",
    )
    user_vote: Literal[-1, 0, 1] = Field(
        default=0,
        description=(
            "Current logged-in user's vote status (Reddit/StackOverflow style): "
            "`1` = Upvoted (Liked 👍), `-1` = Downvoted (Disliked 👎), `0` = No vote (Neutral)."
        ),
    )
    is_bookmarked: bool = Field(
        default=False,
        description=(
            "Whether the current logged-in user has saved/bookmarked (🔖) this note (`true` = Saved, `false` = Not saved)."
        ),
    )

    @field_validator("upvote_count", "downvote_count", "user_vote", mode="before")
    @classmethod
    def coerce_null_int_to_zero(cls, v: int | None) -> int:
        return 0 if v is None else int(v)

    @field_validator("is_bookmarked", mode="before")
    @classmethod
    def coerce_null_bool_to_false(cls, v: bool | None) -> bool:
        return bool(v)


class StudyNoteDetailResponse(StudyNoteSummaryResponse):
    """
    Detailed representation of a single Study Note (`GET /api/v1/study-notes/{note_id}`).
    Inherits all summary fields (including `upvote_count`, `downvote_count`, `user_vote`, `is_bookmarked`).
    Loaded on-demand when user opens the note.
    Guarantees ONLY signed `pdf_url` OR `content_text` (never both).
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


class StudyNoteVoteRequest(BaseModel):
    """
    Request payload for voting on a study note (`POST /api/v1/study-notes/{note_id}/vote`).

    FRONTEND USAGE GUIDE:
    - User clicks Like (👍) when `user_vote != 1`      -> Send `{"vote": 1}`
    - User clicks Like (👍) again when `user_vote == 1` -> Send `{"vote": 0}` (removes upvote)
    - User clicks Dislike (👎) when `user_vote != -1`   -> Send `{"vote": -1}`
    - User clicks Dislike (👎) again when `user_vote == -1` -> Send `{"vote": 0}` (removes downvote)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"vote": 1},
                {"vote": -1},
                {"vote": 0},
            ]
        }
    )

    vote: Literal[-1, 0, 1] = Field(
        ...,
        description=(
            "Vote integer value: `1` = Upvote (Like 👍), `-1` = Downvote (Dislike 👎), "
            "`0` = Remove existing vote (Reset to neutral)."
        ),
    )


class StudyNoteVoteResponse(BaseModel):
    """
    Response returned after casting or removing a vote on a study note.
    Frontend can directly use `user_vote`, `upvote_count`, and `downvote_count` to update the UI card state.
    """

    status: str = Field(default="success", description="Operation status ('success')")
    note_id: str = Field(..., description="ID of the study note that was voted on")
    user_vote: Literal[-1, 0, 1] = Field(
        ...,
        description="Updated vote state for current user: `1` (Upvoted), `-1` (Downvoted), `0` (No vote)",
    )
    upvote_count: int = Field(default=0, ge=0, description="Updated total upvotes (+1) count")
    downvote_count: int = Field(default=0, ge=0, description="Updated total downvotes (-1) count")


class StudyNoteBookmarkRequest(BaseModel):
    """
    Optional request payload for bookmarking/unbookmarking a study note (`POST /api/v1/study-notes/{note_id}/bookmark`).

    FRONTEND USAGE GUIDE:
    - Option A (Explicit): Send `{"is_bookmarked": true}` to save, or `{"is_bookmarked": false}` to unsave.
    - Option B (Auto-Toggle): Send empty body `{}` (or no body at all) and backend will flip `true <-> false`!
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"is_bookmarked": True},
                {"is_bookmarked": False},
            ]
        }
    )

    is_bookmarked: bool | None = Field(
        default=None,
        description="Set `true` to bookmark (save), `false` to remove bookmark, or `null`/omit to toggle current state.",
    )


class StudyNoteBookmarkResponse(BaseModel):
    """
    Response returned after bookmarking or unbookmarking a study note.
    Frontend can directly update the bookmark icon using `is_bookmarked`.
    """

    status: str = Field(default="success", description="Operation status ('success')")
    note_id: str = Field(..., description="ID of the study note")
    is_bookmarked: bool = Field(
        ...,
        description="Updated bookmark status for current user (`true` = Saved 🔖, `false` = Removed)",
    )



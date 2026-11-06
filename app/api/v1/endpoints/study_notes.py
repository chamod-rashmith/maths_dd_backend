"""
FastAPI Router for v1 Study Notes operations with Zero-Leak Server-Side Access Gating,
Normalized 3NF Upvote/Downvote (`1`, `-1`, `0`), and Saved Bookmarks.
මෙම API මොඩියුලය මඟින් පාඩම් වලට අදාළ Theory සටහන්, Short Notes, Upvotes/Downvotes සහ Bookmarks කළමනාකරණය කරයි.

Security & Zero-Leak Principles:
1. Authentication Enforced:
   - All study notes endpoints require authenticated user credentials (`Depends(get_current_user)`).
   - Anonymous access is strictly rejected with HTTP 401 Unauthorized.
2. Server-Side Content Gating:
   - Free notes (`is_premium == False`) are accessible to all logged-in students.
   - Premium notes (`is_premium == True`) require an active premium subscription or ADMIN role.
   - If a free student requests a premium note, the content body and PDF URL are withheld entirely
     at the server boundary with HTTP 403 Forbidden, preventing any local client storage leaks.
3. Bandwidth Optimization & User Interaction State:
   - Catalog listings (`GET /study-notes`) return lightweight summaries inside a standardized
     `PaginatedResponse` envelope with `is_locked` badges, `upvote_count`, `downvote_count`,
     `user_vote` (`1`, `-1`, `0`), and `is_bookmarked` (`bool`) without transmitting heavy text or signed PDF download URLs.
"""

from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_admin_audit_service,
    get_study_note_service,
    require_admin_or_editor,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.domain.enums import AuditAction, AuditResourceType
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.common import DeleteResponse
from app.schemas.pagination import PaginatedResponse, PaginationMetadata
from app.schemas.study_note import (
    StudyNoteBookmarkRequest,
    StudyNoteBookmarkResponse,
    StudyNoteCreateOrUpdate,
    StudyNoteDetailResponse,
    StudyNoteSummaryResponse,
    StudyNoteVoteRequest,
    StudyNoteVoteResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.study_note_service import StudyNoteService

router = APIRouter(prefix="/study-notes", tags=["Study Notes v1"])


@router.get(
    "",
    response_model=PaginatedResponse[StudyNoteSummaryResponse],
    summary="List Study Notes Summaries",
    description=(
        "Returns a standardized paginated envelope of lightweight catalog card summaries for study notes matching filters. "
        "Evaluates the authenticated user's premium entitlement (`is_locked`), aggregate votes (`upvote_count`, `downvote_count`), "
        "and personal state (`user_vote`: 1/-1/0, `is_bookmarked`: true/false). "
        "Supports `bookmarked_only=true` to list only the user's saved study notes."
    ),
)
async def list_study_notes(
    subject_id: str | None = Query(None, description="Filter by subject ID or code (PMAT/AMAT)"),
    lesson_id: str | None = Query(None, description="Filter by syllabus lesson ID"),
    search: str | None = Query(None, description="Case-insensitive title or description keyword search"),
    bookmarked_only: bool = Query(False, description="Filter only study notes bookmarked (saved) by the current user"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: StudyNoteService = Depends(get_study_note_service),
) -> PaginatedResponse[StudyNoteSummaryResponse]:
    """
    ශිෂ්‍යයාට බැලීම සඳහා සටහන් ලැයිස්තුව ලබා දීම.
    ශිෂ්‍යයා සතුව Premium access නොමැති නම්, premium සටහන් සඳහා `is_locked = True` ලෙස ලකුණු කර එවයි.
    එමෙන්ම `upvote_count`, `downvote_count`, `user_vote` (`1`, `-1`, `0`) සහ `is_bookmarked` අගයන් ද එවයි.
    """
    user_id = current_user.get("uid")
    user_role = str(current_user.get("role", "")).upper()

    # Determine whether requesting user has active premium access
    is_premium_user = user_role == "ADMIN"
    if not is_premium_user and user_id:
        sub_repo = SubscriptionRepository(session)
        is_premium_user = await sub_repo.is_user_premium(user_id)

    raw_notes = await service.list_notes(
        subject_id=subject_id,
        lesson_id=lesson_id,
        search=search,
        limit=limit,
        offset=offset,
        user_id=user_id,
        bookmarked_only=bookmarked_only,
    )

    if isinstance(raw_notes, list):
        notes = raw_notes
        total = len(notes)
    else:
        notes = raw_notes["items"]
        total = int(raw_notes.get("total", len(notes)))

    results: list[StudyNoteSummaryResponse] = []
    for note in notes:
        note_dict = dict(note)
        note_dict["is_locked"] = bool(note_dict.get("is_premium") and not is_premium_user)
        results.append(StudyNoteSummaryResponse.model_validate(note_dict))

    return PaginatedResponse(
        items=results,
        pagination=PaginationMetadata.from_offset(
            total=total,
            limit=limit,
            offset=offset,
            items_count=len(results),
        ),
    )


@router.get(
    "/{note_id}",
    response_model=StudyNoteDetailResponse,
    summary="Get Study Note Content (Protected)",
    description=(
        "Fetches a single study note with its full content body or on-demand signed PDF URL. "
        "Zero-Leak Protection: If the note is marked `is_premium` and the user does NOT have an active subscription, "
        "returns HTTP 403 Forbidden with zero content payload leaked."
    ),
)
async def get_study_note(
    note_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: StudyNoteService = Depends(get_study_note_service),
) -> dict[str, Any]:
    """
    තනි Theory සටහනක සම්පූර්ණ අන්තර්ගතය ලබා ගැනීම.
    Premium සටහනක් නොමිලේ ලබා ගැනීමට උත්සාහ කළහොත් 403 Forbidden ලබා දී content කාන්දු වීම වළක්වයි.
    """
    user_id = current_user.get("uid")
    user_role = str(current_user.get("role", "")).upper()

    # 1. Fetch note with user interaction state (vote & bookmark)
    note = await service.get_note_by_id(note_id, user_id=user_id)

    # 2. Server-side zero-leak gating
    if note.get("is_premium"):
        is_premium_user = user_role == "ADMIN"
        if not is_premium_user and user_id:
            sub_repo = SubscriptionRepository(session)
            is_premium_user = await sub_repo.is_user_premium(user_id)

        if not is_premium_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="මෙම Theory සටහන අධ්‍යයනය කිරීමට Premium සාමාජිකත්වය අවශ්‍ය වේ (Premium subscription required)",
            )

    note["is_locked"] = False
    return note


@router.post(
    "/{note_id}/vote",
    response_model=StudyNoteVoteResponse,
    summary="Vote on Study Note (Upvote / Downvote / Remove)",
    description=(
        "Casts or removes a Reddit/StackOverflow-style integer vote on a study note.\n\n"
        "**Frontend Integration Guide:**\n"
        "- `{\"vote\": 1}`  -> **Upvote (Like 👍)**\n"
        "- `{\"vote\": -1}` -> **Downvote (Dislike 👎)**\n"
        "- `{\"vote\": 0}`  -> **Remove Vote (Neutral)** (Send `0` when the user taps an already-active Like/Dislike button to undo their vote).\n\n"
        "Returns updated `user_vote`, `upvote_count`, and `downvote_count` so the UI card can update immediately without refetching the list."
    ),
)
async def vote_study_note(
    note_id: str,
    body: StudyNoteVoteRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: StudyNoteService = Depends(get_study_note_service),
) -> dict[str, Any]:
    """
    Theory සටහනකට Upvote (`1`), Downvote (`-1`) ලබා දීම හෝ ලබා දුන් මනාපය ඉවත් කිරීම (`0`).
    Frontend එකේදී දැනටමත් Like කර ඇති බොත්තමක් නැවත එබූ විට `{"vote": 0}` එවීමෙන් Like එක ඉවත් කළ හැක.
    """
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identity missing.",
        )

    result = await service.vote_note(
        note_id=note_id,
        user_id=str(user_id),
        vote=body.vote,
    )
    await session.commit()
    return result


@router.post(
    "/{note_id}/bookmark",
    response_model=StudyNoteBookmarkResponse,
    summary="Bookmark or Unbookmark Study Note (Save)",
    description=(
        "Saves (bookmarks 🔖) or removes a study note from the user's saved notes.\n\n"
        "**Frontend Integration Guide:**\n"
        "- **Explicit Mode:** Send `{\"is_bookmarked\": true}` to save, or `{\"is_bookmarked\": false}` to remove.\n"
        "- **Auto-Toggle Mode:** Send an empty request body (or `{}`) to automatically flip `true <-> false`.\n"
        "- **Saved Notes Tab:** Call `GET /api/v1/study-notes?bookmarked_only=true` to list only the user's bookmarked notes."
    ),
)
async def toggle_study_note_bookmark(
    note_id: str,
    body: StudyNoteBookmarkRequest | None = Body(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: StudyNoteService = Depends(get_study_note_service),
) -> dict[str, Any]:
    """
    Theory සටහනක් පසුව බැලීම සඳහා Save (Bookmark) කිරීම හෝ ඉවත් කිරීම.
    Frontend එකෙන් body එකක් නොයවා කෙලින්ම POST කළත් ස්වයංක්‍රීයව Toggle (`true <-> false`) වේ.
    """
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identity missing.",
        )

    desired_state = body.is_bookmarked if body is not None else None
    result = await service.toggle_bookmark(
        note_id=note_id,
        user_id=str(user_id),
        is_bookmarked=desired_state,
    )
    await session.commit()
    return result


@router.post(
    "",
    response_model=StudyNoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Update Study Note (Admin)",
    description="Creates or updates a study note (requires ADMIN or EDITOR role). Records an immutable Ring 4 audit log.",
)
async def create_or_update_study_note(
    body: StudyNoteCreateOrUpdate,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: StudyNoteService = Depends(get_study_note_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Creates or updates a study note."""
    result = await service.upsert_note(body)
    note_id = (result.get("id") if isinstance(result, dict) else None) or body.id
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.STUDY_NOTE_UPSERTED.value,
        resource_type=AuditResourceType.STUDY_NOTE.value,
        resource_id=str(note_id) if note_id else None,
        request=request,
        details={
            "title": body.title,
            "subject_id": body.subject_id,
            "is_premium": body.is_premium,
        },
    )
    return result


@router.delete(
    "/{note_id}",
    response_model=DeleteResponse,
    summary="Soft-Delete Study Note (Admin)",
    description="Soft-deletes a study note by ID (requires ADMIN or EDITOR role). Records an immutable Ring 4 audit log.",
)
async def delete_study_note(
    note_id: str,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: StudyNoteService = Depends(get_study_note_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Deletes a study note by ID."""
    result = await service.delete_note(note_id)
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.STUDY_NOTE_DELETED.value,
        resource_type=AuditResourceType.STUDY_NOTE.value,
        resource_id=note_id,
        request=request,
    )
    return result


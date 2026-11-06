"""
FastAPI Router for v1 Study Notes operations with Zero-Leak Server-Side Access Gating.
මෙම API මොඩියුලය මඟින් පාඩම් වලට අදාළ Theory සටහන් සහ Short Notes නිකුත් කිරීම කළමනාකරණය කරයි.

Security & Zero-Leak Principles:
1. Authentication Enforced:
   - All study notes endpoints require authenticated user credentials (`Depends(get_current_user)`).
   - Anonymous access is strictly rejected with HTTP 401 Unauthorized.
2. Server-Side Content Gating:
   - Free notes (`is_premium == False`) are accessible to all logged-in students.
   - Premium notes (`is_premium == True`) require an active premium subscription or ADMIN role.
   - If a free student requests a premium note, the content body and PDF URL are withheld entirely
     at the server boundary with HTTP 403 Forbidden, preventing any local client storage leaks.
3. Bandwidth Optimization:
   - Catalog listings (`GET /study-notes`) return lightweight summaries with `is_locked` badges
     without transmitting heavy text or signed PDF download URLs.
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_study_note_service, require_admin_or_editor
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.study_note import (
    StudyNoteCreateOrUpdate,
    StudyNoteDetailResponse,
    StudyNoteSummaryResponse,
)
from app.services.study_note_service import StudyNoteService

router = APIRouter(prefix="/study-notes", tags=["Study Notes v1"])


@router.get(
    "",
    response_model=Union[
        PaginatedResponse[StudyNoteSummaryResponse], List[StudyNoteSummaryResponse]
    ],
    summary="List Study Notes Summaries",
    description=(
        "Returns lightweight catalog card summaries for study notes matching filters. "
        "Evaluates the authenticated user's premium entitlement to set the `is_locked` flag for UI lock badges. "
        "Does NOT transmit heavy markdown content or signed PDF URLs."
    ),
)
async def list_study_notes(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID or code (PMAT/AMAT)"),
    lesson_id: Optional[str] = Query(None, description="Filter by syllabus lesson ID"),
    search: Optional[str] = Query(None, description="Case-insensitive title or description keyword search"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """
    ශිෂ්‍යයාට බැලීම සඳහා සටහන් ලැයිස්තුව ලබා දීම.
    ශිෂ්‍යයා සතුව Premium access නොමැති නම්, premium සටහන් සඳහා `is_locked = True` ලෙස ලකුණු කර එවයි.
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
    )

    # Attach is_locked badge state per card
    if isinstance(raw_notes, list):
        notes = raw_notes
        results = []
    else:
        notes = raw_notes["items"]
        results = []

    for note in notes:
        note_dict = dict(note)
        note_dict["is_locked"] = bool(note_dict.get("is_premium") and not is_premium_user)
        results.append(note_dict)

    if isinstance(raw_notes, list):
        return results

    page = (offset // limit) + 1
    return {
        "items": results,
        "pagination": {
            "page": page,
            "page_size": limit,
            "total": raw_notes["total"],
            "has_next": offset + len(results) < raw_notes["total"],
        },
    }


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
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """
    තනි Theory සටහනක සම්පූර්ණ අන්තර්ගතය ලබා ගැනීම.
    Premium සටහනක් නොමිලේ ලබා ගැනීමට උත්සාහ කළහොත් 403 Forbidden ලබා දී content කාන්දු වීම වළක්වයි.
    """
    user_id = current_user.get("uid")
    user_role = str(current_user.get("role", "")).upper()

    # 1. Fetch note
    note = await service.get_note_by_id(note_id)

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
    "",
    response_model=StudyNoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Update Study Note (Admin)",
    description="Creates or updates a study note (requires ADMIN or EDITOR role).",
)
async def create_or_update_study_note(
    body: StudyNoteCreateOrUpdate,
    _admin: Dict[str, Any] = Depends(require_admin_or_editor),
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """Creates or updates a study note."""
    return await service.upsert_note(body)


@router.delete(
    "/{note_id}",
    summary="Soft-Delete Study Note (Admin)",
    description="Soft-deletes a study note by ID (requires ADMIN or EDITOR role).",
)
async def delete_study_note(
    note_id: str,
    _admin: Dict[str, Any] = Depends(require_admin_or_editor),
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """Deletes a study note by ID."""
    return await service.delete_note(note_id)

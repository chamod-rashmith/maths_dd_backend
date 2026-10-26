"""
FastAPI Router for v1 Study Notes operations.
List returns lightweight StudyNoteSummaryResponse (no heavy text).
Detail endpoint returns full StudyNoteDetailResponse (on-demand loading).
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_study_note_service, require_admin_or_editor
from app.schemas.study_note import (
    StudyNoteCreateOrUpdate,
    StudyNoteDetailResponse,
    StudyNoteSummaryResponse,
)
from app.services.study_note_service import StudyNoteService

router = APIRouter(prefix="/study-notes", tags=["Study Notes v1"])


@router.get("", response_model=List[StudyNoteSummaryResponse])
async def list_study_notes(
    subject_id: Optional[str] = Query(None),
    lesson_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: StudyNoteService = Depends(get_study_note_service),
) -> List[Dict[str, Any]]:
    """
    Lists study notes as lightweight summaries for catalog cards.
    Does NOT return heavy content_text or pdf_url payloads.
    """
    return await service.list_notes(
        subject_id=subject_id,
        lesson_id=lesson_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{note_id}", response_model=StudyNoteDetailResponse)
async def get_study_note(
    note_id: str,
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """
    Fetches a single study note with its full content body or PDF URL on-demand.
    Guarantees returning ONLY pdf_url OR content_text.
    """
    return await service.get_note_by_id(note_id)


@router.post(
    "",
    response_model=StudyNoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_study_note(
    body: StudyNoteCreateOrUpdate,
    _admin: Dict[str, Any] = Depends(require_admin_or_editor),
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """Creates or updates a study note (requires ADMIN or EDITOR role)."""
    return await service.upsert_note(body)


@router.delete("/{note_id}")
async def delete_study_note(
    note_id: str,
    _admin: Dict[str, Any] = Depends(require_admin_or_editor),
    service: StudyNoteService = Depends(get_study_note_service),
) -> Dict[str, Any]:
    """Deletes a study note by ID (requires ADMIN or EDITOR role)."""
    return await service.delete_note(note_id)

"""
FastAPI Router for v1 Study Notes operations.
"""

from typing import List, Optional, Dict, Any
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.study_note_repository import StudyNoteRepository
from app.schemas.study_note import StudyNoteCreateOrUpdate, StudyNoteResponse

router = APIRouter(prefix="/study-notes", tags=["Study Notes v1"])


@router.get("", response_model=List[StudyNoteResponse])
async def list_study_notes(
    subject_id: Optional[str] = Query(None),
    lesson_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: asyncpg.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists study notes filtered by subject, lesson, or search query."""
    repo = StudyNoteRepository(conn)
    try:
        return await repo.list_notes(
            subject_id=subject_id,
            lesson_id=lesson_id,
            search=search,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/{note_id}", response_model=StudyNoteResponse)
async def get_study_note(
    note_id: str,
    conn: asyncpg.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Fetches a single study note by ID."""
    repo = StudyNoteRepository(conn)
    note = await repo.get_by_id(note_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study note '{note_id}' not found.",
        )
    return note


@router.post("", response_model=StudyNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_study_note(
    body: StudyNoteCreateOrUpdate,
    _current_user: Dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Creates or updates a study note."""
    repo = StudyNoteRepository(conn)
    try:
        return await repo.upsert(
            note_id=body.id,
            title=body.title,
            subject_id=body.subject_id,
            lesson_id=body.lesson_id,
            content_text=body.content_text,
            description=body.description,
            pdf_url=body.pdf_url,
            is_premium=body.is_premium,
            order_index=body.order_index,
            author=body.author,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.delete("/{note_id}")
async def delete_study_note(
    note_id: str,
    _current_user: Dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Deletes a study note by ID."""
    repo = StudyNoteRepository(conn)
    try:
        return await repo.delete(note_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

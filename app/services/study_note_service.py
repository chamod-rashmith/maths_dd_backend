"""
Application Service for Study Notes.
"""

from typing import Any, Dict, List, Optional

from app.domain.exceptions import EntityNotFoundError
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.schemas.study_note import StudyNoteCreateOrUpdate


class StudyNoteService:
    """Orchestrates study note filtering, retrieval, creation, and deletion."""

    def __init__(self, repo: StudyNoteRepository) -> None:
        self._repo = repo

    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return await self._repo.list_notes(
            subject_id=subject_id,
            lesson_id=lesson_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def get_note_by_id(self, note_id: str) -> Dict[str, Any]:
        note = await self._repo.get_by_id(note_id)
        if not note:
            raise EntityNotFoundError(f"Study note '{note_id}' not found.")
        return note

    async def upsert_note(self, payload: StudyNoteCreateOrUpdate) -> Dict[str, Any]:
        return await self._repo.upsert(
            note_id=payload.id,
            title=payload.title,
            subject_id=payload.subject_id,
            lesson_id=payload.lesson_id,
            content_text=payload.content_text,
            description=payload.description,
            pdf_url=payload.pdf_url,
            is_premium=payload.is_premium,
            order_index=payload.order_index,
            author=payload.author,
        )

    async def delete_note(self, note_id: str) -> Dict[str, Any]:
        return await self._repo.delete(note_id)

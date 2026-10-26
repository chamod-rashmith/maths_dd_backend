"""
Application Service for Study Notes with Upstash Redis Caching.
"""

from typing import Any, Dict, List, Optional

from app.core.cache import study_notes_cache
from app.core.storage import generate_signed_download_url
from app.domain.exceptions import EntityNotFoundError
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.schemas.study_note import StudyNoteCreateOrUpdate

_STUDY_NOTES_LIST_PREFIX = "study_notes:list:"
_STUDY_NOTES_DETAIL_PREFIX = "study_notes:detail:"


class StudyNoteService:
    """Orchestrates study note filtering, retrieval with caching, signed URL generation, and cache-invalidating writes."""

    def __init__(self, repo: StudyNoteRepository) -> None:
        self._repo = repo

    def _build_list_cache_key(
        self,
        subject_id: Optional[str],
        lesson_id: Optional[str],
        search: Optional[str],
        limit: int,
        offset: int,
    ) -> str:
        s_id = (subject_id or "all").strip().lower()
        l_id = (lesson_id or "all").strip().lower()
        q = (search or "none").strip().lower()
        return f"{_STUDY_NOTES_LIST_PREFIX}{s_id}:{l_id}:{q}:{limit}:{offset}"

    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        cache_key = self._build_list_cache_key(subject_id, lesson_id, search, limit, offset)
        cached = study_notes_cache.get(cache_key)
        if cached is not None:
            return cached

        notes = await self._repo.list_notes(
            subject_id=subject_id,
            lesson_id=lesson_id,
            search=search,
            limit=limit,
            offset=offset,
        )
        study_notes_cache.set(cache_key, notes)
        return notes

    async def get_note_by_id(self, note_id: str) -> Dict[str, Any]:
        cache_key = f"{_STUDY_NOTES_DETAIL_PREFIX}{note_id.strip()}"
        cached = study_notes_cache.get(cache_key)
        if cached is not None:
            result = dict(cached)
        else:
            note = await self._repo.get_by_id(note_id)
            if not note:
                raise EntityNotFoundError(f"Study note '{note_id}' not found.")
            result = dict(note)
            # Cache the raw note payload for 1 hour
            study_notes_cache.set(cache_key, result)

        # Generate on-demand fresh signed URL if note is PDF
        raw_pdf_path = result.get("pdf_url")
        if raw_pdf_path and str(raw_pdf_path).strip():
            result["pdf_url"] = generate_signed_download_url(
                storage_path=str(raw_pdf_path),
                expiration_minutes=60,
            )

        return result

    async def upsert_note(self, payload: StudyNoteCreateOrUpdate) -> Dict[str, Any]:
        # Normalize storage path if incoming payload has full gs:// URI
        normalized_pdf_path = payload.pdf_url
        if normalized_pdf_path and normalized_pdf_path.startswith("gs://"):
            parts = normalized_pdf_path.replace("gs://", "").split("/", 1)
            normalized_pdf_path = parts[1] if len(parts) > 1 else parts[0]

        note = await self._repo.upsert(
            note_id=payload.id,
            title=payload.title,
            subject_id=payload.subject_id,
            lesson_id=payload.lesson_id,
            content_text=payload.content_text,
            description=payload.description,
            pdf_url=normalized_pdf_path,
            is_premium=payload.is_premium,
            order_index=payload.order_index,
            author=payload.author,
        )

        # Invalidate study notes cache (lists and detail)
        study_notes_cache.invalidate_prefix("study_notes:")
        return note

    async def delete_note(self, note_id: str) -> Dict[str, Any]:
        result = await self._repo.delete(note_id)
        # Invalidate study notes cache (lists and detail)
        study_notes_cache.invalidate_prefix("study_notes:")
        return result

"""
Application Service for Study Notes with Upstash Redis Caching, Voting, and Bookmarking.
"""

from typing import Any, Dict, List, Optional

from app.core.cache import study_notes_cache
from app.core.storage import generate_signed_download_url
from app.domain.exceptions import EntityNotFoundError, ValidationDomainError
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.schemas.study_note import StudyNoteCreateOrUpdate

_STUDY_NOTES_LIST_PREFIX = "study_notes:list:"
_STUDY_NOTES_DETAIL_PREFIX = "study_notes:detail:"


class StudyNoteService:
    """Orchestrates study note filtering, retrieval with caching, signed URL generation, voting, bookmarking, and cache-invalidating writes."""

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
        user_id: Optional[str] = None,
        bookmarked_only: bool = False,
    ) -> Dict[str, Any]:
        # Bookmarked-only listing is user-specific; query normalized tables directly
        if bookmarked_only:
            return await self._repo.list_notes(
                subject_id=subject_id,
                lesson_id=lesson_id,
                search=search,
                limit=limit,
                offset=offset,
                user_id=user_id,
                bookmarked_only=True,
            )

        cache_key = self._build_list_cache_key(subject_id, lesson_id, search, limit, offset)
        cached = study_notes_cache.get(cache_key)
        if cached is not None:
            items_copy = [dict(item) for item in cached.get("items", [])]
            if user_id and items_copy:
                note_ids = [str(item["id"]) for item in items_copy if item.get("id")]
                states = await self._repo.get_user_note_states(user_id=user_id, note_ids=note_ids)
                for item in items_copy:
                    st = states.get(str(item.get("id")), {})
                    item["user_vote"] = int(st.get("user_vote", 0))
                    item["is_bookmarked"] = bool(st.get("is_bookmarked", False))
            return {
                "items": items_copy,
                "total": int(cached.get("total", len(items_copy))),
            }

        result = await self._repo.list_notes(
            subject_id=subject_id,
            lesson_id=lesson_id,
            search=search,
            limit=limit,
            offset=offset,
            user_id=user_id,
            bookmarked_only=False,
        )

        # Store a clean user-agnostic copy in shared cache so user A's vote/bookmark state never leaks to user B
        shared_items = []
        for item in result.get("items", []):
            clean_item = dict(item)
            clean_item["user_vote"] = 0
            clean_item["is_bookmarked"] = False
            shared_items.append(clean_item)
        study_notes_cache.set(
            cache_key,
            {
                "items": shared_items,
                "total": int(result.get("total", len(shared_items))),
            },
        )
        return result

    async def get_note_by_id(
        self,
        note_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cache_key = f"{_STUDY_NOTES_DETAIL_PREFIX}{note_id.strip()}"
        cached = study_notes_cache.get(cache_key)
        if cached is not None:
            result = dict(cached)
            if user_id:
                states = await self._repo.get_user_note_states(
                    user_id=user_id,
                    note_ids=[note_id.strip()],
                )
                st = states.get(note_id.strip(), {})
                result["user_vote"] = int(st.get("user_vote", 0))
                result["is_bookmarked"] = bool(st.get("is_bookmarked", False))
        else:
            note = await self._repo.get_by_id(note_id, user_id=user_id)
            if not note:
                raise EntityNotFoundError(f"Study note '{note_id}' not found.")
            result = dict(note)
            # Cache the user-agnostic note payload for 1 hour
            clean_cache_copy = dict(result)
            clean_cache_copy["user_vote"] = 0
            clean_cache_copy["is_bookmarked"] = False
            study_notes_cache.set(cache_key, clean_cache_copy)

        # Generate on-demand fresh signed URL if note is PDF
        raw_pdf_path = result.get("pdf_url")
        if raw_pdf_path and str(raw_pdf_path).strip():
            result["pdf_url"] = generate_signed_download_url(
                storage_path=str(raw_pdf_path),
                expiration_minutes=60,
            )

        return result

    async def vote_note(
        self,
        note_id: str,
        user_id: str,
        vote: int,
    ) -> Dict[str, Any]:
        if vote not in (-1, 0, 1):
            raise ValidationDomainError(
                "Invalid vote value. Must be 1 (Upvote), -1 (Downvote), or 0 (No vote)."
            )
        result = await self._repo.vote_note(
            note_id=note_id.strip(),
            user_id=user_id.strip(),
            vote=int(vote),
        )
        if not result:
            raise EntityNotFoundError(f"Study note '{note_id}' not found.")

        # Invalidate shared study notes cache so updated upvote_count/downvote_count reflect immediately
        study_notes_cache.invalidate_prefix("study_notes:")
        return result

    async def toggle_bookmark(
        self,
        note_id: str,
        user_id: str,
        is_bookmarked: Optional[bool] = None,
    ) -> Dict[str, Any]:
        result = await self._repo.toggle_bookmark(
            note_id=note_id.strip(),
            user_id=user_id.strip(),
            is_bookmarked=is_bookmarked,
        )
        if not result:
            raise EntityNotFoundError(f"Study note '{note_id}' not found.")
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


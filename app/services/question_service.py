"""
Application Service for Questions and Marking Schemes.
Orchestrates catalog filtering, scheduled_date daily challenge resolution with hybrid Redis caching,
on-demand marking scheme retrieval, signed URL generation, and curriculum/question cache invalidation.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.core.cache import curriculum_cache, questions_cache
from app.core.storage import generate_signed_download_url
from app.domain.exceptions import (
    AuthenticationError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from app.domain.repositories.question_repository import QuestionRepository
from app.schemas.question import QuestionCreate

_COLOMBO_TZ = ZoneInfo("Asia/Colombo")


def _resolve_colombo_date_str(target_date: Optional[str] = None) -> str:
    """Returns YYYY-MM-DD string for target_date or current date in Asia/Colombo."""
    if target_date and str(target_date).strip():
        try:
            return date.fromisoformat(str(target_date).strip()[:10]).isoformat()
        except (ValueError, TypeError):
            pass
    return datetime.now(_COLOMBO_TZ).date().isoformat()


class QuestionService:
    """Orchestrates question creation, catalog retrieval, daily challenge lookup, and on-demand solutions."""

    def __init__(self, repo: QuestionRepository) -> None:
        self._repo = repo

    def _hydrate_question_signed_url(
        self, question: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generates a fresh 1-hour signed download URL if the question uses a Cloud Storage asset."""
        result = dict(question)
        raw_url = result.get("content_url")
        if raw_url and str(raw_url).strip():
            result["content_url"] = generate_signed_download_url(
                storage_path=str(raw_url),
                expiration_minutes=60,
            )
        return result

    async def list_questions(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        schedule: Optional[str] = None,
        source: Optional[str] = None,
        is_premium: Optional[bool] = None,
        include_unpublished: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return await self._repo.list_questions(
            subject_id=subject_id,
            lesson_id=lesson_id,
            question_type=question_type,
            difficulty=difficulty,
            schedule=schedule,
            source=source,
            is_premium=is_premium,
            include_unpublished=include_unpublished,
            limit=limit,
            offset=offset,
        )

    async def list_recent_questions(
        self, limit: int = 15
    ) -> List[Dict[str, Any]]:
        return await self._repo.get_recent(limit=limit)

    async def get_question_by_id(self, question_id: str) -> Dict[str, Any]:
        question = await self._repo.get_by_id(question_id)
        if not question:
            raise EntityNotFoundError(f"Question '{question_id}' not found.")
        return self._hydrate_question_signed_url(question)

    async def get_daily_question(
        self, target_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        resolved_date_str = _resolve_colombo_date_str(target_date)
        cache_key = f"daily_question:{resolved_date_str}"

        # 1. Check Redis / In-Memory hybrid cache
        cached = questions_cache.get(cache_key)
        if cached is not None:
            # Re-hydrate signed download URL dynamically on-the-fly so it never expires in cache
            return self._hydrate_question_signed_url(cached)

        # 2. Cache miss -> query Cloud SQL repository
        question = await self._repo.get_daily_question(target_date=target_date)
        if not question:
            return None

        # 3. Store raw question in cache (without pre-signed URL) with 24-hour TTL
        questions_cache.set(cache_key, question, ttl_seconds=86400)

        # 4. Hydrate signed URL dynamically for client response
        return self._hydrate_question_signed_url(question)

    async def get_marking_scheme(
        self,
        question_id: str,
        current_user: Optional[Dict[str, Any]] = None,
        is_premium: bool = False,
    ) -> Dict[str, Any]:
        scheme = await self._repo.get_marking_scheme(question_id)
        if not scheme:
            raise EntityNotFoundError(
                f"Marking scheme for question '{question_id}' not found."
            )

        if scheme.get("is_premium_only"):
            if not current_user:
                raise AuthenticationError(
                    "Authentication is required to access this premium solution."
                )
            if not is_premium:
                raise PermissionDeniedError(
                    "A premium subscription is required to view this marking scheme."
                )

        result = dict(scheme)
        raw_pdf = result.get("pdf_url")
        if raw_pdf and str(raw_pdf).strip():
            result["pdf_url"] = generate_signed_download_url(
                storage_path=str(raw_pdf),
                expiration_minutes=60,
            )
        return result

    async def create_question(
        self, payload: QuestionCreate
    ) -> Dict[str, Any]:
        resolved_id = payload.id or payload.custom_id
        result = await self._repo.create_question_with_solution(
            title=payload.title,
            description=payload.description or "",
            subject_id=payload.subject_id,
            lesson_id=payload.lesson_id,
            content_text=payload.content_text or "",
            content_url=payload.content_url,
            solution_text=payload.solution_text or "",
            solution_pdf_url=payload.solution_pdf_url,
            solution_title=payload.solution_title,
            question_type=payload.question_type,
            difficulty=payload.difficulty,
            schedule=payload.schedule,
            source=payload.source,
            source_details=payload.source_details or "",
            allocated_marks=payload.allocated_marks,
            is_premium=payload.is_premium,
            is_published=payload.is_published,
            scheduled_date=payload.scheduled_date,
            custom_id=resolved_id,
        )
        # Invalidate curriculum lesson cache so question_count / premium_count refresh immediately
        curriculum_cache.invalidate_prefix("curriculum:")
        # Invalidate daily question cache so newly scheduled challenges appear immediately
        questions_cache.invalidate_prefix("daily_question")
        return result

    async def delete_question(self, question_id: str) -> Dict[str, Any]:
        result = await self._repo.delete_question(question_id)
        curriculum_cache.invalidate_prefix("curriculum:")
        questions_cache.invalidate_prefix("daily_question")
        return result

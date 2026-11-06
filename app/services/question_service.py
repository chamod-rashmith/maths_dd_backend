"""
Application Service for Questions, Marking Schemes, and Daily Challenges.
Orchestrates catalog filtering, dynamic multi-question daily pack resolution with hybrid Redis caching,
sequential daily challenge series cataloging with tomorrow's teaser support,
strict anti-leak time-locks, on-demand marking scheme retrieval,
dynamic signed URL generation, and cache invalidation.
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
    """Orchestrates question creation, catalog retrieval, daily challenge packs, and on-demand solutions."""

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
        day_number: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        result = await self._repo.list_questions(
            subject_id=subject_id,
            lesson_id=lesson_id,
            question_type=question_type,
            difficulty=difficulty,
            schedule=schedule,
            source=source,
            is_premium=is_premium,
            include_unpublished=include_unpublished,
            day_number=day_number,
            limit=limit,
            offset=offset,
        )
        result["items"] = [
            self._hydrate_question_signed_url(q) for q in result["items"]
        ]
        return result

    async def list_recent_questions(
        self, limit: int = 15
    ) -> List[Dict[str, Any]]:
        result = await self._repo.get_recent(limit=limit)
        items = result["items"] if isinstance(result, dict) else result
        return [self._hydrate_question_signed_url(q) for q in items]

    @staticmethod
    def _is_privileged_user(current_user: Optional[Dict[str, Any]]) -> bool:
        role = str((current_user or {}).get("role", "")).upper()
        return role in ("ADMIN", "EDITOR")

    @staticmethod
    def _question_date(question: Dict[str, Any]) -> Optional[date]:
        scheduled_date = question.get("scheduled_date")
        if isinstance(scheduled_date, date):
            return scheduled_date
        if scheduled_date:
            try:
                return date.fromisoformat(str(scheduled_date)[:10])
            except (TypeError, ValueError):
                return None
        return None

    def _enforce_question_access(
        self,
        question: Dict[str, Any],
        current_user: Optional[Dict[str, Any]],
        is_premium: bool,
    ) -> None:
        """Block unreleased and premium question content at the service boundary."""
        if self._is_privileged_user(current_user):
            return

        if not question.get("is_published", False):
            raise PermissionDeniedError(
                "This question has not been published yet."
            )

        scheduled_date = self._question_date(question)
        today_colombo = datetime.now(_COLOMBO_TZ).date()
        if scheduled_date and scheduled_date > today_colombo:
            raise PermissionDeniedError(
                f"This question is locked until {scheduled_date.isoformat()}."
            )

        if question.get("is_premium", False) and not is_premium:
            raise PermissionDeniedError(
                "An active premium subscription is required to view this question."
            )

    async def get_question_by_id(
        self,
        question_id: str,
        current_user: Optional[Dict[str, Any]] = None,
        is_premium: bool = False,
    ) -> Dict[str, Any]:
        question = await self._repo.get_by_id(question_id)
        if not question:
            raise EntityNotFoundError(
                f"Question with ID '{question_id}' was not found in database."
            )
        self._enforce_question_access(question, current_user, is_premium)
        return self._hydrate_question_signed_url(question)

    async def get_daily_question(
        self, target_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Internal helper for single daily question lookup."""
        resolved_date_str = _resolve_colombo_date_str(target_date)
        cache_key = f"daily_question:{resolved_date_str}"

        cached = questions_cache.get(cache_key)
        if cached is not None:
            return self._hydrate_question_signed_url(cached)

        question = await self._repo.get_daily_question(target_date=target_date)
        if not question:
            return None

        questions_cache.set(cache_key, question, ttl_seconds=86400)
        return self._hydrate_question_signed_url(question)

    async def get_daily_pack(
        self,
        target_date: Optional[str] = None,
        day_number: Optional[int] = None,
        current_user: Optional[Dict[str, Any]] = None,
        is_premium: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the complete dynamic multi-question daily challenge pack for a target date or day number.
        Uses date-based or day-based hybrid Redis caching with on-the-fly pre-signed download URL hydration.

        Strict Anti-Leak Security Policy:
        - Regular students cannot access future challenge packs. If the scheduled date is in the future
          compared to Asia/Colombo time, a PermissionDeniedError (HTTP 403) is raised.
        - Privileged roles (ADMIN, EDITOR) can preview future packs.
        """
        is_privileged = self._is_privileged_user(current_user)

        today_colombo = datetime.now(_COLOMBO_TZ).date()

        # Pre-check target_date parameter if explicitly provided
        if target_date and not is_privileged:
            try:
                requested_date = date.fromisoformat(str(target_date).strip()[:10])
                if requested_date > today_colombo:
                    raise PermissionDeniedError(
                        f"Daily Challenge Pack for {requested_date} is locked until that date."
                    )
            except (ValueError, TypeError):
                pass

        if day_number is not None and day_number > 0:
            cache_key = f"daily_pack:day_{day_number}"
        else:
            resolved_date_str = _resolve_colombo_date_str(target_date)
            cache_key = f"daily_pack:date_{resolved_date_str}"

        # 1. Check Redis / In-Memory hybrid cache
        cached = questions_cache.get(cache_key)
        if cached is not None:
            pack_date = cached.get("scheduled_date")
            if not is_privileged and pack_date is not None:
                if isinstance(pack_date, str):
                    try:
                        pack_date = date.fromisoformat(pack_date[:10])
                    except (ValueError, TypeError):
                        pack_date = None
                if pack_date and pack_date > today_colombo:
                    raise PermissionDeniedError(
                        f"Day {cached.get('day_number', day_number)} Challenge Pack is locked until {pack_date} 00:00 AM Sri Lanka Time."
                    )
            result = dict(cached)
            for question in result.get("questions", []):
                self._enforce_question_access(question, current_user, is_premium)
            result["questions"] = [
                self._hydrate_question_signed_url(q) for q in result.get("questions", [])
            ]
            return result

        # 2. Cache miss -> query Cloud SQL repository
        pack = await self._repo.get_daily_pack(target_date=target_date, day_number=day_number)
        if not pack:
            return None

        # Verify anti-leak lock on repository result
        pack_date = pack.get("scheduled_date")
        if not is_privileged and pack_date is not None:
            if isinstance(pack_date, str):
                try:
                    pack_date = date.fromisoformat(pack_date[:10])
                except (ValueError, TypeError):
                    pack_date = None
            if pack_date and pack_date > today_colombo:
                raise PermissionDeniedError(
                    f"Day {pack.get('day_number', day_number)} Challenge Pack is locked until {pack_date} 00:00 AM Sri Lanka Time."
                )

        for question in pack.get("questions", []):
            self._enforce_question_access(question, current_user, is_premium)

        # 3. Store raw pack in cache (without pre-signed URLs) with 24-hour TTL
        questions_cache.set(cache_key, pack, ttl_seconds=86400)

        # 4. Hydrate signed URLs dynamically for client response
        result = dict(pack)
        result["questions"] = [
            self._hydrate_question_signed_url(q) for q in result.get("questions", [])
        ]
        return result

    async def list_daily_series(
        self,
        limit: int = 30,
        offset: int = 0,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves the catalog list of daily challenge series summaries in reverse-chronological order.
        Includes safe teaser metadata for tomorrow's challenge (without leaking question bodies).
        """
        cache_key = f"daily_series:catalog:{limit}_{offset}"
        cached = questions_cache.get(cache_key)
        if cached is not None:
            return cached

        series = await self._repo.list_daily_series(limit=limit, offset=offset)
        questions_cache.set(cache_key, series, ttl_seconds=300)
        return series

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
            day_number=payload.day_number,
            custom_id=resolved_id,
        )
        curriculum_cache.invalidate_prefix("curriculum:")
        questions_cache.invalidate_prefix("daily_question")
        questions_cache.invalidate_prefix("daily_pack")
        questions_cache.invalidate_prefix("daily_series")
        return result

    async def delete_question(self, question_id: str) -> Dict[str, Any]:
        result = await self._repo.delete_question(question_id)
        curriculum_cache.invalidate_prefix("curriculum:")
        questions_cache.invalidate_prefix("daily_question")
        questions_cache.invalidate_prefix("daily_pack")
        questions_cache.invalidate_prefix("daily_series")
        return result

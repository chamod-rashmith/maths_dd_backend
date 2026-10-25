"""
Application Service for Curriculum (Subjects & Syllabus Lessons) with TTL Caching.
"""

from typing import Any, Dict, List, Optional

from app.core.cache import curriculum_cache
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.schemas.curriculum import LessonCreate, SubjectCreate

_SUBJECTS_CACHE_KEY = "curriculum:subjects:all"
_LESSONS_CACHE_PREFIX = "curriculum:lessons:"


class CurriculumService:
    """Orchestrates curriculum reads (with in-memory/Redis TTL caching) and cache-invalidating writes."""

    def __init__(self, repo: CurriculumRepository) -> None:
        self._repo = repo

    async def list_subjects(self) -> List[Dict[str, Any]]:
        cached = curriculum_cache.get(_SUBJECTS_CACHE_KEY)
        if cached is not None:
            return cached

        subjects = await self._repo.get_subjects()
        curriculum_cache.set(_SUBJECTS_CACHE_KEY, subjects)
        return subjects

    async def upsert_subject(self, payload: SubjectCreate) -> Dict[str, Any]:
        subject = await self._repo.upsert_subject(
            subject_id=payload.id,
            name=payload.name,
            sinhala_name=payload.sinhala_name or "",
            code=payload.code,
            order_index=payload.order_index,
            description=payload.description or "",
        )
        curriculum_cache.invalidate_prefix("curriculum:")
        return subject

    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        result = await self._repo.delete_subject(subject_id)
        curriculum_cache.invalidate_prefix("curriculum:")
        return result

    async def list_lessons(
        self,
        subject_id: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cache_key_suffix = (subject_code or subject_id or "all").lower()
        cache_key = f"{_LESSONS_CACHE_PREFIX}{cache_key_suffix}"
        cached = curriculum_cache.get(cache_key)
        if cached is not None:
            return cached

        lessons = await self._repo.get_lessons(
            subject_id=subject_id, subject_code=subject_code
        )
        curriculum_cache.set(cache_key, lessons)
        return lessons

    async def upsert_lesson(self, payload: LessonCreate) -> Dict[str, Any]:
        lesson = await self._repo.upsert_lesson(
            lesson_id=payload.id,
            subject_id=payload.subject_id,
            title=payload.title,
            sinhala_title=payload.sinhala_title or "",
            order_index=payload.order_index,
            description=payload.description or "",
        )
        curriculum_cache.invalidate_prefix(_LESSONS_CACHE_PREFIX)
        return lesson

    async def delete_lesson(self, lesson_id: str) -> Dict[str, Any]:
        result = await self._repo.delete_lesson(lesson_id)
        curriculum_cache.invalidate_prefix(_LESSONS_CACHE_PREFIX)
        return result

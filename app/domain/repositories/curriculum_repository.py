"""
Abstract Repository Contract for Curriculum (Subjects & Syllabus Lessons).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.domain.entities import LessonEntity, SubjectEntity


class CurriculumRepository(ABC):
    """Domain contract defining curriculum subjects and syllabus lessons persistence."""

    @abstractmethod
    async def get_subjects(self) -> List[SubjectEntity]:
        """Returns all subjects ordered by order_index ascending."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_subject(
        self,
        subject_id: str,
        name: str,
        sinhala_name: str,
        code: str,
        order_index: int,
        description: str = "",
    ) -> SubjectEntity:
        """Creates or updates a curriculum subject."""
        raise NotImplementedError

    @abstractmethod
    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        """Deletes a curriculum subject by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_lessons(
        self, subject_id: Optional[str] = None
    ) -> List[LessonEntity]:
        """Returns syllabus lessons, optionally filtered by subject_id."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_lesson(
        self,
        lesson_id: str,
        subject_id: str,
        title: str,
        sinhala_title: str,
        order_index: int,
        description: str = "",
    ) -> LessonEntity:
        """Creates or updates a syllabus lesson."""
        raise NotImplementedError

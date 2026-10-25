"""
Abstract Repository Contract for Curriculum (Subjects & Syllabus Lessons).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CurriculumRepository(ABC):
    """Domain contract defining curriculum subjects and syllabus lessons persistence."""

    @abstractmethod
    async def get_subjects(self) -> List[Dict[str, Any]]:
        """Returns all subjects ordered by order_index ascending."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_subject(
        self,
        subject_id: Optional[str],
        name: str,
        sinhala_name: str,
        code: str,
        order_index: int,
        description: str = "",
    ) -> Dict[str, Any]:
        """Creates or updates a curriculum subject."""
        raise NotImplementedError

    @abstractmethod
    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        """Deletes a curriculum subject by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_lessons(
        self, subject_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns syllabus lessons, optionally filtered by subject_id."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_lesson(
        self,
        lesson_id: Optional[str],
        subject_id: str,
        title: str,
        sinhala_title: str,
        order_index: int,
        description: str = "",
    ) -> Dict[str, Any]:
        """Creates or updates a syllabus lesson."""
        raise NotImplementedError

    @abstractmethod
    async def delete_lesson(self, lesson_id: str) -> Dict[str, Any]:
        """Deletes a syllabus lesson by ID."""
        raise NotImplementedError

"""
Abstract Repository Contract for Curriculum (Subjects & Syllabus Lessons).

===============================================================================
විෂය නිර්දේශයේ Repository අතුරුමුහුණත (Curriculum Repository Contract):
-------------------------------------------------------------------------------
Subjects සහ Hierarchical Syllabus Lessons (Units & Sub-lessons) කළමනාකරණය
සඳහා අවශ්‍ය සියලු database operations මෙම interface එක මඟින් අර්ථ දක්වයි.
===============================================================================
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
        self,
        subject_id: Optional[str] = None,
        subject_code: Optional[str] = None,
        parent_lesson_id: Optional[str] = None,
        root_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Returns syllabus lessons, optionally filtered by subject, parent_lesson_id, or root_only.

        Args:
            subject_id: Filter by subject ID.
            subject_code: Filter by subject code (e.g. 'PMAT', 'AMAT').
            parent_lesson_id: Filter sub-lessons belonging to this specific parent unit.
            root_only: If True, returns only top-level units (parent_lesson_id IS NULL).
        """
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
        parent_lesson_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates or updates a syllabus lesson or sub-lesson.

        Args:
            lesson_id: Lesson UUID or string ID (auto-generated if None).
            subject_id: ID of the subject this lesson belongs to.
            title: English title.
            sinhala_title: Sinhala title.
            order_index: Sequence order among siblings.
            description: Overview or notes.
            parent_lesson_id: Optional parent unit ID for hierarchical sub-lessons.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_lesson(self, lesson_id: str) -> Dict[str, Any]:
        """Deletes a syllabus lesson by ID."""
        raise NotImplementedError

"""
Abstract Repository Contract for Questions and Marking Schemes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class QuestionRepository(ABC):
    """Domain contract defining questions and marking schemes persistence."""

    @abstractmethod
    async def create_question_with_solution(
        self,
        title: str,
        subject_id: str,
        lesson_id: Optional[str],
        content_text: str,
        solution_text: str,
        description: str = "",
        content_url: Optional[str] = None,
        solution_pdf_url: Optional[str] = None,
        solution_title: str = "Official Marking Scheme",
        question_type: str = "SHORT",
        difficulty: str = "MEDIUM",
        schedule: str = "REGULAR",
        source: str = "PAST_PAPER",
        source_details: str = "",
        allocated_marks: int = 25,
        is_premium: bool = False,
        is_published: bool = True,
        scheduled_date: Optional[str] = None,
        custom_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atomically creates or updates a question along with its official marking scheme."""
        raise NotImplementedError

    @abstractmethod
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
        """Lists filtered and paginated question summaries."""
        raise NotImplementedError

    @abstractmethod
    async def get_recent(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recently created questions."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single question with its full content by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_daily_question(
        self, target_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetches the daily challenge question scheduled for the target calendar date."""
        raise NotImplementedError

    @abstractmethod
    async def get_marking_scheme(
        self, question_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetches the official marking scheme for a question on-demand."""
        raise NotImplementedError

    @abstractmethod
    async def delete_question(self, question_id: str) -> Dict[str, Any]:
        """Deletes a question and its cascaded marking schemes by ID."""
        raise NotImplementedError

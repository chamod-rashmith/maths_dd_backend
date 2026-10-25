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
        """Atomically creates a question along with its official marking scheme."""
        raise NotImplementedError

    @abstractmethod
    async def get_recent(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recently created questions."""
        raise NotImplementedError

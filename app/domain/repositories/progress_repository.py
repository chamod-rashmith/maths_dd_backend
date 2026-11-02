"""
Abstract Repository Contract for Student Progress, Attempts, and Heatmap telemetry.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.schemas.progress import (
    MarkQuestionCompletedRequest,
    UserProgressSummaryResponse,
)


class ProgressRepository(ABC):
    """Domain contract defining student progress persistence and calculation operations."""

    @abstractmethod
    async def get_user_progress_summary(
        self, user_id: str
    ) -> UserProgressSummaryResponse:
        """Computes and returns the full aggregated progress summary for the user."""
        raise NotImplementedError

    @abstractmethod
    async def mark_question_completed(
        self, user_id: str, request: MarkQuestionCompletedRequest
    ) -> UserProgressSummaryResponse:
        """Records or updates a question completion attempt, updating daily activity and streaks."""
        raise NotImplementedError

    @abstractmethod
    async def unmark_question_completed(
        self, user_id: str, question_id: str
    ) -> UserProgressSummaryResponse:
        """Deletes a question completion record and adjusts daily activity and streaks."""
        raise NotImplementedError

    @abstractmethod
    async def toggle_bookmark(
        self, user_id: str, question_id: str, is_bookmarked: bool
    ) -> bool:
        """Toggles the bookmark status for a question attempt."""
        raise NotImplementedError

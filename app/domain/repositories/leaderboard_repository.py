"""
Abstract Domain Repository interface for Island-Wide & District Leaderboards.
"""

from abc import ABC, abstractmethod
from typing import Any


class LeaderboardRepository(ABC):
    """Contract for querying Island-wide and District student XP leaderboards and personal ranks."""

    @abstractmethod
    async def get_leaderboard(
        self,
        current_user: dict[str, Any],
        district_identifier: int | str | None = None,
        exam_year: int | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Fetches top N students (Island-wide or District) plus the current user's live rank summary."""

    @abstractmethod
    async def get_user_rank_summary(
        self,
        current_user: dict[str, Any],
        exam_year: int | None = None,
    ) -> dict[str, Any]:
        """Fetches only the authenticated student's live Island-wide and District rank summary."""

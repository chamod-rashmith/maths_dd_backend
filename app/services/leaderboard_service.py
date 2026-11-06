"""
Application Service for Island-Wide & District Leaderboards.
"""

from typing import Any

from app.domain.repositories.leaderboard_repository import LeaderboardRepository
from app.schemas.leaderboard import LeaderboardResponse, MyRankSummaryResponse


class LeaderboardService:
    """Orchestrates Island-wide Top 50, District Leaderboard, and My Current Rank queries."""

    def __init__(self, repo: LeaderboardRepository) -> None:
        self._repo = repo

    async def get_leaderboard(
        self,
        current_user: dict[str, Any],
        district_id: int | str | None = None,
        exam_year: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LeaderboardResponse:
        """Returns validated `LeaderboardResponse` with top students and `my_rank`."""
        data = await self._repo.get_leaderboard(
            current_user=current_user,
            district_identifier=district_id,
            exam_year=exam_year,
            limit=limit,
            offset=offset,
        )
        return LeaderboardResponse.model_validate(data)

    async def get_my_rank(
        self,
        current_user: dict[str, Any],
        exam_year: int | None = None,
    ) -> MyRankSummaryResponse:
        """Returns validated `MyRankSummaryResponse` for the authenticated student."""
        data = await self._repo.get_user_rank_summary(
            current_user=current_user,
            exam_year=exam_year,
        )
        return MyRankSummaryResponse.model_validate(data)

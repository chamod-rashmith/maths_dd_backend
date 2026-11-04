"""
Application Service orchestrating Student Progress, Attempt Telemetry, Heatmap metrics, and XP Ledger.
මෙම Service මඟින් ශිෂ්‍යයාගේ ප්‍රගතිය, ප්‍රශ්න විසඳීම, Heatmap දත්ත, සහ XP විගණන ගනුදෙනු සම්බන්ධ
ව්‍යාපාරික නීති (Business Logic) කළමනාකරණය කරයි.
"""

import logging
from typing import Any, Dict, List

from app.domain.repositories.progress_repository import ProgressRepository
from app.schemas.progress import (
    MarkQuestionCompletedRequest,
    ToggleBookmarkRequest,
    UserProgressSummaryResponse,
    XpHistoryResponse,
    XpTransactionResponse,
)

logger = logging.getLogger("maths_dd.progress_service")


class ProgressService:
    """Service encapsulating business workflows for student progress tracking and gamification."""

    def __init__(self, repository: ProgressRepository) -> None:
        self.repository = repository

    async def get_progress_summary(
        self, current_user: Dict[str, Any]
    ) -> UserProgressSummaryResponse:
        """Fetch the authenticated student's full aggregated progress summary."""
        user_id = current_user.get("uid")
        if not user_id:
            return UserProgressSummaryResponse()
        return await self.repository.get_user_progress_summary(user_id)

    async def mark_question_completed(
        self, current_user: Dict[str, Any], body: MarkQuestionCompletedRequest
    ) -> UserProgressSummaryResponse:
        """
        Marks a question as completed (or records a practice session),
        accumulates study duration, awards verified XP transactions,
        updates Colombo streaks, and returns the updated progress summary.
        """
        user_id = current_user.get("uid")
        if not user_id:
            return UserProgressSummaryResponse()
        logger.info("Marking question %s completed for user %s", body.question_id, user_id)
        return await self.repository.mark_question_completed(user_id, body)

    async def unmark_question_completed(
        self, current_user: Dict[str, Any], question_id: str
    ) -> UserProgressSummaryResponse:
        """Removes question completion, logs negative XP reversal transaction, and refreshes summary."""
        user_id = current_user.get("uid")
        if not user_id:
            return UserProgressSummaryResponse()
        logger.info("Unmarking question %s completed for user %s", question_id, user_id)
        return await self.repository.unmark_question_completed(user_id, question_id)

    async def toggle_bookmark(
        self, current_user: Dict[str, Any], question_id: str, body: ToggleBookmarkRequest
    ) -> Dict[str, Any]:
        """Bookmark or unbookmark a question for student revision lists."""
        user_id = current_user.get("uid")
        if not user_id:
            return {"is_bookmarked": False}
        res = await self.repository.toggle_bookmark(user_id, question_id, body.is_bookmarked)
        return {"question_id": question_id, "is_bookmarked": res}

    async def get_xp_history(
        self, current_user: Dict[str, Any], limit: int = 50
    ) -> XpHistoryResponse:
        """Retrieves immutable XP audit trail records verifying the student's earned score."""
        user_id = current_user.get("uid")
        if not user_id:
            return XpHistoryResponse(total_xp=0, transactions=[])
        summary = await self.repository.get_user_progress_summary(user_id)
        txs = await self.repository.get_user_xp_history(user_id, limit=limit)
        tx_dtos = [XpTransactionResponse.model_validate(t) for t in txs]
        return XpHistoryResponse(total_xp=summary.xp, transactions=tx_dtos)

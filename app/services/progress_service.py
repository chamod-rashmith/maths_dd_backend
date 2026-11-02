"""
Application Service orchestrating Student Progress, Attempt Telemetry, and Heatmap metrics.
"""

import logging
from typing import Any, Dict

from app.domain.repositories.progress_repository import ProgressRepository
from app.schemas.progress import (
    MarkQuestionCompletedRequest,
    ToggleBookmarkRequest,
    UserProgressSummaryResponse,
)

logger = logging.getLogger("maths_dd.progress_service")


class ProgressService:
    """Service encapsulating business workflows for student progress tracking."""

    def __init__(self, repository: ProgressRepository) -> None:
        self.repository = repository

    async def get_progress_summary(
        self, current_user: Dict[str, Any]
    ) -> UserProgressSummaryResponse:
        user_id = current_user.get("uid")
        if not user_id:
            return UserProgressSummaryResponse()
        return await self.repository.get_user_progress_summary(user_id)

    async def mark_question_completed(
        self, current_user: Dict[str, Any], body: MarkQuestionCompletedRequest
    ) -> UserProgressSummaryResponse:
        user_id = current_user.get("uid")
        if not user_id:
            return UserProgressSummaryResponse()
        logger.info("Marking question %s completed for user %s", body.question_id, user_id)
        return await self.repository.mark_question_completed(user_id, body)

    async def unmark_question_completed(
        self, current_user: Dict[str, Any], question_id: str
    ) -> UserProgressSummaryResponse:
        user_id = current_user.get("uid")
        if not user_id:
            return UserProgressSummaryResponse()
        logger.info("Unmarking question %s completed for user %s", question_id, user_id)
        return await self.repository.unmark_question_completed(user_id, question_id)

    async def toggle_bookmark(
        self, current_user: Dict[str, Any], question_id: str, body: ToggleBookmarkRequest
    ) -> Dict[str, Any]:
        user_id = current_user.get("uid")
        if not user_id:
            return {"is_bookmarked": False}
        res = await self.repository.toggle_bookmark(user_id, question_id, body.is_bookmarked)
        return {"question_id": question_id, "is_bookmarked": res}

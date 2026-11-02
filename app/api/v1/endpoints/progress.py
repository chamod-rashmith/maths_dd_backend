"""
FastAPI Router for Student Progress, Question Completion Attempts, and Activity Heatmap v1.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, status

from app.api.deps import get_progress_service
from app.core.security import get_current_user
from app.schemas.progress import (
    MarkQuestionCompletedRequest,
    ToggleBookmarkRequest,
    UserProgressSummaryResponse,
)
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["Student Progress v1"])


@router.get(
    "/summary",
    response_model=UserProgressSummaryResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def get_progress_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> UserProgressSummaryResponse:
    """
    Returns the student's complete aggregated progress summary,
    including completed question records, lesson/subject stats, streaks,
    and daily activity heatmap buckets.
    """
    return await service.get_progress_summary(current_user)


@router.post(
    "/completed-questions",
    response_model=UserProgressSummaryResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def mark_question_completed(
    body: MarkQuestionCompletedRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> UserProgressSummaryResponse:
    """
    Marks a question as completed (or increments attempt count on re-solve),
    records elapsed time telemetry, updates today's daily activity heatmap bucket,
    recalculates consecutive streaks, and returns the updated progress summary.
    """
    return await service.mark_question_completed(current_user, body)


@router.delete(
    "/completed-questions/{question_id}",
    response_model=UserProgressSummaryResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def unmark_question_completed(
    question_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> UserProgressSummaryResponse:
    """
    Removes the completion attempt record for a question, decrements
    the corresponding date's activity heatmap bucket, recalculates streaks,
    and returns the updated progress summary.
    """
    return await service.unmark_question_completed(current_user, question_id)


@router.post(
    "/bookmarks/{question_id}",
    status_code=status.HTTP_200_OK,
)
async def toggle_bookmark(
    question_id: str,
    body: ToggleBookmarkRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> Dict[str, Any]:
    """
    Stars or unstars a question for quick student bookmarking and revision lists.
    """
    return await service.toggle_bookmark(current_user, question_id, body)

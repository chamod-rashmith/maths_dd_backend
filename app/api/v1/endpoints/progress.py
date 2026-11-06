"""
FastAPI Router for Student Progress, Question Completion Attempts, Activity Heatmap, and XP Ledger v1.
මෙම API මොඩියුලය මඟින් ශිෂ්‍යයාගේ ප්‍රගතිය, ප්‍රශ්න සම්පූර්ණ කිරීම, සමුච්චිත අධ්‍යයන කාලය,
සහ සාක්ෂි සහිත XP ගනුදෙනු ලේඛනය (XP Audit Proofs) ලබා දෙන සියලුම Endpoints කළමනාකරණය කරයි.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_progress_service
from app.core.security import get_current_user
from app.schemas.common import BookmarkToggleResponse
from app.schemas.progress import (
    MarkQuestionCompletedRequest,
    ToggleBookmarkRequest,
    UserProgressSummaryResponse,
    XpHistoryResponse,
)
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["Student Progress v1"])


@router.get(
    "/summary",
    response_model=UserProgressSummaryResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_200_OK,
    summary="Get Complete Student Progress & Heatmap Summary",
    description=(
        "Returns the student's complete aggregated progress summary, including completed question records, "
        "accurate cumulative study time, Colombo streaks, and daily activity heatmap buckets."
    ),
)
async def get_progress_summary(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> UserProgressSummaryResponse:
    """ශිෂ්‍යයාගේ සමස්ත ප්‍රගති සාරාංශය ලබා ගැනීම."""
    return await service.get_progress_summary(current_user)


@router.post(
    "/completed-questions",
    response_model=UserProgressSummaryResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_200_OK,
    summary="Mark Question as Completed / Practice",
    description=(
        "Marks a question as completed (or records a re-practice session), accumulates study duration "
        "without overwriting previous time, logs an immutable XP transaction with proof, and refreshes summary."
    ),
)
async def mark_question_completed(
    body: MarkQuestionCompletedRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> UserProgressSummaryResponse:
    """ප්‍රශ්නයක් විසඳූ බව සටහන් කර අදාළ XP ලකුණු ලබා දීම."""
    return await service.mark_question_completed(current_user, body)


@router.delete(
    "/completed-questions/{question_id}",
    response_model=UserProgressSummaryResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_200_OK,
    summary="Unmark Completed Question",
    description=(
        "Removes the completion attempt record for a question, decrements the corresponding date's "
        "activity heatmap bucket, records negative XP reversal audit proof, and returns refreshed summary."
    ),
)
async def unmark_question_completed(
    question_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> UserProgressSummaryResponse:
    """ප්‍රශ්නයක් සම්පූර්ණ කළ බවට වූ වාර්තාව ඉවත් කිරීම."""
    return await service.unmark_question_completed(current_user, question_id)


@router.post(
    "/bookmarks/{question_id}",
    response_model=BookmarkToggleResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle Question Bookmark",
    description="Stars or unstars a question for quick student bookmarking and revision lists.",
)
async def toggle_bookmark(
    question_id: str,
    body: ToggleBookmarkRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> dict[str, Any]:
    """ප්‍රශ්නයක් Bookmark / Star කිරීම හෝ ඉවත් කිරීම."""
    return await service.toggle_bookmark(current_user, question_id, body)


@router.get(
    "/xp-history",
    response_model=XpHistoryResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_200_OK,
    summary="Get Verified XP Transaction Ledger & Proofs",
    description=(
        "Returns the student's immutable XP audit history, listing every XP award or deduction "
        "with reason codes, timestamps, and localized Sinhala descriptions."
    ),
)
async def get_xp_history(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of recent XP transactions to return"),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> XpHistoryResponse:
    """ශිෂ්‍යයාගේ XP ගනුදෙනු ඉතිහාසය සහ සාක්ෂි ලබා ගැනීම."""
    return await service.get_xp_history(current_user, limit=limit)

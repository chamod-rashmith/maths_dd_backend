"""
FastAPI Router for v1 Questions and Marking Schemes operations.
Provides catalog filtering, scheduled_date daily challenge resolution,
single-question detail hydration, and on-demand marking scheme retrieval.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_question_service,
    get_user_repository,
    require_admin_or_editor,
)
from app.core.security import get_optional_current_user
from app.domain.repositories.user_repository import UserRepository
from app.schemas.question import (
    MarkingSchemeResponse,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionSummaryResponse,
    QuestionWithSolutionResponse,
)
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["Questions v1"])


@router.get("", response_model=List[QuestionSummaryResponse])
async def list_questions(
    subject_id: Optional[str] = Query(
        None,
        description="Filter by subject ID or code (e.g. 'PMAT', 'AMAT', 'pure_maths', 'applied_maths')",
    ),
    lesson_id: Optional[str] = Query(
        None, description="Filter by syllabus lesson ID"
    ),
    type: Optional[str] = Query(
        None, description="Filter by question type ('SHORT' or 'ESSAY')"
    ),
    difficulty: Optional[str] = Query(
        None, description="Filter by difficulty ('EASY', 'MEDIUM', 'HARD')"
    ),
    schedule: Optional[str] = Query(
        None, description="Filter by schedule category"
    ),
    source: Optional[str] = Query(
        None, description="Filter by source ('PAST_PAPER', 'MODEL_PAPER', etc.)"
    ),
    is_premium: Optional[bool] = Query(
        None, description="Filter by premium tier status"
    ),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: QuestionService = Depends(get_question_service),
) -> List[Dict[str, Any]]:
    """
    Lists published and active questions (where scheduled_date IS NULL or <= today)
    as lightweight summaries for catalog and lesson views.
    """
    return await service.list_questions(
        subject_id=subject_id,
        lesson_id=lesson_id,
        question_type=type,
        difficulty=difficulty,
        schedule=schedule,
        source=source,
        is_premium=is_premium,
        include_unpublished=False,
        limit=limit,
        offset=offset,
    )


@router.get("/daily", response_model=Optional[QuestionDetailResponse])
async def get_daily_question(
    date: Optional[str] = Query(
        None,
        description="Optional target date in YYYY-MM-DD format (defaults to today in Asia/Colombo)",
    ),
    service: QuestionService = Depends(get_question_service),
) -> Optional[Dict[str, Any]]:
    """
    Fetches today's Daily Challenge question using the immutable `scheduled_date` column.
    Automatically rolls over at midnight Sri Lanka Time with zero background cron jobs.
    """
    return await service.get_daily_question(target_date=date)


@router.get("/recent", response_model=List[QuestionSummaryResponse])
async def list_recent_questions(
    limit: int = Query(15, ge=1, le=100),
    service: QuestionService = Depends(get_question_service),
) -> List[Dict[str, Any]]:
    """Fetches the latest questions stored in Cloud SQL (including future scheduled for admin inspection)."""
    return await service.list_recent_questions(limit=limit)


@router.get("/{question_id}", response_model=QuestionDetailResponse)
async def get_question_by_id(
    question_id: str,
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """Fetches a single question with its full LaTeX/Markdown body or signed asset URL on-demand."""
    return await service.get_question_by_id(question_id)


@router.get("/{question_id}/solution", response_model=MarkingSchemeResponse)
async def get_question_solution(
    question_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """
    Fetches the official marking scheme and step-by-step solution for a question on-demand.
    Enforces subscription paywall access if the marking scheme is marked premium-only.
    """
    is_premium = False
    if current_user:
        role = str(current_user.get("role", "")).upper()
        if role in ("ADMIN", "EDITOR"):
            is_premium = True
        else:
            uid = current_user.get("uid")
            if uid:
                db_user = await user_repo.get_by_uid(uid)
                if db_user:
                    is_premium = bool(db_user.get("is_premium", False)) or str(
                        db_user.get("role", "")
                    ).upper() in ("ADMIN", "EDITOR")

    return await service.get_marking_scheme(
        question_id=question_id,
        current_user=current_user,
        is_premium=is_premium,
    )


@router.post(
    "",
    response_model=QuestionWithSolutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    q: QuestionCreate,
    _admin: Dict[str, Any] = Depends(require_admin_or_editor),
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """Creates or updates a question with its corresponding marking scheme (requires ADMIN or EDITOR role)."""
    return await service.create_question(q)


@router.delete("/{question_id}")
async def remove_question(
    question_id: str,
    _admin: Dict[str, Any] = Depends(require_admin_or_editor),
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """Deletes a question by ID (requires ADMIN or EDITOR role)."""
    return await service.delete_question(question_id)

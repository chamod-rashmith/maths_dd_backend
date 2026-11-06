"""
FastAPI Router for v1 Questions and Marking Schemes operations.
Enforces strict authentication across all student endpoints (Logged-in users only).
Enforces anti-leak time-locks on daily challenges (content is never sent for future locked days).
Removes deprecated single-question /daily endpoint in favor of dynamic multi-question /daily/pack.
Provides reverse-chronological daily series catalog with safe teaser metadata for tomorrow.
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_question_service,
    get_user_repository,
    require_admin_or_editor,
)
from app.core.security import get_current_user, get_optional_current_user
from app.domain.repositories.user_repository import UserRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.question import (
    DailyChallengePackResponse,
    DailySeriesDaySummaryResponse,
    MarkingSchemeResponse,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionSummaryResponse,
    QuestionWithSolutionResponse,
)
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["Questions v1"])


async def _has_premium_access(
    current_user: Dict[str, Any], user_repo: UserRepository
) -> bool:
    """Resolve premium access server-side; never trust a client-supplied flag."""
    role = str(current_user.get("role", "")).upper()
    if role in ("ADMIN", "EDITOR"):
        return True

    uid = current_user.get("uid")
    if not uid:
        return False
    db_user = await user_repo.get_by_uid(uid)
    return bool(
        db_user
        and (
            db_user.get("is_premium", False)
            or str(db_user.get("role", "")).upper() in ("ADMIN", "EDITOR")
        )
    )


@router.get(
    "",
    response_model=Union[
        PaginatedResponse[QuestionSummaryResponse], List[QuestionSummaryResponse]
    ],
)
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
    day_number: Optional[int] = Query(
        None, description="Filter by sequential daily challenge day number"
    ),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """
    Lists published and active questions as lightweight summaries for catalog and lesson views.
    Security: Requires an authenticated user session (Bearer token).
    Data minimization: Excludes heavy problem content and internal database timestamps.
    """
    result = await service.list_questions(
        subject_id=subject_id,
        lesson_id=lesson_id,
        question_type=type,
        difficulty=difficulty,
        schedule=schedule,
        source=source,
        is_premium=is_premium,
        include_unpublished=False,
        day_number=day_number,
        limit=limit,
        offset=offset,
    )
    if isinstance(result, list):
        return result

    page_size = limit
    page = (offset // page_size) + 1
    return {
        "items": result["items"],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": result["total"],
            "has_next": offset + len(result["items"]) < result["total"],
        },
    }


@router.get("/daily/pack", response_model=Optional[DailyChallengePackResponse])
async def get_daily_challenge_pack(
    date: Optional[str] = Query(
        None,
        description="Target date in YYYY-MM-DD format (defaults to current date in Asia/Colombo)",
    ),
    day: Optional[int] = Query(
        None,
        description="Sequential target day number (e.g. 1 for Day 1 challenge pack)",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> Optional[Dict[str, Any]]:
    """
    Fetches the dynamic multi-question daily challenge workout pack (e.g. 1, 4, or 8-10 questions).
    Security & Anti-Leak Policy:
    - Requires an authenticated user session.
    - Future locked days (e.g. tomorrow or beyond) will NEVER return question content or LaTeX texts
      to regular students. Attempting to fetch a future locked day returns a 403 Forbidden.
    - Admins and content editors can preview future days for verification.
    """
    return await service.get_daily_pack(
        target_date=date,
        day_number=day,
        current_user=current_user,
        is_premium=await _has_premium_access(current_user, user_repo),
    )


@router.get("/daily/series", response_model=List[DailySeriesDaySummaryResponse])
async def list_daily_challenge_series(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
) -> List[Dict[str, Any]]:
    """
    Lists daily challenge series summaries in reverse-chronological order (Newest/Tomorrow/Today at top).
    Security & Privacy:
    - Requires an authenticated user session.
    - Tomorrow's challenge is included as a safe teaser (with total_questions, marks, unlock time),
      WITHOUT leaking any problem text or marking schemes.
    - Distant future days (beyond tomorrow) are excluded from student catalog.
    """
    return await service.list_daily_series(
        limit=limit,
        offset=offset,
        current_user=current_user,
    )


@router.get("/recent", response_model=List[QuestionSummaryResponse])
async def list_recent_questions(
    limit: int = Query(15, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
) -> List[Dict[str, Any]]:
    """
    Fetches the latest questions stored in Cloud SQL for catalog discovery.
    Requires an authenticated user session.
    """
    return await service.list_recent_questions(limit=limit)


@router.get("/{question_id}", response_model=QuestionDetailResponse)
async def get_question_by_id(
    question_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """
    Fetches a single question with its full LaTeX/Markdown problem statement or signed asset URL.
    Requires an authenticated user session.
    """
    return await service.get_question_by_id(
        question_id=question_id,
        current_user=current_user,
        is_premium=await _has_premium_access(current_user, user_repo),
    )


@router.get("/{question_id}/solution", response_model=MarkingSchemeResponse)
async def get_question_solution(
    question_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> Dict[str, Any]:
    """
    Fetches the official marking scheme and step-by-step solution for a question.
    Requires an authenticated user session and enforces premium subscription check for premium solutions.
    """
    is_premium = False
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

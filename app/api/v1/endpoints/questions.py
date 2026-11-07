"""
FastAPI Router for v1 Questions and Marking Schemes operations.
Enforces strict authentication across all student endpoints (Logged-in users only).
Enforces anti-leak time-locks on daily challenges (content is never sent for future locked days).
Removes deprecated single-question /daily endpoint in favor of dynamic multi-question /daily/pack.
Provides reverse-chronological daily series catalog with safe teaser metadata for tomorrow.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_admin_audit_service,
    get_question_service,
    get_user_repository,
    require_admin_or_editor,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.domain.enums import AuditAction, AuditResourceType
from app.domain.repositories.user_repository import UserRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.common import DeleteResponse
from app.schemas.pagination import PaginatedResponse, PaginationMetadata
from app.schemas.question import (
    DailyChallengePackResponse,
    DailySeriesDaySummaryResponse,
    MarkingSchemeResponse,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionSummaryResponse,
    QuestionWithSolutionResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["Questions v1"])
_PRIVILEGED_ROLES = {"ADMIN", "EDITOR"}


async def _resolve_question_access_context(
    current_user: dict[str, Any],
    user_repo: UserRepository,
    session: AsyncSession,
) -> tuple[dict[str, Any], bool]:
    """Resolve authoritative role + premium entitlement server-side."""
    resolved_user = dict(current_user)
    token_role = str(resolved_user.get("role", "")).upper()
    if token_role in _PRIVILEGED_ROLES:
        return resolved_user, True

    uid = resolved_user.get("uid")
    if not uid:
        return resolved_user, False

    db_user = await user_repo.get_by_uid(uid)
    db_role = str((db_user or {}).get("role", "")).upper()
    if db_role in _PRIVILEGED_ROLES:
        resolved_user["role"] = db_role
        return resolved_user, True

    sub_repo = SubscriptionRepository(session)
    return resolved_user, await sub_repo.is_user_premium(uid)


@router.get(
    "",
    response_model=PaginatedResponse[QuestionSummaryResponse],
)
async def list_questions(
    subject_id: str | None = Query(
        None,
        description="Filter by subject ID or code (e.g. 'PMAT', 'AMAT', 'pure_maths', 'applied_maths')",
    ),
    lesson_id: str | None = Query(
        None, description="Filter by syllabus lesson ID"
    ),
    type: str | None = Query(
        None, description="Filter by question type ('SHORT' or 'ESSAY')"
    ),
    difficulty: str | None = Query(
        None, description="Filter by difficulty ('EASY', 'MEDIUM', 'HARD')"
    ),
    source: str | None = Query(
        None, description="Filter by source ('PAST_PAPER', 'MODEL_PAPER', etc.)"
    ),
    is_premium: bool | None = Query(
        None, description="Filter by premium tier status"
    ),
    day_number: int | None = Query(
        None, description="Filter by sequential daily challenge day number"
    ),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
) -> PaginatedResponse[QuestionSummaryResponse]:
    """
    Lists published and active questions as lightweight summaries for catalog and lesson views.
    Always returns a standardized `PaginatedResponse[QuestionSummaryResponse]` envelope.
    Security: Requires an authenticated user session (Bearer token).
    Data minimization: Excludes heavy problem content and internal database timestamps.
    """
    result = await service.list_questions(
        subject_id=subject_id,
        lesson_id=lesson_id,
        question_type=type,
        difficulty=difficulty,
        source=source,
        is_premium=is_premium,
        include_unpublished=False,
        day_number=day_number,
        limit=limit,
        offset=offset,
    )
    if isinstance(result, list):
        items = result
        total = len(items)
    else:
        items = result["items"]
        total = int(result.get("total", len(items)))

    return PaginatedResponse(
        items=[QuestionSummaryResponse.model_validate(q) for q in items],
        pagination=PaginationMetadata.from_offset(
            total=total,
            limit=limit,
            offset=offset,
            items_count=len(items),
        ),
    )


@router.get("/daily/pack", response_model=DailyChallengePackResponse | None)
async def get_daily_challenge_pack(
    date: str | None = Query(
        None,
        description="Target date in YYYY-MM-DD format (defaults to current date in Asia/Colombo)",
    ),
    day: int | None = Query(
        None,
        description="Sequential target day number (e.g. 1 for Day 1 challenge pack)",
    ),
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> dict[str, Any] | None:
    """
    Fetches the dynamic multi-question daily challenge workout pack (e.g. 1, 4, or 8-10 questions).
    Security & Anti-Leak Policy:
    - Requires an authenticated user session.
    - Future locked days (e.g. tomorrow or beyond) will NEVER return question content or LaTeX texts
      to regular students. Attempting to fetch a future locked day returns a 403 Forbidden.
    - Admins and content editors can preview future days for verification.
    """
    resolved_user, is_premium = await _resolve_question_access_context(
        current_user=current_user,
        user_repo=user_repo,
        session=session,
    )
    return await service.get_daily_pack(
        target_date=date,
        day_number=day,
        current_user=resolved_user,
        is_premium=is_premium,
    )


@router.get("/daily/series", response_model=list[DailySeriesDaySummaryResponse])
async def list_daily_challenge_series(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
) -> list[dict[str, Any]]:
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


@router.get("/recent", response_model=list[QuestionSummaryResponse])
async def list_recent_questions(
    limit: int = Query(15, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
) -> list[dict[str, Any]]:
    """
    Fetches the latest questions stored in Cloud SQL for catalog discovery.
    Requires an authenticated user session.
    """
    return await service.list_recent_questions(limit=limit)


@router.get("/{question_id}", response_model=QuestionDetailResponse)
async def get_question_by_id(
    question_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> dict[str, Any]:
    """
    Fetches a single question with its full LaTeX/Markdown problem statement or signed asset URL.
    Requires an authenticated user session.
    """
    resolved_user, is_premium = await _resolve_question_access_context(
        current_user=current_user,
        user_repo=user_repo,
        session=session,
    )
    return await service.get_question_by_id(
        question_id=question_id,
        current_user=resolved_user,
        is_premium=is_premium,
    )


@router.get("/{question_id}/solution", response_model=MarkingSchemeResponse)
async def get_question_solution(
    question_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    service: QuestionService = Depends(get_question_service),
) -> dict[str, Any]:
    """
    Fetches the official marking scheme and step-by-step solution for a question.
    Requires an authenticated user session and enforces premium subscription check for premium solutions.
    """
    resolved_user, is_premium = await _resolve_question_access_context(
        current_user=current_user,
        user_repo=user_repo,
        session=session,
    )

    return await service.get_marking_scheme(
        question_id=question_id,
        current_user=resolved_user,
        is_premium=is_premium,
    )


@router.post(
    "",
    response_model=QuestionWithSolutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    q: QuestionCreate,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: QuestionService = Depends(get_question_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Creates or updates a question with its corresponding marking scheme (requires ADMIN or EDITOR role)."""
    result = await service.create_question(q)
    q_data = result.get("question") if isinstance(result, dict) else {}
    q_id = (q_data.get("id") if isinstance(q_data, dict) else None) or q.id
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.QUESTION_UPSERTED.value,
        resource_type=AuditResourceType.QUESTION.value,
        resource_id=str(q_id) if q_id else None,
        request=request,
        details={
            "title": q.title,
            "subject_id": q.subject_id,
            "type": str(
                q.question_type.value
                if hasattr(q.question_type, "value")
                else q.question_type
            ),
        },
    )
    return result


@router.delete(
    "/{question_id}",
    response_model=DeleteResponse,
)
async def remove_question(
    question_id: str,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: QuestionService = Depends(get_question_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Deletes a question by ID (requires ADMIN or EDITOR role)."""
    result = await service.delete_question(question_id)
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.QUESTION_DELETED.value,
        resource_type=AuditResourceType.QUESTION.value,
        resource_id=question_id,
        request=request,
    )
    return result

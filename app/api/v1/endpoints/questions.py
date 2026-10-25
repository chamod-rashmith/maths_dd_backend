"""
FastAPI Router for v1 Questions and Marking Schemes operations.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_question_repository
from app.core.security import get_current_user
from app.domain.repositories.question_repository import QuestionRepository
from app.schemas.question import (
    QuestionCreate,
    QuestionSummaryResponse,
    QuestionWithSolutionResponse,
)

router = APIRouter(prefix="/questions", tags=["Questions v1"])


@router.get("/recent", response_model=List[QuestionSummaryResponse])
async def list_recent_questions(
    limit: int = Query(15, ge=1, le=100),
    repo: QuestionRepository = Depends(get_question_repository),
) -> List[Dict[str, Any]]:
    """Fetches the latest questions stored in Cloud SQL."""
    try:
        return await repo.get_recent(limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("", response_model=QuestionWithSolutionResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    q: QuestionCreate,
    _current_user: Dict[str, Any] = Depends(get_current_user),
    repo: QuestionRepository = Depends(get_question_repository),
) -> Dict[str, Any]:
    """Creates a new question with its corresponding marking scheme in Cloud SQL."""
    try:
        return await repo.create_question_with_solution(
            title=q.title,
            subject_id=q.subject_id,
            lesson_id=q.lesson_id,
            content_text=q.content_text,
            solution_text=q.solution_text,
            solution_title=q.solution_title,
            question_type=q.question_type,
            difficulty=q.difficulty,
            schedule=q.schedule,
            source=q.source,
            source_details=q.source_details or "",
            allocated_marks=q.allocated_marks,
            is_premium=q.is_premium,
            is_published=q.is_published,
            scheduled_date=q.scheduled_date,
            custom_id=q.custom_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

"""
FastAPI Router for v1 Questions and Marking Schemes operations.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_question_service, require_admin_or_editor
from app.schemas.question import (
    QuestionCreate,
    QuestionSummaryResponse,
    QuestionWithSolutionResponse,
)
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["Questions v1"])


@router.get("/recent", response_model=List[QuestionSummaryResponse])
async def list_recent_questions(
    limit: int = Query(15, ge=1, le=100),
    service: QuestionService = Depends(get_question_service),
) -> List[Dict[str, Any]]:
    """Fetches the latest questions stored in Cloud SQL."""
    return await service.list_recent_questions(limit=limit)


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
    """Creates a new question with its corresponding marking scheme (requires ADMIN or EDITOR role)."""
    return await service.create_question(q)

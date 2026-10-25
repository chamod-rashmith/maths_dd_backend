"""
FastAPI Router for v1 Curriculum (Subjects & Syllabus Lessons) operations.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_curriculum_repository
from app.core.security import get_current_user
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.schemas.curriculum import (
    LessonCreate,
    LessonResponse,
    SubjectCreate,
    SubjectResponse,
)

router = APIRouter(prefix="/curriculum", tags=["Curriculum v1"])


@router.get("/subjects", response_model=List[SubjectResponse])
async def list_subjects(
    repo: CurriculumRepository = Depends(get_curriculum_repository),
) -> List[Dict[str, Any]]:
    """Fetches syllabus subjects."""
    try:
        return await repo.get_subjects()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def add_subject(
    sub: SubjectCreate,
    _current_user: Dict[str, Any] = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repository),
) -> Dict[str, Any]:
    """Creates or updates a syllabus subject."""
    try:
        return await repo.upsert_subject(
            subject_id=sub.id,
            name=sub.name,
            sinhala_name=sub.sinhala_name or "",
            code=sub.code,
            order_index=sub.order_index,
            description=sub.description or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.delete("/subjects/{subject_id}")
async def remove_subject(
    subject_id: str,
    _current_user: Dict[str, Any] = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repository),
) -> Dict[str, Any]:
    """Deletes a syllabus subject by ID."""
    try:
        return await repo.delete_subject(subject_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/lessons", response_model=List[LessonResponse])
async def list_lessons(
    subject_id: Optional[str] = Query(None),
    repo: CurriculumRepository = Depends(get_curriculum_repository),
) -> List[Dict[str, Any]]:
    """Fetches syllabus lessons, optionally filtered by subject ID."""
    try:
        return await repo.get_lessons(subject_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def add_lesson(
    les: LessonCreate,
    _current_user: Dict[str, Any] = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repository),
) -> Dict[str, Any]:
    """Creates or updates a syllabus lesson."""
    try:
        return await repo.upsert_lesson(
            lesson_id=les.id,
            subject_id=les.subject_id,
            title=les.title,
            sinhala_title=les.sinhala_title or "",
            order_index=les.order_index,
            description=les.description or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

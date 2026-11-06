"""
FastAPI Router for v1 Curriculum (Subjects & Syllabus Lessons) operations.

===============================================================================
Curriculum API Endpoints (v1):
-------------------------------------------------------------------------------
1. `GET /subjects` - විෂයයන් ලැයිස්තුව.
2. `POST /subjects` - විෂයයක් ඇතුළත් කිරීම (Admin only).
3. `DELETE /subjects/{id}` - විෂයයක් ඉවත් කිරීම (Admin only).
4. `GET /lessons` - පාඩම් ලැයිස්තුව. `subject_code`, `subject_id`, `parent_lesson_id`,
   සහ `root_only` මඟින් units සහ hierarchical sub-lessons filter කළ හැක.
5. `POST /lessons` - පාඩමක් හෝ උප-පාඩමක් ඇතුළත් කිරීම (Admin only).
6. `DELETE /lessons/{id}` - පාඩමක් ඉවත් කිරීම (Admin only).
===============================================================================
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_admin_audit_service,
    get_curriculum_service,
    require_admin_or_editor,
)
from app.domain.enums import AuditAction, AuditResourceType
from app.schemas.common import DeleteResponse
from app.schemas.curriculum import (
    LessonCreate,
    LessonResponse,
    SubjectCreate,
    SubjectResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.curriculum_service import CurriculumService

router = APIRouter(prefix="/curriculum", tags=["Curriculum v1"])


@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(
    service: CurriculumService = Depends(get_curriculum_service),
) -> list[dict[str, Any]]:
    """Fetches syllabus subjects (cached via Redis/TTL cache)."""
    return await service.list_subjects()


@router.post(
    "/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_subject(
    sub: SubjectCreate,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: CurriculumService = Depends(get_curriculum_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Creates or updates a syllabus subject with auto UUIDv4 generation (requires ADMIN or EDITOR role)."""
    result = await service.upsert_subject(sub)
    sub_id = (result.get("id") if isinstance(result, dict) else None) or sub.id
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.SUBJECT_UPSERTED.value,
        resource_type=AuditResourceType.SUBJECT.value,
        resource_id=str(sub_id) if sub_id else None,
        request=request,
        details={"name": sub.name, "code": sub.code},
    )
    return result


@router.delete(
    "/subjects/{subject_id}",
    response_model=DeleteResponse,
)
async def remove_subject(
    subject_id: str,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: CurriculumService = Depends(get_curriculum_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Deletes a syllabus subject by ID (requires ADMIN or EDITOR role)."""
    result = await service.delete_subject(subject_id)
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.SUBJECT_DELETED.value,
        resource_type=AuditResourceType.SUBJECT.value,
        resource_id=subject_id,
        request=request,
    )
    return result


@router.get("/lessons", response_model=list[LessonResponse])
async def list_lessons(
    subject_code: str | None = Query(
        None,
        description="Filter lessons by human-readable subject code (e.g. 'AMAT', 'PMAT')",
    ),
    subject_id: str | None = Query(
        None,
        description="Filter lessons by subject UUID or ID (fallback)",
    ),
    parent_lesson_id: str | None = Query(
        None,
        description="Filter sub-lessons belonging to a parent unit UUID/ID (උදා: 'les_trig')",
    ),
    root_only: bool = Query(
        False,
        description="If True, returns only top-level units (parent_lesson_id IS NULL)",
    ),
    service: CurriculumService = Depends(get_curriculum_service),
) -> list[dict[str, Any]]:
    """
    Fetches syllabus lessons.
    Supports filtering by subject (`?subject_code=PMAT`), parent unit (`?parent_lesson_id=les_trig`),
    or top-level units only (`?root_only=true`).
    """
    return await service.list_lessons(
        subject_id=subject_id,
        subject_code=subject_code,
        parent_lesson_id=parent_lesson_id,
        root_only=root_only,
    )


@router.post(
    "/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_lesson(
    les: LessonCreate,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: CurriculumService = Depends(get_curriculum_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Creates or updates a syllabus lesson/sub-lesson with auto UUIDv4 generation (requires ADMIN or EDITOR role)."""
    result = await service.upsert_lesson(les)
    les_id = (result.get("id") if isinstance(result, dict) else None) or les.id
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.LESSON_UPSERTED.value,
        resource_type=AuditResourceType.LESSON.value,
        resource_id=str(les_id) if les_id else None,
        request=request,
        details={"title": les.title, "subject_id": les.subject_id},
    )
    return result


@router.delete(
    "/lessons/{lesson_id}",
    response_model=DeleteResponse,
)
async def remove_lesson(
    lesson_id: str,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin_or_editor),
    service: CurriculumService = Depends(get_curriculum_service),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> dict[str, Any]:
    """Deletes a syllabus lesson by ID (requires ADMIN or EDITOR role)."""
    result = await service.delete_lesson(lesson_id)
    await audit_service.record_action(
        actor=_admin,
        action=AuditAction.LESSON_DELETED.value,
        resource_type=AuditResourceType.LESSON.value,
        resource_id=lesson_id,
        request=request,
    )
    return result

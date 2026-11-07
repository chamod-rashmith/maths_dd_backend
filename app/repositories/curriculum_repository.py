"""
Concrete PostgreSQL Implementation of CurriculumRepository using SQLAlchemy 2.0.

===============================================================================
විෂය නිර්දේශයේ දත්ත ගබඩා මෙහෙයුම් (Postgres Curriculum Repository):
-------------------------------------------------------------------------------
1. Subjects (විෂයයන්) විමසීම, නිර්මාණය, සහ මකා දැමීම.
2. Syllabus Lessons සහ Hierarchical Sub-lessons (ප්‍රධාන පාඩම් සහ උප පාඩම්)
   කළමනාකරණය:
   - `parent_lesson_id` filter මඟින් කිසියම් unit එකක sub-topics පමණක් ලබාගැනීම.
   - `root_only=True` මඟින් ප්‍රධාන ඒකක (Root units) පමණක් ලබාගැනීම.
   - සම්පූර්ණ ලැයිස්තුව (All units & sub-lessons) එකවර ලබාගැනීම.
===============================================================================
"""

import datetime
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.models.lesson import SyllabusLesson
from app.models.question import Question
from app.models.subject import Subject

_SL_TZ = ZoneInfo("Asia/Colombo")


def _serialize_subject(subj: Subject) -> Dict[str, Any]:
    """Serializes a Subject SQLAlchemy model into a clean dictionary."""
    return {
        "id": subj.id,
        "name": subj.name,
        "sinhala_name": subj.sinhala_name,
        "code": subj.code,
        "description": subj.description,
    }


def _serialize_lesson(lesson: SyllabusLesson) -> Dict[str, Any]:
    """Serializes a SyllabusLesson SQLAlchemy model with parent_lesson_id into a clean dictionary."""
    return {
        "id": lesson.id,
        "subject_id": lesson.subject_id,
        "parent_lesson_id": lesson.parent_lesson_id,
        "title": lesson.title,
        "sinhala_title": lesson.sinhala_title,
        "description": lesson.description,
        "question_count": lesson.question_count,
        "premium_count": lesson.premium_count,
    }


class PostgresCurriculumRepository(CurriculumRepository):
    """PostgreSQL implementation of `CurriculumRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_subjects(self) -> List[Dict[str, Any]]:
        """Fetches all subjects sorted by order_index ascending."""
        try:
            stmt = select(
                Subject.id,
                Subject.name,
                Subject.sinhala_name,
                Subject.code,
                Subject.description,
            ).order_by(Subject.order_index.asc())
            result = await self._session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def upsert_subject(
        self,
        subject_id: Optional[str],
        name: str,
        sinhala_name: str,
        code: str,
        order_index: int,
        description: str = "",
    ) -> Dict[str, Any]:
        """Creates or updates a Subject record."""
        cleaned_code = code.strip().upper()
        try:
            subj: Optional[Subject] = None
            if subject_id and subject_id.strip():
                subj = (
                    await self._session.execute(
                        select(Subject).where(Subject.id == subject_id.strip())
                    )
                ).scalar_one_or_none()

            if not subj:
                subj = (
                    await self._session.execute(
                        select(Subject).where(func.upper(Subject.code) == cleaned_code)
                    )
                ).scalar_one_or_none()

            if subj:
                subj.name = name
                subj.sinhala_name = sinhala_name
                subj.code = cleaned_code
                subj.order_index = order_index
                subj.description = description
            else:
                resolved_id = (
                    subject_id.strip()
                    if (subject_id and subject_id.strip())
                    else str(uuid.uuid4())
                )
                subj = Subject(
                    id=resolved_id,
                    name=name,
                    sinhala_name=sinhala_name,
                    code=cleaned_code,
                    order_index=order_index,
                    description=description,
                )
                self._session.add(subj)

            await self._session.flush()
            await self._session.refresh(subj)
            return _serialize_subject(subj)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        """Deletes a Subject record and cascades to its lessons."""
        try:
            subj = (
                await self._session.execute(
                    select(Subject).where(Subject.id == subject_id)
                )
            ).scalar_one_or_none()

            deleted_id = subject_id
            if subj:
                deleted_id = subj.id
                await self._session.delete(subj)
                await self._session.flush()

            return {
                "status": "success",
                "deleted_id": deleted_id,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_lessons(
        self,
        subject_id: Optional[str] = None,
        subject_code: Optional[str] = None,
        parent_lesson_id: Optional[str] = None,
        root_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetches syllabus lessons with real-time question counts.
        Supports filtering by subject, parent_lesson_id (for subtopics), or root_only (for main units).
        """
        try:
            today_colombo = datetime.datetime.now(_SL_TZ).date()

            q_count = func.count(Question.id).label("question_count")
            prem_count = func.count(
                case((Question.is_premium.is_(True), Question.id), else_=None)
            ).label("premium_count")

            stmt = (
                select(
                    SyllabusLesson.id,
                    SyllabusLesson.subject_id,
                    SyllabusLesson.parent_lesson_id,
                    SyllabusLesson.title,
                    SyllabusLesson.sinhala_title,
                    SyllabusLesson.description,
                    q_count,
                    prem_count,
                )
                .join(Subject, SyllabusLesson.subject_id == Subject.id)
                .outerjoin(
                    Question,
                    and_(
                        Question.lesson_id == SyllabusLesson.id,
                        Question.is_published.is_(True),
                        Question.is_deleted.is_(False),
                        or_(
                            Question.scheduled_date.is_(None),
                            Question.scheduled_date <= today_colombo,
                        ),
                    ),
                )
            )

            # Subject filter
            raw_filter = (subject_code or subject_id or "").strip()
            if raw_filter:
                stmt = stmt.where(
                    or_(
                        SyllabusLesson.subject_id == raw_filter,
                        func.upper(Subject.code) == raw_filter.upper(),
                        and_(
                            Subject.code == "PMAT",
                            func.lower(raw_filter).in_(
                                ["pure_maths", "puremaths", "pure", "subj_pmat"]
                            ),
                        ),
                        and_(
                            Subject.code == "AMAT",
                            func.lower(raw_filter).in_(
                                ["applied_maths", "appliedmaths", "applied", "subj_amat"]
                            ),
                        ),
                    )
                )

            # Hierarchy filter: specific parent unit or top-level units only
            if parent_lesson_id and parent_lesson_id.strip():
                stmt = stmt.where(SyllabusLesson.parent_lesson_id == parent_lesson_id.strip())
            elif root_only:
                stmt = stmt.where(SyllabusLesson.parent_lesson_id.is_(None))

            stmt = stmt.group_by(
                SyllabusLesson.id,
                SyllabusLesson.parent_lesson_id,
                Subject.order_index,
            ).order_by(Subject.order_index.asc(), SyllabusLesson.order_index.asc())

            result = await self._session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def upsert_lesson(
        self,
        lesson_id: Optional[str],
        subject_id: str,
        title: str,
        sinhala_title: str,
        order_index: int,
        description: str = "",
        parent_lesson_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates or updates a SyllabusLesson record (supporting hierarchical units and sub-lessons).
        """
        try:
            lesson: Optional[SyllabusLesson] = None
            if lesson_id and lesson_id.strip():
                lesson = (
                    await self._session.execute(
                        select(SyllabusLesson).where(
                            SyllabusLesson.id == lesson_id.strip()
                        )
                    )
                ).scalar_one_or_none()

            resolved_parent_id = (
                parent_lesson_id.strip()
                if (parent_lesson_id and parent_lesson_id.strip())
                else None
            )

            if lesson:
                lesson.subject_id = subject_id
                lesson.parent_lesson_id = resolved_parent_id
                lesson.title = title
                lesson.sinhala_title = sinhala_title
                lesson.order_index = order_index
                lesson.description = description
            else:
                resolved_id = (
                    lesson_id.strip()
                    if (lesson_id and lesson_id.strip())
                    else str(uuid.uuid4())
                )
                lesson = SyllabusLesson(
                    id=resolved_id,
                    subject_id=subject_id,
                    parent_lesson_id=resolved_parent_id,
                    title=title,
                    sinhala_title=sinhala_title,
                    order_index=order_index,
                    description=description,
                )
                self._session.add(lesson)

            await self._session.flush()
            await self._session.refresh(lesson)
            return _serialize_lesson(lesson)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_lesson(self, lesson_id: str) -> Dict[str, Any]:
        """Deletes a SyllabusLesson record and cascades to its sub-lessons."""
        try:
            lesson = (
                await self._session.execute(
                    select(SyllabusLesson).where(SyllabusLesson.id == lesson_id)
                )
            ).scalar_one_or_none()

            deleted_id = lesson_id
            if lesson:
                deleted_id = lesson.id
                await self._session.delete(lesson)
                await self._session.flush()

            return {
                "status": "success",
                "deleted_id": deleted_id,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

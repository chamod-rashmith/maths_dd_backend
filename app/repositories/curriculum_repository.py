"""
Concrete PostgreSQL Implementation of CurriculumRepository using SQLAlchemy 2.0.
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


class PostgresCurriculumRepository(CurriculumRepository):
    """PostgreSQL implementation of `CurriculumRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_subjects(self) -> List[Dict[str, Any]]:
        try:
            result = await self._session.execute(
                select(Subject).order_by(Subject.order_index.asc())
            )
            subjects = result.scalars().all()
            return [s.to_dict() for s in subjects]
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
            return subj.to_dict()
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
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
    ) -> List[Dict[str, Any]]:
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
                    SyllabusLesson.title,
                    SyllabusLesson.sinhala_title,
                    SyllabusLesson.order_index,
                    SyllabusLesson.description,
                    q_count,
                    prem_count,
                    SyllabusLesson.created_at,
                    SyllabusLesson.updated_at,
                    Subject.code.label("subject_code"),
                    Subject.name.label("subject_name"),
                )
                .join(Subject, SyllabusLesson.subject_id == Subject.id)
                .outerjoin(
                    Question,
                    and_(
                        Question.lesson_id == SyllabusLesson.id,
                        Question.is_published.is_(True),
                        or_(
                            Question.scheduled_date.is_(None),
                            Question.scheduled_date <= today_colombo,
                        ),
                    ),
                )
            )

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

            stmt = stmt.group_by(
                SyllabusLesson.id,
                Subject.order_index,
                Subject.code,
                Subject.name,
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
    ) -> Dict[str, Any]:
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

            if lesson:
                lesson.subject_id = subject_id
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
                    title=title,
                    sinhala_title=sinhala_title,
                    order_index=order_index,
                    description=description,
                )
                self._session.add(lesson)

            await self._session.flush()
            await self._session.refresh(lesson)
            return lesson.to_dict()
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_lesson(self, lesson_id: str) -> Dict[str, Any]:
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

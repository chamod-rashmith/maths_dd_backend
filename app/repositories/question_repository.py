"""
PostgreSQL Repository implementation for Questions and Marking Schemes using SQLAlchemy 2.0 AsyncSession.
Supports single questions, dynamic multi-question daily packs, and chronological daily challenge series.
Auto-sorts questions by Combined Maths canonical hierarchy:
Pure Short (Part A) -> Pure Essay (Part B) -> Applied Short (Part A) -> Applied Essay (Part B).
"""

import datetime
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Date,
    and_,
    case,
    cast,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.question_repository import QuestionRepository
from app.models.lesson import SyllabusLesson
from app.models.marking_scheme import MarkingScheme
from app.models.question import Question
from app.models.subject import Subject

_SL_TZ = ZoneInfo("Asia/Colombo")


def _resolve_colombo_date(target_date: Optional[str] = None) -> datetime.date:
    """Resolves a target YYYY-MM-DD string or defaults to current date in Asia/Colombo."""
    if target_date and str(target_date).strip():
        try:
            raw = str(target_date).strip()[:10]
            return datetime.date.fromisoformat(raw)
        except (ValueError, TypeError):
            pass
    return datetime.datetime.now(_SL_TZ).date()


def _question_select_stmt():
    """Builds the canonical SQLAlchemy select statement for questions with joined relations."""
    content_type_case = case(
        (
            and_(Question.content_url.isnot(None), Question.content_url != ""),
            case(
                (
                    or_(
                        Question.content_url.ilike("%.png%"),
                        Question.content_url.ilike("%.jpg%"),
                        Question.content_url.ilike("%.jpeg%"),
                        Question.content_url.ilike("%.webp%"),
                    ),
                    "image",
                ),
                else_="pdf",
            ),
        ),
        else_="markdown",
    ).label("content_type")

    has_ms_subquery = (
        select(literal(1))
        .where(
            MarkingScheme.question_id == Question.id,
            or_(
                and_(MarkingScheme.content_text.isnot(None), MarkingScheme.content_text != ""),
                and_(MarkingScheme.pdf_url.isnot(None), MarkingScheme.pdf_url != ""),
            ),
        )
        .exists()
        .label("has_marking_scheme")
    )

    return (
        select(
            Question.id,
            Question.title,
            func.coalesce(Question.description, "").label("description"),
            Question.subject_id,
            Question.lesson_id,
            func.coalesce(Question.content_text, "").label("content_text"),
            Question.content_url,
            content_type_case,
            Question.type,
            Question.difficulty,
            Question.schedule,
            Question.source,
            func.coalesce(Question.source_details, "").label("source_details"),
            Question.allocated_marks,
            Question.is_premium,
            Question.is_published,
            Question.scheduled_date,
            Question.day_number,
            has_ms_subquery,
            Subject.code.label("subject_code"),
            Subject.name.label("subject_name"),
            SyllabusLesson.title.label("lesson_title"),
            SyllabusLesson.sinhala_title.label("lesson_sinhala_title"),
        )
        .outerjoin(Subject, Question.subject_id == Subject.id)
        .outerjoin(SyllabusLesson, Question.lesson_id == SyllabusLesson.id)
        .where(Question.is_deleted.is_(False))
    )


class PostgresQuestionRepository(QuestionRepository):
    """PostgreSQL implementation of `QuestionRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_question_with_solution(
        self,
        title: str,
        subject_id: str,
        lesson_id: Optional[str],
        content_text: str,
        solution_text: str,
        description: str = "",
        content_url: Optional[str] = None,
        solution_pdf_url: Optional[str] = None,
        solution_title: str = "Official Marking Scheme",
        question_type: str = "SHORT",
        difficulty: str = "MEDIUM",
        schedule: str = "REGULAR",
        source: str = "PAST_PAPER",
        source_details: str = "",
        allocated_marks: int = 25,
        is_premium: bool = False,
        is_published: bool = True,
        scheduled_date: Optional[str] = None,
        day_number: Optional[int] = None,
        custom_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atomically creates or updates a question along with its official marking scheme."""
        try:
            q_id = custom_id.strip() if (custom_id and custom_id.strip()) else str(uuid.uuid4())
            cleaned_lesson_id = lesson_id.strip() if (lesson_id and lesson_id.strip()) else None

            parsed_date: Optional[datetime.date] = None
            if scheduled_date and str(scheduled_date).strip():
                try:
                    parsed_date = datetime.date.fromisoformat(str(scheduled_date).strip()[:10])
                except (ValueError, TypeError):
                    parsed_date = None

            effective_schedule = schedule
            if (parsed_date is not None or day_number is not None) and effective_schedule == "REGULAR":
                effective_schedule = "DAILY"

            cleaned_content_url = content_url.strip() if (content_url and content_url.strip()) else None

            # Upsert Question entity
            q = (
                await self._session.execute(
                    select(Question).where(Question.id == q_id)
                )
            ).scalar_one_or_none()

            if q:
                q.title = title
                q.description = description or ""
                q.subject_id = subject_id
                q.lesson_id = cleaned_lesson_id
                q.content_text = content_text or ""
                q.content_url = cleaned_content_url
                q.type = question_type
                q.difficulty = difficulty
                q.schedule = effective_schedule
                q.source = source
                q.source_details = source_details or ""
                q.allocated_marks = allocated_marks
                q.is_premium = is_premium
                q.is_published = is_published
                q.is_deleted = False
                q.scheduled_date = parsed_date
                q.day_number = day_number
            else:
                q = Question(
                    id=q_id,
                    title=title,
                    description=description or "",
                    subject_id=subject_id,
                    lesson_id=cleaned_lesson_id,
                    content_text=content_text or "",
                    content_url=cleaned_content_url,
                    type=question_type,
                    difficulty=difficulty,
                    schedule=effective_schedule,
                    source=source,
                    source_details=source_details or "",
                    allocated_marks=allocated_marks,
                    is_premium=is_premium,
                    is_published=is_published,
                    scheduled_date=parsed_date,
                    day_number=day_number,
                )
                self._session.add(q)

            await self._session.flush()

            # Upsert MarkingScheme entity
            ms = (
                await self._session.execute(
                    select(MarkingScheme)
                    .where(MarkingScheme.question_id == q_id)
                    .order_by(MarkingScheme.order_index.asc())
                )
            ).scalars().first()

            cleaned_sol_pdf = solution_pdf_url.strip() if (solution_pdf_url and solution_pdf_url.strip()) else None

            if ms:
                ms.title = solution_title
                ms.content_text = solution_text or ""
                ms.pdf_url = cleaned_sol_pdf
                ms.total_marks = allocated_marks
                ms.is_premium_only = is_premium
            else:
                ms = MarkingScheme(
                    id=uuid.uuid4(),
                    question_id=q_id,
                    title=solution_title,
                    content_text=solution_text or "",
                    pdf_url=cleaned_sol_pdf,
                    total_marks=allocated_marks,
                    is_official=True,
                    is_premium_only=is_premium,
                    order_index=1,
                )
                self._session.add(ms)

            await self._session.flush()

            created_question = await self.get_by_id(q_id)
            created_solution = await self.get_marking_scheme(q_id)

            return {
                "question": created_question or {
                    "id": q_id,
                    "title": title,
                    "description": description or "",
                    "subject_id": subject_id,
                    "lesson_id": cleaned_lesson_id,
                    "content_text": content_text or "",
                    "content_url": cleaned_content_url,
                    "content_type": "pdf" if (cleaned_content_url and cleaned_content_url.endswith(".pdf")) else "markdown",
                    "type": question_type,
                    "difficulty": difficulty,
                    "schedule": effective_schedule,
                    "source": source,
                    "source_details": source_details or "",
                    "allocated_marks": allocated_marks,
                    "is_premium": is_premium,
                    "is_published": is_published,
                    "scheduled_date": parsed_date,
                    "day_number": day_number,
                    "has_marking_scheme": True,
                },
                "marking_scheme": created_solution,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def list_questions(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        schedule: Optional[str] = None,
        source: Optional[str] = None,
        is_premium: Optional[bool] = None,
        include_unpublished: bool = False,
        day_number: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Lists filtered and paginated question summaries."""
        try:
            today_colombo = datetime.datetime.now(_SL_TZ).date()
            stmt = _question_select_stmt()

            if not include_unpublished:
                stmt = stmt.where(
                    Question.is_published.is_(True),
                    or_(
                        Question.scheduled_date.is_(None),
                        Question.scheduled_date <= today_colombo,
                    ),
                )

            if subject_id and subject_id.strip():
                sid = subject_id.strip()
                stmt = stmt.where(
                    or_(
                        Question.subject_id == sid,
                        func.upper(Subject.code) == sid.upper(),
                        and_(
                            Subject.code == "PMAT",
                            sid.lower() in ("pure_maths", "puremaths", "pure", "subj_pmat"),
                        ),
                        and_(
                            Subject.code == "AMAT",
                            sid.lower() in ("applied_maths", "appliedmaths", "applied", "subj_amat"),
                        ),
                    )
                )

            if lesson_id and lesson_id.strip():
                stmt = stmt.where(Question.lesson_id == lesson_id.strip())

            if question_type and question_type.strip():
                stmt = stmt.where(func.upper(Question.type) == question_type.strip().upper())

            if difficulty and difficulty.strip():
                stmt = stmt.where(func.upper(Question.difficulty) == difficulty.strip().upper())

            if schedule and schedule.strip():
                stmt = stmt.where(func.upper(Question.schedule) == schedule.strip().upper())

            if source and source.strip():
                stmt = stmt.where(func.upper(Question.source) == source.strip().upper())

            if is_premium is not None:
                stmt = stmt.where(Question.is_premium.is_(is_premium))

            if day_number is not None:
                stmt = stmt.where(Question.day_number == day_number)

            stmt = (
                stmt.order_by(
                    func.coalesce(Question.scheduled_date, cast(Question.created_at, Date)).desc(),
                    Question.created_at.desc(),
                )
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_recent(self, limit: int = 15) -> List[Dict[str, Any]]:
        return await self.list_questions(include_unpublished=True, limit=limit, offset=0)

    async def get_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        try:
            stmt = _question_select_stmt().where(Question.id == question_id.strip())
            result = await self._session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_daily_question(
        self, target_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetches a single daily question for backward compatibility with older client builds."""
        resolved_date = _resolve_colombo_date(target_date)
        try:
            # 1. Exact match on scheduled_date
            stmt1 = (
                _question_select_stmt()
                .where(
                    Question.is_published.is_(True),
                    Question.scheduled_date == resolved_date,
                )
                .order_by(Question.updated_at.desc())
                .limit(1)
            )
            result1 = await self._session.execute(stmt1)
            row = result1.mappings().first()
            if row:
                d = dict(row)
                d["schedule"] = "DAILY"
                return d

            # 2. Fallback to latest scheduled question on or before resolved_date
            stmt2 = (
                _question_select_stmt()
                .where(
                    Question.is_published.is_(True),
                    Question.scheduled_date.isnot(None),
                    Question.scheduled_date <= resolved_date,
                )
                .order_by(Question.scheduled_date.desc(), Question.updated_at.desc())
                .limit(1)
            )
            result2 = await self._session.execute(stmt2)
            row2 = result2.mappings().first()
            if row2:
                d = dict(row2)
                d["schedule"] = "DAILY"
                return d

            return None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_daily_pack(
        self,
        target_date: Optional[str] = None,
        day_number: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches the complete multi-question daily challenge pack for target calendar date or day number.
        Auto-sorts questions by Combined Maths canonical hierarchy:
        Pure Short (Part A) -> Pure Essay (Part B) -> Applied Short (Part A) -> Applied Essay (Part B).
        """
        canonical_sort_order = [
            case((func.upper(Subject.code) == "PMAT", 1), (func.upper(Subject.code) == "AMAT", 2), else_=3),
            case((func.upper(Question.type) == "SHORT", 1), (func.upper(Question.type) == "ESSAY", 2), else_=3),
            Question.allocated_marks.asc(),
            Question.id.asc(),
        ]

        try:
            # Case A: Explicit day_number lookup (e.g. ?day=1)
            if day_number is not None and day_number > 0:
                stmt = (
                    _question_select_stmt()
                    .where(
                        Question.is_published.is_(True),
                        Question.day_number == day_number,
                    )
                    .order_by(*canonical_sort_order)
                )
                result = await self._session.execute(stmt)
                rows = result.mappings().all()
                if rows:
                    questions = [dict(r) for r in rows]
                    day_num = day_number or 1
                    for q in questions:
                        if q.get("day_number") is None:
                            q["day_number"] = day_num
                    return {
                        "day_number": day_num,
                        "challenge_title": f"Day {day_num} Combined Maths Challenge",
                        "scheduled_date": questions[0].get("scheduled_date"),
                        "total_questions": len(questions),
                        "total_marks": sum(q.get("allocated_marks", 0) for q in questions),
                        "questions": questions,
                    }
                return None

            # Case B: Calendar date resolution
            resolved_date = _resolve_colombo_date(target_date)

            # Step 1: Exact match on scheduled_date
            stmt1 = (
                _question_select_stmt()
                .where(
                    Question.is_published.is_(True),
                    Question.scheduled_date == resolved_date,
                )
                .order_by(*canonical_sort_order)
            )
            result1 = await self._session.execute(stmt1)
            rows1 = result1.mappings().all()
            if rows1:
                questions = [dict(r) for r in rows1]
                day_num = questions[0].get("day_number") or 1
                for q in questions:
                    if q.get("day_number") is None:
                        q["day_number"] = day_num
                return {
                    "day_number": day_num,
                    "challenge_title": f"Day {day_num} Combined Maths Challenge",
                    "scheduled_date": resolved_date,
                    "total_questions": len(questions),
                    "total_marks": sum(q.get("allocated_marks", 0) for q in questions),
                    "questions": questions,
                }

            # Step 2: Fallback to questions with the latest scheduled_date on or before resolved_date
            latest_date_stmt = (
                select(Question.scheduled_date)
                .where(
                    Question.is_published.is_(True),
                    Question.scheduled_date.isnot(None),
                    Question.scheduled_date <= resolved_date,
                    Question.is_deleted.is_(False),
                )
                .order_by(Question.scheduled_date.desc())
                .limit(1)
            )
            latest_date_res = await self._session.execute(latest_date_stmt)
            latest_date = latest_date_res.scalar_one_or_none()

            if latest_date:
                stmt2 = (
                    _question_select_stmt()
                    .where(
                        Question.is_published.is_(True),
                        Question.scheduled_date == latest_date,
                    )
                    .order_by(*canonical_sort_order)
                )
                result2 = await self._session.execute(stmt2)
                rows2 = result2.mappings().all()
                if rows2:
                    questions = [dict(r) for r in rows2]
                    day_num = questions[0].get("day_number") or 1
                    for q in questions:
                        if q.get("day_number") is None:
                            q["day_number"] = day_num
                    return {
                        "day_number": day_num,
                        "challenge_title": f"Day {day_num} Combined Maths Challenge",
                        "scheduled_date": latest_date,
                        "total_questions": len(questions),
                        "total_marks": sum(q.get("allocated_marks", 0) for q in questions),
                        "questions": questions,
                    }

            return None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def list_daily_series(
        self,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Lists available daily challenge series summaries grouped by day number (Day 1, Day 2...).
        Allows students to browse past daily challenges chronologically.
        """
        today_colombo = datetime.datetime.now(_SL_TZ).date()
        try:
            stmt = (
                select(
                    Question.day_number,
                    Question.scheduled_date,
                    func.count(Question.id).label("total_questions"),
                    func.sum(Question.allocated_marks).label("total_marks"),
                )
                .where(
                    Question.is_published.is_(True),
                    Question.is_deleted.is_(False),
                    Question.day_number.isnot(None),
                )
                .group_by(Question.day_number, Question.scheduled_date)
                .order_by(Question.day_number.asc())
                .limit(limit)
                .offset(offset)
            )
            result = await self._session.execute(stmt)
            rows = result.mappings().all()
            series = []
            for r in rows:
                d = dict(r)
                day_num = d.get("day_number")
                sched_date = d.get("scheduled_date")
                is_unlocked = True if (sched_date is None or sched_date <= today_colombo) else False
                series.append({
                    "day_number": day_num,
                    "scheduled_date": sched_date,
                    "title": f"Day {day_num:02d} Challenge Workout",
                    "total_questions": d.get("total_questions", 0),
                    "total_marks": d.get("total_marks", 0),
                    "is_unlocked": is_unlocked,
                })
            return series
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_marking_scheme(
        self, question_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            stmt = (
                select(
                    MarkingScheme.id,
                    MarkingScheme.question_id,
                    MarkingScheme.title,
                    func.coalesce(MarkingScheme.content_text, "").label("content_text"),
                    MarkingScheme.pdf_url,
                    case(
                        (
                            and_(MarkingScheme.pdf_url.isnot(None), MarkingScheme.pdf_url != ""),
                            "pdf",
                        ),
                        else_="markdown",
                    ).label("content_type"),
                    MarkingScheme.total_marks,
                    MarkingScheme.is_official,
                    MarkingScheme.is_premium_only,
                    MarkingScheme.order_index,
                )
                .where(MarkingScheme.question_id == question_id.strip())
                .order_by(MarkingScheme.order_index.asc())
                .limit(1)
            )
            result = await self._session.execute(stmt)
            row = result.mappings().first()
            if not row:
                return None
            res = dict(row)
            res["id"] = str(res["id"])
            return res
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_question(self, question_id: str) -> Dict[str, Any]:
        try:
            q = (
                await self._session.execute(
                    select(Question).where(
                        Question.id == question_id.strip(),
                        Question.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()

            if q:
                q.is_deleted = True
                await self._session.flush()

            return {
                "status": "success",
                "deleted_id": question_id.strip(),
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

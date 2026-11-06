"""
Concrete PostgreSQL Implementation of StudyNoteRepository using SQLAlchemy 2.0.
Optimized to exclude heavy content_text during catalog listings and omit internal audit timestamps.
"""

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.models.lesson import SyllabusLesson
from app.models.study_note import StudyNote
from app.models.subject import Subject


class PostgresStudyNoteRepository(StudyNoteRepository):
    """PostgreSQL implementation of `StudyNoteRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        try:
            content_type_case = case(
                (and_(StudyNote.pdf_url.isnot(None), StudyNote.pdf_url != ""), "pdf"),
                else_="markdown",
            ).label("content_type")

            stmt = (
                select(
                    StudyNote.id,
                    StudyNote.title,
                    StudyNote.description,
                    StudyNote.subject_id,
                    StudyNote.lesson_id,
                    content_type_case,
                    StudyNote.is_premium,
                    StudyNote.order_index,
                    StudyNote.author,
                    Subject.name.label("subject_name"),
                    Subject.sinhala_name.label("subject_sinhala_name"),
                    SyllabusLesson.title.label("lesson_title"),
                    SyllabusLesson.sinhala_title.label("lesson_sinhala_title"),
                )
                .outerjoin(Subject, StudyNote.subject_id == Subject.id)
                .outerjoin(SyllabusLesson, StudyNote.lesson_id == SyllabusLesson.id)
                .where(StudyNote.is_deleted.is_(False))
            )

            if subject_id and subject_id.strip():
                sid = subject_id.strip()
                stmt = stmt.where(
                    or_(
                        StudyNote.subject_id == sid,
                        func.upper(Subject.code) == sid.upper(),
                        and_(
                            Subject.code == "PMAT",
                            sid.lower() in ("pure_maths", "pure", "subj_pmat"),
                        ),
                        and_(
                            Subject.code == "AMAT",
                            sid.lower() in ("applied_maths", "applied", "subj_amat"),
                        ),
                    )
                )

            if lesson_id and lesson_id.strip():
                stmt = stmt.where(StudyNote.lesson_id == lesson_id.strip())

            if search and search.strip():
                pattern = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        StudyNote.title.ilike(pattern),
                        StudyNote.description.ilike(pattern),
                        StudyNote.author.ilike(pattern),
                    )
                )

            count_stmt = select(func.count()).select_from(
                stmt.order_by(None).subquery()
            )
            total = int((await self._session.execute(count_stmt)).scalar_one())

            stmt = (
                stmt.order_by(StudyNote.order_index.asc(), StudyNote.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(stmt)
            return {
                "items": [dict(row) for row in result.mappings().all()],
                "total": total,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        try:
            stmt = (
                select(
                    StudyNote.id,
                    StudyNote.title,
                    StudyNote.description,
                    StudyNote.subject_id,
                    StudyNote.lesson_id,
                    StudyNote.content_text,
                    StudyNote.pdf_url,
                    StudyNote.is_premium,
                    StudyNote.order_index,
                    StudyNote.author,
                    Subject.name.label("subject_name"),
                    Subject.sinhala_name.label("subject_sinhala_name"),
                    SyllabusLesson.title.label("lesson_title"),
                    SyllabusLesson.sinhala_title.label("lesson_sinhala_title"),
                )
                .outerjoin(Subject, StudyNote.subject_id == Subject.id)
                .outerjoin(SyllabusLesson, StudyNote.lesson_id == SyllabusLesson.id)
                .where(StudyNote.id == note_id, StudyNote.is_deleted.is_(False))
            )
            result = await self._session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def upsert(
        self,
        note_id: Optional[str],
        title: str,
        subject_id: str,
        lesson_id: Optional[str],
        content_text: Optional[str] = "",
        description: Optional[str] = "",
        pdf_url: Optional[str] = None,
        is_premium: bool = False,
        order_index: int = 0,
        author: Optional[str] = "",
    ) -> Dict[str, Any]:
        try:
            resolved_id = (
                note_id.strip()
                if (note_id and note_id.strip())
                else str(uuid.uuid4())
            )
            cleaned_lesson_id = (
                lesson_id.strip() if (lesson_id and lesson_id.strip()) else None
            )
            final_pdf = pdf_url.strip() if (pdf_url and pdf_url.strip()) else None
            final_content = (content_text or "").strip() if not final_pdf else ""

            note: Optional[StudyNote] = None
            if note_id and note_id.strip():
                note = (
                    await self._session.execute(
                        select(StudyNote).where(StudyNote.id == resolved_id)
                    )
                ).scalar_one_or_none()

            if note:
                note.title = title
                note.description = description or ""
                note.subject_id = subject_id
                note.lesson_id = cleaned_lesson_id
                note.content_text = final_content
                note.pdf_url = final_pdf
                note.is_premium = is_premium
                note.is_deleted = False
                note.order_index = order_index
                note.author = author or ""
            else:
                note = StudyNote(
                    id=resolved_id,
                    title=title,
                    description=description or "",
                    subject_id=subject_id,
                    lesson_id=cleaned_lesson_id,
                    content_text=final_content,
                    pdf_url=final_pdf,
                    is_premium=is_premium,
                    order_index=order_index,
                    author=author or "",
                )
                self._session.add(note)

            await self._session.flush()
            created_or_updated = await self.get_by_id(resolved_id)
            if created_or_updated:
                return created_or_updated

            return {
                "id": resolved_id,
                "title": title,
                "description": description or "",
                "subject_id": subject_id,
                "lesson_id": cleaned_lesson_id,
                "content_text": final_content,
                "pdf_url": final_pdf,
                "is_premium": is_premium,
                "order_index": order_index,
                "author": author or "",
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete(self, note_id: str) -> Dict[str, Any]:
        try:
            note = (
                await self._session.execute(
                    select(StudyNote).where(StudyNote.id == note_id, StudyNote.is_deleted.is_(False))
                )
            ).scalar_one_or_none()

            if note:
                note.is_deleted = True
                await self._session.flush()

            return {"status": "success", "deleted_id": note_id}
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

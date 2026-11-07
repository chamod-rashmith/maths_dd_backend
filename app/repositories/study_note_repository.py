"""
Concrete PostgreSQL Implementation of StudyNoteRepository using SQLAlchemy 2.0.
Optimized to exclude heavy content_text during catalog listings, omit internal audit timestamps,
and join normalized 3NF `study_note_votes` and `study_note_bookmarks` tables in a single query.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.models.lesson import SyllabusLesson
from app.models.study_note import StudyNote, StudyNoteBookmark, StudyNoteVote
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
        user_id: Optional[str] = None,
        bookmarked_only: bool = False,
    ) -> Dict[str, Any]:
        try:
            clean_user_id = user_id.strip() if (user_id and user_id.strip()) else None
            if bookmarked_only and not clean_user_id:
                return {"items": [], "total": 0}

            content_type_case = case(
                (and_(StudyNote.pdf_url.isnot(None), StudyNote.pdf_url != ""), "pdf"),
                else_="markdown",
            ).label("content_type")

            if clean_user_id:
                user_vote_col = func.coalesce(StudyNoteVote.vote_type, 0).label("user_vote")
                if bookmarked_only:
                    is_bookmarked_col = literal(True).label("is_bookmarked")
                else:
                    is_bookmarked_col = case(
                        (StudyNoteBookmark.id.isnot(None), True),
                        else_=False,
                    ).label("is_bookmarked")
            else:
                user_vote_col = literal(0).label("user_vote")
                is_bookmarked_col = literal(False).label("is_bookmarked")

            stmt = (
                select(
                    StudyNote.id,
                    StudyNote.title,
                    StudyNote.description,
                    StudyNote.subject_id,
                    StudyNote.lesson_id,
                    content_type_case,
                    StudyNote.is_premium,
                    StudyNote.author,
                    StudyNote.upvote_count,
                    StudyNote.downvote_count,
                    user_vote_col,
                    is_bookmarked_col,
                    Subject.name.label("subject_name"),
                    Subject.sinhala_name.label("subject_sinhala_name"),
                    SyllabusLesson.title.label("lesson_title"),
                    SyllabusLesson.sinhala_title.label("lesson_sinhala_title"),
                )
                .outerjoin(Subject, StudyNote.subject_id == Subject.id)
                .outerjoin(SyllabusLesson, StudyNote.lesson_id == SyllabusLesson.id)
            )

            if clean_user_id:
                stmt = stmt.outerjoin(
                    StudyNoteVote,
                    and_(
                        StudyNoteVote.note_id == StudyNote.id,
                        StudyNoteVote.user_id == clean_user_id,
                    ),
                )
                if bookmarked_only:
                    stmt = stmt.join(
                        StudyNoteBookmark,
                        and_(
                            StudyNoteBookmark.note_id == StudyNote.id,
                            StudyNoteBookmark.user_id == clean_user_id,
                        ),
                    )
                else:
                    stmt = stmt.outerjoin(
                        StudyNoteBookmark,
                        and_(
                            StudyNoteBookmark.note_id == StudyNote.id,
                            StudyNoteBookmark.user_id == clean_user_id,
                        ),
                    )

            stmt = stmt.where(StudyNote.is_deleted.is_(False))

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

    async def get_by_id(
        self,
        note_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            clean_user_id = user_id.strip() if (user_id and user_id.strip()) else None
            if clean_user_id:
                user_vote_col = func.coalesce(StudyNoteVote.vote_type, 0).label("user_vote")
                is_bookmarked_col = case(
                    (StudyNoteBookmark.id.isnot(None), True),
                    else_=False,
                ).label("is_bookmarked")
            else:
                user_vote_col = literal(0).label("user_vote")
                is_bookmarked_col = literal(False).label("is_bookmarked")

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
                    StudyNote.author,
                    StudyNote.upvote_count,
                    StudyNote.downvote_count,
                    user_vote_col,
                    is_bookmarked_col,
                    Subject.name.label("subject_name"),
                    Subject.sinhala_name.label("subject_sinhala_name"),
                    SyllabusLesson.title.label("lesson_title"),
                    SyllabusLesson.sinhala_title.label("lesson_sinhala_title"),
                )
                .outerjoin(Subject, StudyNote.subject_id == Subject.id)
                .outerjoin(SyllabusLesson, StudyNote.lesson_id == SyllabusLesson.id)
            )

            if clean_user_id:
                stmt = stmt.outerjoin(
                    StudyNoteVote,
                    and_(
                        StudyNoteVote.note_id == StudyNote.id,
                        StudyNoteVote.user_id == clean_user_id,
                    ),
                ).outerjoin(
                    StudyNoteBookmark,
                    and_(
                        StudyNoteBookmark.note_id == StudyNote.id,
                        StudyNoteBookmark.user_id == clean_user_id,
                    ),
                )

            stmt = stmt.where(StudyNote.id == note_id, StudyNote.is_deleted.is_(False))
            result = await self._session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_user_note_states(
        self,
        user_id: str,
        note_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        try:
            clean_uid = user_id.strip() if user_id else ""
            if not clean_uid or not note_ids:
                return {}

            states: Dict[str, Dict[str, Any]] = {
                nid: {"user_vote": 0, "is_bookmarked": False} for nid in note_ids
            }

            votes_stmt = select(StudyNoteVote.note_id, StudyNoteVote.vote_type).where(
                StudyNoteVote.user_id == clean_uid,
                StudyNoteVote.note_id.in_(note_ids),
            )
            votes_res = await self._session.execute(votes_stmt)
            for row in votes_res.all():
                if row.note_id in states:
                    states[row.note_id]["user_vote"] = int(row.vote_type)

            bookmarks_stmt = select(StudyNoteBookmark.note_id).where(
                StudyNoteBookmark.user_id == clean_uid,
                StudyNoteBookmark.note_id.in_(note_ids),
            )
            bookmarks_res = await self._session.execute(bookmarks_stmt)
            for row in bookmarks_res.all():
                if row.note_id in states:
                    states[row.note_id]["is_bookmarked"] = True

            return states
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def vote_note(
        self,
        note_id: str,
        user_id: str,
        vote: int,
    ) -> Optional[Dict[str, Any]]:
        try:
            note = (
                await self._session.execute(
                    select(StudyNote).where(
                        StudyNote.id == note_id,
                        StudyNote.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if not note:
                return None

            existing_vote = (
                await self._session.execute(
                    select(StudyNoteVote).where(
                        StudyNoteVote.user_id == user_id,
                        StudyNoteVote.note_id == note_id,
                    )
                )
            ).scalar_one_or_none()

            old_vote = int(existing_vote.vote_type) if existing_vote else 0
            target_vote = int(vote)

            if old_vote != target_vote:
                # 1. Decrement previous counter if user had an active vote
                if old_vote == 1:
                    note.upvote_count = max(0, int(note.upvote_count or 0) - 1)
                elif old_vote == -1:
                    note.downvote_count = max(0, int(note.downvote_count or 0) - 1)

                # 2. Increment new counter if casting a vote
                if target_vote == 1:
                    note.upvote_count = int(note.upvote_count or 0) + 1
                elif target_vote == -1:
                    note.downvote_count = int(note.downvote_count or 0) + 1

                # 3. Apply 3NF normalized row mutation (DELETE on 0, UPSERT on 1/-1)
                if target_vote == 0:
                    if existing_vote is not None:
                        await self._session.delete(existing_vote)
                else:
                    if existing_vote is not None:
                        existing_vote.vote_type = target_vote
                        existing_vote.updated_at = datetime.now(timezone.utc)
                    else:
                        new_vote = StudyNoteVote(
                            id=f"{user_id}_{note_id}",
                            user_id=user_id,
                            note_id=note_id,
                            vote_type=target_vote,
                        )
                        self._session.add(new_vote)

                await self._session.flush()

            return {
                "status": "success",
                "note_id": note_id,
                "user_vote": target_vote,
                "upvote_count": int(note.upvote_count or 0),
                "downvote_count": int(note.downvote_count or 0),
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def toggle_bookmark(
        self,
        note_id: str,
        user_id: str,
        is_bookmarked: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            note = (
                await self._session.execute(
                    select(StudyNote).where(
                        StudyNote.id == note_id,
                        StudyNote.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if not note:
                return None

            existing_bookmark = (
                await self._session.execute(
                    select(StudyNoteBookmark).where(
                        StudyNoteBookmark.user_id == user_id,
                        StudyNoteBookmark.note_id == note_id,
                    )
                )
            ).scalar_one_or_none()

            target_state = (
                (existing_bookmark is None)
                if is_bookmarked is None
                else bool(is_bookmarked)
            )

            # Strict 3NF normalization: insert row when True, delete row when False
            if target_state and existing_bookmark is None:
                bookmark = StudyNoteBookmark(
                    id=f"{user_id}_{note_id}",
                    user_id=user_id,
                    note_id=note_id,
                )
                self._session.add(bookmark)
                await self._session.flush()
            elif not target_state and existing_bookmark is not None:
                await self._session.delete(existing_bookmark)
                await self._session.flush()

            return {
                "status": "success",
                "note_id": note_id,
                "is_bookmarked": target_state,
            }
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
                "upvote_count": int(note.upvote_count or 0) if note else 0,
                "downvote_count": int(note.downvote_count or 0) if note else 0,
                "user_vote": 0,
                "is_bookmarked": False,
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


"""
Concrete PostgreSQL Implementation of StudyNoteRepository returning pure StudyNoteEntity objects.
"""

import uuid
from typing import List, Dict, Any, Optional
import asyncpg

from app.domain.entities import StudyNoteEntity
from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.study_note_repository import StudyNoteRepository


class PostgresStudyNoteRepository(StudyNoteRepository):
    """PostgreSQL implementation of `StudyNoteRepository` using asyncpg."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> StudyNoteEntity:
        d = dict(row)
        return StudyNoteEntity(
            id=d["id"],
            title=d["title"],
            description=d.get("description"),
            subject_id=d["subject_id"],
            lesson_id=d.get("lesson_id"),
            content_text=d.get("content_text") or "",
            pdf_url=d.get("pdf_url"),
            is_premium=bool(d.get("is_premium", False)),
            order_index=int(d.get("order_index") or 0),
            author=d.get("author"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            subject_name=d.get("subject_name"),
            subject_sinhala_name=d.get("subject_sinhala_name"),
            lesson_title=d.get("lesson_title"),
            lesson_sinhala_title=d.get("lesson_sinhala_title"),
        )

    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[StudyNoteEntity]:
        query = """
            SELECT n.id, n.title, n.description, n.subject_id, n.lesson_id,
                   n.content_text, n.pdf_url, n.is_premium, n.order_index, n.author,
                   n.created_at, n.updated_at,
                   s.name as subject_name, s.sinhala_name as subject_sinhala_name,
                   l.title as lesson_title, l.sinhala_title as lesson_sinhala_title
            FROM study_notes n
            LEFT JOIN subjects s ON n.subject_id = s.id
            LEFT JOIN syllabus_lessons l ON n.lesson_id = l.id
            WHERE 1=1
        """
        params: List[Any] = []
        param_idx = 1

        if subject_id and subject_id.strip():
            query += f" AND n.subject_id = ${param_idx}"
            params.append(subject_id.strip())
            param_idx += 1

        if lesson_id and lesson_id.strip():
            query += f" AND n.lesson_id = ${param_idx}"
            params.append(lesson_id.strip())
            param_idx += 1

        if search and search.strip():
            query += (
                f" AND (n.title ILIKE ${param_idx} "
                f"OR n.description ILIKE ${param_idx} "
                f"OR n.author ILIKE ${param_idx})"
            )
            params.append(f"%{search.strip()}%")
            param_idx += 1

        query += f" ORDER BY n.order_index ASC, n.created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1};"
        params.extend([limit, offset])

        try:
            rows = await self._conn.fetch(query, *params)
            return [self._to_entity(r) for r in rows]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_by_id(self, note_id: str) -> Optional[StudyNoteEntity]:
        try:
            row = await self._conn.fetchrow(
                """
                SELECT n.id, n.title, n.description, n.subject_id, n.lesson_id,
                       n.content_text, n.pdf_url, n.is_premium, n.order_index, n.author,
                       n.created_at, n.updated_at,
                       s.name as subject_name, s.sinhala_name as subject_sinhala_name,
                       l.title as lesson_title, l.sinhala_title as lesson_sinhala_title
                FROM study_notes n
                LEFT JOIN subjects s ON n.subject_id = s.id
                LEFT JOIN syllabus_lessons l ON n.lesson_id = l.id
                WHERE n.id = $1;
                """,
                note_id,
            )
            return self._to_entity(row) if row else None
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
    ) -> StudyNoteEntity:
        prefix = subject_id.replace("_maths", "") if subject_id else "note"
        resolved_id = (
            note_id.strip()
            if (note_id and note_id.strip())
            else f"note_{prefix}_{uuid.uuid4().hex[:8]}"
        )
        cleaned_lesson_id = (
            lesson_id.strip() if (lesson_id and lesson_id.strip()) else None
        )

        query = """
        INSERT INTO study_notes (
            id, title, description, subject_id, lesson_id,
            content_text, pdf_url, is_premium, order_index, author,
            created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            NOW(), NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            subject_id = EXCLUDED.subject_id,
            lesson_id = EXCLUDED.lesson_id,
            content_text = EXCLUDED.content_text,
            pdf_url = EXCLUDED.pdf_url,
            is_premium = EXCLUDED.is_premium,
            order_index = EXCLUDED.order_index,
            author = EXCLUDED.author,
            updated_at = NOW()
        RETURNING *;
        """
        try:
            row = await self._conn.fetchrow(
                query,
                resolved_id,
                title,
                description or "",
                subject_id,
                cleaned_lesson_id,
                content_text or "",
                pdf_url or None,
                is_premium,
                order_index,
                author or "",
            )
            return self._to_entity(row)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete(self, note_id: str) -> Dict[str, Any]:
        try:
            res = await self._conn.execute(
                "DELETE FROM study_notes WHERE id = $1;", note_id
            )
            return {"status": "success", "result": res}
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

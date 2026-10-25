"""
Concrete PostgreSQL Implementation of CurriculumRepository.
"""

import uuid
from typing import List, Dict, Any, Optional
import asyncpg

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.curriculum_repository import CurriculumRepository


class PostgresCurriculumRepository(CurriculumRepository):
    """PostgreSQL implementation of `CurriculumRepository` using asyncpg."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_subjects(self) -> List[Dict[str, Any]]:
        try:
            rows = await self._conn.fetch(
                """
                SELECT id, name, sinhala_name, code, order_index, description, created_at, updated_at
                FROM subjects
                ORDER BY order_index ASC;
                """
            )
            return [dict(r) for r in rows]
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
        resolved_id = (
            subject_id.strip()
            if (subject_id and subject_id.strip())
            else str(uuid.uuid4())
        )
        query = """
        INSERT INTO subjects (id, name, sinhala_name, code, order_index, description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            sinhala_name = EXCLUDED.sinhala_name,
            code = EXCLUDED.code,
            order_index = EXCLUDED.order_index,
            description = EXCLUDED.description,
            updated_at = NOW()
        RETURNING *;
        """
        try:
            row = await self._conn.fetchrow(
                query,
                resolved_id,
                name,
                sinhala_name,
                code,
                order_index,
                description,
            )
            return dict(row)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        try:
            row = await self._conn.fetchrow(
                "DELETE FROM subjects WHERE id = $1 RETURNING id;", subject_id
            )
            return {
                "status": "success",
                "deleted_id": row["id"] if row else subject_id,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_lessons(
        self, subject_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            if subject_id:
                rows = await self._conn.fetch(
                    """
                    SELECT id, subject_id, title, sinhala_title, order_index, description,
                           question_count, premium_count, created_at, updated_at
                    FROM syllabus_lessons
                    WHERE subject_id = $1
                    ORDER BY order_index ASC;
                    """,
                    subject_id,
                )
            else:
                rows = await self._conn.fetch(
                    """
                    SELECT id, subject_id, title, sinhala_title, order_index, description,
                           question_count, premium_count, created_at, updated_at
                    FROM syllabus_lessons
                    ORDER BY subject_id, order_index ASC;
                    """
                )
            return [dict(r) for r in rows]
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
        resolved_id = (
            lesson_id.strip()
            if (lesson_id and lesson_id.strip())
            else str(uuid.uuid4())
        )
        query = """
        INSERT INTO syllabus_lessons (id, subject_id, title, sinhala_title, order_index, description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            subject_id = EXCLUDED.subject_id,
            title = EXCLUDED.title,
            sinhala_title = EXCLUDED.sinhala_title,
            order_index = EXCLUDED.order_index,
            description = EXCLUDED.description,
            updated_at = NOW()
        RETURNING *;
        """
        try:
            row = await self._conn.fetchrow(
                query,
                resolved_id,
                subject_id,
                title,
                sinhala_title,
                order_index,
                description,
            )
            return dict(row)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_lesson(self, lesson_id: str) -> Dict[str, Any]:
        try:
            row = await self._conn.fetchrow(
                "DELETE FROM syllabus_lessons WHERE id = $1 RETURNING id;", lesson_id
            )
            return {
                "status": "success",
                "deleted_id": row["id"] if row else lesson_id,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

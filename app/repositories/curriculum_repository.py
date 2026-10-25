"""
Concrete PostgreSQL Implementation of CurriculumRepository returning pure Domain Entities.
"""

from typing import List, Dict, Any, Optional
import asyncpg

from app.domain.entities import LessonEntity, SubjectEntity
from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.curriculum_repository import CurriculumRepository


class PostgresCurriculumRepository(CurriculumRepository):
    """PostgreSQL implementation of `CurriculumRepository` using asyncpg."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _to_subject_entity(row: asyncpg.Record) -> SubjectEntity:
        data = dict(row)
        return SubjectEntity(
            id=data["id"],
            name=data["name"],
            sinhala_name=data.get("sinhala_name"),
            code=data["code"],
            order_index=int(data.get("order_index") or 1),
            description=data.get("description"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @staticmethod
    def _to_lesson_entity(row: asyncpg.Record) -> LessonEntity:
        data = dict(row)
        return LessonEntity(
            id=data["id"],
            subject_id=data["subject_id"],
            title=data["title"],
            sinhala_title=data.get("sinhala_title"),
            order_index=int(data.get("order_index") or 1),
            description=data.get("description"),
            question_count=int(data.get("question_count") or 0),
            premium_count=int(data.get("premium_count") or 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def get_subjects(self) -> List[SubjectEntity]:
        try:
            rows = await self._conn.fetch(
                """
                SELECT id, name, sinhala_name, code, order_index, description, created_at, updated_at
                FROM subjects
                ORDER BY order_index ASC;
                """
            )
            return [self._to_subject_entity(r) for r in rows]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def upsert_subject(
        self,
        subject_id: str,
        name: str,
        sinhala_name: str,
        code: str,
        order_index: int,
        description: str = "",
    ) -> SubjectEntity:
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
                query, subject_id, name, sinhala_name, code, order_index, description
            )
            return self._to_subject_entity(row)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        try:
            res = await self._conn.execute(
                "DELETE FROM subjects WHERE id = $1;", subject_id
            )
            return {"status": "success", "result": res}
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_lessons(
        self, subject_id: Optional[str] = None
    ) -> List[LessonEntity]:
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
            return [self._to_lesson_entity(r) for r in rows]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def upsert_lesson(
        self,
        lesson_id: str,
        subject_id: str,
        title: str,
        sinhala_title: str,
        order_index: int,
        description: str = "",
    ) -> LessonEntity:
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
                lesson_id,
                subject_id,
                title,
                sinhala_title,
                order_index,
                description,
            )
            return self._to_lesson_entity(row)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

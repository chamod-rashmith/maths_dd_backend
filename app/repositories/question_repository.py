"""
Concrete PostgreSQL Implementation of QuestionRepository.
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional
import asyncpg

from app.domain.repositories.question_repository import QuestionRepository


class PostgresQuestionRepository(QuestionRepository):
    """PostgreSQL implementation of `QuestionRepository` using asyncpg."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create_question_with_solution(
        self,
        title: str,
        subject_id: str,
        lesson_id: Optional[str],
        content_text: str,
        solution_text: str,
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
        custom_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._conn.transaction():
            q_id = (
                custom_id.strip()
                if (custom_id and custom_id.strip())
                else f"q_{uuid.uuid4().hex[:10]}"
            )

            parsed_date = None
            if scheduled_date and str(scheduled_date).strip():
                try:
                    parsed_date = datetime.date.fromisoformat(
                        str(scheduled_date).strip()
                    )
                except (ValueError, TypeError):
                    parsed_date = None

            q_query = """
            INSERT INTO questions (
                id, title, subject_id, lesson_id, content_text,
                type, difficulty, schedule, source, source_details,
                allocated_marks, is_premium, is_published, scheduled_date,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                $11, $12, $13, $14,
                NOW(), NOW()
            )
            RETURNING id, title, subject_id, lesson_id, created_at;
            """
            q_row = await self._conn.fetchrow(
                q_query,
                q_id,
                title,
                subject_id,
                lesson_id,
                content_text,
                question_type,
                difficulty,
                schedule,
                source,
                source_details,
                allocated_marks,
                is_premium,
                is_published,
                parsed_date,
            )

            sol_id = uuid.uuid4()
            sol_query = """
            INSERT INTO marking_schemes (
                id, question_id, title, content_text, total_marks,
                is_official, is_premium_only, order_index, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                true, false, 1, NOW(), NOW()
            )
            RETURNING id, question_id, title;
            """
            sol_row = await self._conn.fetchrow(
                sol_query,
                sol_id,
                q_id,
                solution_title,
                solution_text,
                allocated_marks,
            )

            return {
                "question": dict(q_row),
                "marking_scheme": dict(sol_row),
            }

    async def get_recent(self, limit: int = 15) -> List[Dict[str, Any]]:
        rows = await self._conn.fetch(
            """
            SELECT q.id, q.title, q.subject_id, q.type, q.difficulty, q.schedule,
                   q.source, q.allocated_marks, q.is_published, q.created_at,
                   s.name as subject_name, l.title as lesson_title
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN syllabus_lessons l ON q.lesson_id = l.id
            ORDER BY q.created_at DESC
            LIMIT $1;
            """,
            limit,
        )
        return [dict(r) for r in rows]

"""
Concrete PostgreSQL Implementation of QuestionRepository.
Implements immutable scheduled_date daily lookups, lightweight catalog queries,
and on-demand marking scheme retrieval.
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import asyncpg

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.question_repository import QuestionRepository

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
        custom_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            async with self._conn.transaction():
                q_id = (
                    custom_id.strip()
                    if (custom_id and custom_id.strip())
                    else str(uuid.uuid4())
                )
                cleaned_lesson_id = (
                    lesson_id.strip()
                    if (lesson_id and lesson_id.strip())
                    else None
                )

                parsed_date: Optional[datetime.date] = None
                if scheduled_date and str(scheduled_date).strip():
                    try:
                        parsed_date = datetime.date.fromisoformat(
                            str(scheduled_date).strip()[:10]
                        )
                    except (ValueError, TypeError):
                        parsed_date = None

                # If a scheduled_date is provided, automatically mark schedule as DAILY if default REGULAR
                effective_schedule = schedule
                if parsed_date is not None and effective_schedule == "REGULAR":
                    effective_schedule = "DAILY"

                q_query = """
                INSERT INTO questions (
                    id, title, description, subject_id, lesson_id,
                    content_text, content_url,
                    type, difficulty, schedule, source, source_details,
                    allocated_marks, is_premium, is_published, scheduled_date,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7,
                    $8, $9, $10, $11, $12,
                    $13, $14, $15, $16,
                    NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    subject_id = EXCLUDED.subject_id,
                    lesson_id = EXCLUDED.lesson_id,
                    content_text = EXCLUDED.content_text,
                    content_url = EXCLUDED.content_url,
                    type = EXCLUDED.type,
                    difficulty = EXCLUDED.difficulty,
                    schedule = EXCLUDED.schedule,
                    source = EXCLUDED.source,
                    source_details = EXCLUDED.source_details,
                    allocated_marks = EXCLUDED.allocated_marks,
                    is_premium = EXCLUDED.is_premium,
                    is_published = EXCLUDED.is_published,
                    scheduled_date = EXCLUDED.scheduled_date,
                    updated_at = NOW()
                RETURNING id, title, description, subject_id, lesson_id, scheduled_date, created_at, updated_at;
                """
                q_row = await self._conn.fetchrow(
                    q_query,
                    q_id,
                    title,
                    description or "",
                    subject_id,
                    cleaned_lesson_id,
                    content_text or "",
                    content_url.strip() if (content_url and content_url.strip()) else None,
                    question_type,
                    difficulty,
                    effective_schedule,
                    source,
                    source_details or "",
                    allocated_marks,
                    is_premium,
                    is_published,
                    parsed_date,
                )

                # Upsert official marking scheme for this question
                existing_sol_id = await self._conn.fetchval(
                    "SELECT id FROM marking_schemes WHERE question_id = $1 ORDER BY order_index ASC LIMIT 1;",
                    q_id,
                )
                sol_id = existing_sol_id or uuid.uuid4()
                cleaned_sol_pdf = (
                    solution_pdf_url.strip()
                    if (solution_pdf_url and solution_pdf_url.strip())
                    else None
                )

                sol_query = """
                INSERT INTO marking_schemes (
                    id, question_id, title, content_text, pdf_url, total_marks,
                    is_official, is_premium_only, order_index, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    true, $7, 1, NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content_text = EXCLUDED.content_text,
                    pdf_url = EXCLUDED.pdf_url,
                    total_marks = EXCLUDED.total_marks,
                    is_premium_only = EXCLUDED.is_premium_only,
                    updated_at = NOW()
                RETURNING id, question_id, title, total_marks;
                """
                sol_row = await self._conn.fetchrow(
                    sol_query,
                    sol_id,
                    q_id,
                    solution_title,
                    solution_text or "",
                    cleaned_sol_pdf,
                    allocated_marks,
                    is_premium,
                )

                sol_dict = dict(sol_row)
                sol_dict["id"] = str(sol_dict["id"])
                return {
                    "question": dict(q_row),
                    "marking_scheme": sol_dict,
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
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT q.id, q.title, COALESCE(q.description, '') AS description,
                   q.subject_id, q.lesson_id,
                   CASE
                       WHEN q.content_url IS NOT NULL AND q.content_url != '' THEN
                           CASE
                               WHEN LOWER(q.content_url) LIKE '%.png%'
                                 OR LOWER(q.content_url) LIKE '%.jpg%'
                                 OR LOWER(q.content_url) LIKE '%.jpeg%'
                                 OR LOWER(q.content_url) LIKE '%.webp%' THEN 'image'
                               ELSE 'pdf'
                           END
                       ELSE 'markdown'
                   END AS content_type,
                   q.type, q.difficulty, q.schedule, q.source,
                   COALESCE(q.source_details, '') AS source_details,
                   q.allocated_marks, q.is_premium, q.is_published, q.scheduled_date,
                   EXISTS (
                       SELECT 1 FROM marking_schemes ms
                       WHERE ms.question_id = q.id
                         AND (
                           (ms.content_text IS NOT NULL AND ms.content_text != '')
                           OR (ms.pdf_url IS NOT NULL AND ms.pdf_url != '')
                         )
                   ) AS has_marking_scheme,
                   q.created_at, q.updated_at,
                   s.code AS subject_code, s.name AS subject_name,
                   l.title AS lesson_title, l.sinhala_title AS lesson_sinhala_title
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN syllabus_lessons l ON q.lesson_id = l.id
            WHERE 1=1
        """
        params: List[Any] = []
        param_idx = 1

        if not include_unpublished:
            query += """
                AND q.is_published = TRUE
                AND (q.scheduled_date IS NULL OR q.scheduled_date <= (NOW() AT TIME ZONE 'Asia/Colombo')::date)
            """

        if subject_id and subject_id.strip():
            query += f""" AND (
                q.subject_id = ${param_idx}
                OR UPPER(s.code) = UPPER(${param_idx})
                OR (s.code = 'PMAT' AND LOWER(${param_idx}) IN ('pure_maths', 'puremaths', 'pure', 'subj_pmat'))
                OR (s.code = 'AMAT' AND LOWER(${param_idx}) IN ('applied_maths', 'appliedmaths', 'applied', 'subj_amat'))
            )"""
            params.append(subject_id.strip())
            param_idx += 1

        if lesson_id and lesson_id.strip():
            query += f" AND q.lesson_id = ${param_idx}"
            params.append(lesson_id.strip())
            param_idx += 1

        if question_type and question_type.strip():
            query += f" AND UPPER(q.type) = UPPER(${param_idx})"
            params.append(question_type.strip())
            param_idx += 1

        if difficulty and difficulty.strip():
            query += f" AND UPPER(q.difficulty) = UPPER(${param_idx})"
            params.append(difficulty.strip())
            param_idx += 1

        if schedule and schedule.strip():
            query += f" AND UPPER(q.schedule) = UPPER(${param_idx})"
            params.append(schedule.strip())
            param_idx += 1

        if source and source.strip():
            query += f" AND UPPER(q.source) = UPPER(${param_idx})"
            params.append(source.strip())
            param_idx += 1

        if is_premium is not None:
            query += f" AND q.is_premium = ${param_idx}"
            params.append(is_premium)
            param_idx += 1

        query += f"""
            ORDER BY COALESCE(q.scheduled_date, q.created_at::date) DESC, q.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1};
        """
        params.extend([limit, offset])

        try:
            rows = await self._conn.fetch(query, *params)
            return [dict(r) for r in rows]
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_recent(self, limit: int = 15) -> List[Dict[str, Any]]:
        return await self.list_questions(include_unpublished=True, limit=limit, offset=0)

    async def get_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        try:
            row = await self._conn.fetchrow(
                """
                SELECT q.id, q.title, COALESCE(q.description, '') AS description,
                       q.subject_id, q.lesson_id,
                       COALESCE(q.content_text, '') AS content_text,
                       q.content_url,
                       CASE
                           WHEN q.content_url IS NOT NULL AND q.content_url != '' THEN
                               CASE
                                   WHEN LOWER(q.content_url) LIKE '%.png%'
                                     OR LOWER(q.content_url) LIKE '%.jpg%'
                                     OR LOWER(q.content_url) LIKE '%.jpeg%'
                                     OR LOWER(q.content_url) LIKE '%.webp%' THEN 'image'
                                   ELSE 'pdf'
                               END
                           ELSE 'markdown'
                       END AS content_type,
                       q.type, q.difficulty, q.schedule, q.source,
                       COALESCE(q.source_details, '') AS source_details,
                       q.allocated_marks, q.is_premium, q.is_published, q.scheduled_date,
                       EXISTS (
                           SELECT 1 FROM marking_schemes ms
                           WHERE ms.question_id = q.id
                             AND (
                               (ms.content_text IS NOT NULL AND ms.content_text != '')
                               OR (ms.pdf_url IS NOT NULL AND ms.pdf_url != '')
                             )
                       ) AS has_marking_scheme,
                       q.created_at, q.updated_at,
                       s.code AS subject_code, s.name AS subject_name,
                       l.title AS lesson_title, l.sinhala_title AS lesson_sinhala_title
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN syllabus_lessons l ON q.lesson_id = l.id
                WHERE q.id = $1;
                """,
                question_id.strip(),
            )
            return dict(row) if row else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_daily_question(
        self, target_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        resolved_date = _resolve_colombo_date(target_date)
        try:
            # 1. Primary O(1) lookup by exact scheduled_date match
            row = await self._conn.fetchrow(
                """
                SELECT q.id, q.title, COALESCE(q.description, '') AS description,
                       q.subject_id, q.lesson_id,
                       COALESCE(q.content_text, '') AS content_text,
                       q.content_url,
                       CASE
                           WHEN q.content_url IS NOT NULL AND q.content_url != '' THEN
                               CASE
                                   WHEN LOWER(q.content_url) LIKE '%.png%'
                                     OR LOWER(q.content_url) LIKE '%.jpg%'
                                     OR LOWER(q.content_url) LIKE '%.jpeg%'
                                     OR LOWER(q.content_url) LIKE '%.webp%' THEN 'image'
                                   ELSE 'pdf'
                               END
                           ELSE 'markdown'
                       END AS content_type,
                       q.type, q.difficulty,
                       'DAILY' AS schedule,
                       q.source,
                       COALESCE(q.source_details, '') AS source_details,
                       q.allocated_marks, q.is_premium, q.is_published, q.scheduled_date,
                       EXISTS (
                           SELECT 1 FROM marking_schemes ms
                           WHERE ms.question_id = q.id
                             AND (
                               (ms.content_text IS NOT NULL AND ms.content_text != '')
                               OR (ms.pdf_url IS NOT NULL AND ms.pdf_url != '')
                             )
                       ) AS has_marking_scheme,
                       q.created_at, q.updated_at,
                       s.code AS subject_code, s.name AS subject_name,
                       l.title AS lesson_title, l.sinhala_title AS lesson_sinhala_title
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN syllabus_lessons l ON q.lesson_id = l.id
                WHERE q.is_published = TRUE
                  AND q.scheduled_date = $1
                ORDER BY q.updated_at DESC
                LIMIT 1;
                """,
                resolved_date,
            )
            if row:
                return dict(row)

            # 2. Fallback: Most recent scheduled question on or before resolved_date
            fallback_row = await self._conn.fetchrow(
                """
                SELECT q.id, q.title, COALESCE(q.description, '') AS description,
                       q.subject_id, q.lesson_id,
                       COALESCE(q.content_text, '') AS content_text,
                       q.content_url,
                       CASE
                           WHEN q.content_url IS NOT NULL AND q.content_url != '' THEN
                               CASE
                                   WHEN LOWER(q.content_url) LIKE '%.png%'
                                     OR LOWER(q.content_url) LIKE '%.jpg%'
                                     OR LOWER(q.content_url) LIKE '%.jpeg%'
                                     OR LOWER(q.content_url) LIKE '%.webp%' THEN 'image'
                                   ELSE 'pdf'
                               END
                           ELSE 'markdown'
                       END AS content_type,
                       q.type, q.difficulty,
                       'DAILY' AS schedule,
                       q.source,
                       COALESCE(q.source_details, '') AS source_details,
                       q.allocated_marks, q.is_premium, q.is_published, q.scheduled_date,
                       EXISTS (
                           SELECT 1 FROM marking_schemes ms
                           WHERE ms.question_id = q.id
                             AND (
                               (ms.content_text IS NOT NULL AND ms.content_text != '')
                               OR (ms.pdf_url IS NOT NULL AND ms.pdf_url != '')
                             )
                       ) AS has_marking_scheme,
                       q.created_at, q.updated_at,
                       s.code AS subject_code, s.name AS subject_name,
                       l.title AS lesson_title, l.sinhala_title AS lesson_sinhala_title
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN syllabus_lessons l ON q.lesson_id = l.id
                WHERE q.is_published = TRUE
                  AND q.scheduled_date IS NOT NULL
                  AND q.scheduled_date <= $1
                ORDER BY q.scheduled_date DESC, q.updated_at DESC
                LIMIT 1;
                """,
                resolved_date,
            )
            return dict(fallback_row) if fallback_row else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_marking_scheme(
        self, question_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            row = await self._conn.fetchrow(
                """
                SELECT id, question_id, title,
                       COALESCE(content_text, '') AS content_text,
                       pdf_url,
                       CASE
                           WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 'pdf'
                           ELSE 'markdown'
                       END AS content_type,
                       total_marks, is_official, is_premium_only, order_index,
                       created_at, updated_at
                FROM marking_schemes
                WHERE question_id = $1
                ORDER BY order_index ASC
                LIMIT 1;
                """,
                question_id.strip(),
            )
            if not row:
                return None
            result = dict(row)
            result["id"] = str(result["id"])
            return result
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def delete_question(self, question_id: str) -> Dict[str, Any]:
        try:
            row = await self._conn.fetchrow(
                "DELETE FROM questions WHERE id = $1 RETURNING id;",
                question_id.strip(),
            )
            return {
                "status": "success",
                "deleted_id": row["id"] if row else question_id,
            }
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

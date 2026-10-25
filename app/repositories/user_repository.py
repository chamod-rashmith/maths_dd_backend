"""
Concrete PostgreSQL Implementation of UserRepository.
"""

from typing import Optional, Dict, Any
import asyncpg

from app.domain.repositories.user_repository import UserRepository


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of `UserRepository` using asyncpg."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        row = await self._conn.fetchrow("SELECT * FROM users WHERE uid = $1;", uid)
        return dict(row) if row else None

    async def sync_or_create(
        self,
        uid: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
        telephone_no: Optional[str] = None,
        school_name: Optional[str] = None,
        district: Optional[str] = None,
        stream: Optional[str] = None,
        grade: Optional[str] = None,
        attempt: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = """
        INSERT INTO users (
            uid, email, name, avatar_url, telephone_no,
            school_name, district, stream, grade, attempt,
            created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            NOW(), NOW()
        )
        ON CONFLICT (uid) DO UPDATE SET
            email = EXCLUDED.email,
            name = CASE
                WHEN EXCLUDED.name IS NOT NULL AND EXCLUDED.name != ''
                THEN EXCLUDED.name
                ELSE users.name
            END,
            avatar_url = COALESCE(EXCLUDED.avatar_url, users.avatar_url),
            telephone_no = COALESCE(EXCLUDED.telephone_no, users.telephone_no),
            school_name = COALESCE(EXCLUDED.school_name, users.school_name),
            district = COALESCE(EXCLUDED.district, users.district),
            stream = COALESCE(EXCLUDED.stream, users.stream),
            grade = COALESCE(EXCLUDED.grade, users.grade),
            attempt = COALESCE(EXCLUDED.attempt, users.attempt),
            updated_at = NOW()
        RETURNING *;
        """
        row = await self._conn.fetchrow(
            query,
            uid,
            email,
            name,
            avatar_url,
            telephone_no,
            school_name,
            district,
            stream,
            grade,
            attempt,
        )
        return dict(row)

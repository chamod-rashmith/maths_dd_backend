"""
Concrete PostgreSQL Implementation of UserRepository returning pure UserEntity objects.
"""

from typing import Optional
import asyncpg

from app.domain.entities import UserEntity
from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.user_repository import UserRepository


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of `UserRepository` using asyncpg."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> UserEntity:
        data = dict(row)
        return UserEntity(
            uid=data["uid"],
            email=data["email"],
            name=data["name"],
            telephone_no=data.get("telephone_no"),
            role=data.get("role") or "USER",
            avatar_url=data.get("avatar_url"),
            school_name=data.get("school_name"),
            district=data.get("district"),
            stream=data.get("stream"),
            grade=data.get("grade"),
            attempt=data.get("attempt"),
            is_premium=bool(data.get("is_premium", False)),
            current_streak_days=int(data.get("current_streak_days") or 0),
            longest_streak_days=int(data.get("longest_streak_days") or 0),
            total_solved_count=int(data.get("total_solved_count") or 0),
            total_study_time_seconds=int(data.get("total_study_time_seconds") or 0),
            last_active_date=data.get("last_active_date"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def get_by_uid(self, uid: str) -> Optional[UserEntity]:
        try:
            row = await self._conn.fetchrow("SELECT * FROM users WHERE uid = $1;", uid)
            return self._to_entity(row) if row else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

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
    ) -> UserEntity:
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
        try:
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
            return self._to_entity(row)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

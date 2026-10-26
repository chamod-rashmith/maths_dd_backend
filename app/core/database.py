"""
PostgreSQL connection pool and schema lifecycle management via asyncpg.
"""

import os
import logging
from typing import Optional, AsyncGenerator
import asyncpg

from app.core.config import settings

logger = logging.getLogger("maths_dd.database")

_pool: Optional[asyncpg.Pool] = None


def _get_connection_kwargs() -> dict:
    """Builds connection parameters for Cloud SQL Unix socket or TCP."""
    if settings.INSTANCE_CONNECTION_NAME:
        cloudsql_socket_dir = f"/cloudsql/{settings.INSTANCE_CONNECTION_NAME}"
        if os.path.exists(cloudsql_socket_dir):
            return {
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD,
                "database": settings.DB_NAME,
                "host": cloudsql_socket_dir,
            }

    return {
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
        "database": settings.DB_NAME,
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
    }


async def init_db_pool() -> Optional[asyncpg.Pool]:
    """Initializes the global asyncpg connection pool and ensures database schema exists."""
    global _pool
    if _pool is not None:
        return _pool

    conn_kwargs = _get_connection_kwargs()
    try:
        _pool = await asyncpg.create_pool(
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            command_timeout=30.0,
            **conn_kwargs,
        )
        async with _pool.acquire() as conn:
            await ensure_schema(conn)
            from app.core.seed import seed_database
            await seed_database(conn)
        logger.info("Database connection pool initialized, schema verified, and seed applied.")
        return _pool
    except Exception as exc:
        logger.warning(
            "Database pool initialization deferred (database unreachable at startup): %s",
            exc,
        )
        return None


async def close_db_pool() -> None:
    """Gracefully closes the active asyncpg connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


async def get_db_connection() -> asyncpg.Connection:
    """
    Acquires a standalone connection (used when pool is not active or for direct diagnostics).
    """
    conn_kwargs = _get_connection_kwargs()
    return await asyncpg.connect(**conn_kwargs)


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency that yields a connection from the pool (or a direct connection fallback).
    """
    global _pool
    if _pool is None:
        await init_db_pool()

    if _pool is not None:
        async with _pool.acquire() as conn:
            yield conn
    else:
        conn = await get_db_connection()
        try:
            yield conn
        finally:
            await conn.close()


async def ensure_schema(conn: asyncpg.Connection) -> None:
    """
    Ensures all core production tables and indexes exist idempotently.
    Contains strictly DDL statements — zero mock or seed data.
    """
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            sinhala_name VARCHAR(255),
            code VARCHAR(50) UNIQUE NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS syllabus_lessons (
            id VARCHAR(100) PRIMARY KEY,
            subject_id VARCHAR(100) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            sinhala_title VARCHAR(255),
            order_index INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            question_count INTEGER NOT NULL DEFAULT 0,
            premium_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS questions (
            id VARCHAR(100) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            subject_id VARCHAR(100) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            lesson_id VARCHAR(100) REFERENCES syllabus_lessons(id) ON DELETE SET NULL,
            content_text TEXT NOT NULL,
            type VARCHAR(50) NOT NULL DEFAULT 'SHORT' CHECK (type IN ('SHORT', 'ESSAY')),
            difficulty VARCHAR(50) NOT NULL DEFAULT 'MEDIUM' CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
            schedule VARCHAR(50) NOT NULL DEFAULT 'REGULAR' CHECK (schedule IN ('REGULAR', 'DAILY', 'WEEKLY', 'MONTHLY')),
            source VARCHAR(50) NOT NULL DEFAULT 'PAST_PAPER' CHECK (source IN ('PAST_PAPER', 'MODEL_PAPER', 'PROVINCIAL', 'SCHOOL_PAPER')),
            source_details TEXT DEFAULT '',
            allocated_marks INTEGER NOT NULL DEFAULT 25,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            is_published BOOLEAN NOT NULL DEFAULT TRUE,
            scheduled_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS marking_schemes (
            id UUID PRIMARY KEY,
            question_id VARCHAR(100) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL DEFAULT 'Official Marking Scheme',
            content_text TEXT NOT NULL,
            total_marks INTEGER NOT NULL DEFAULT 25,
            is_official BOOLEAN NOT NULL DEFAULT TRUE,
            is_premium_only BOOLEAN NOT NULL DEFAULT FALSE,
            order_index INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS study_notes (
            id VARCHAR(100) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            subject_id VARCHAR(100) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            lesson_id VARCHAR(100) REFERENCES syllabus_lessons(id) ON DELETE SET NULL,
            content_text TEXT NOT NULL DEFAULT '',
            pdf_url TEXT,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            order_index INTEGER NOT NULL DEFAULT 0,
            author VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_study_notes_subject_order
            ON study_notes(subject_id, order_index, created_at);
        CREATE INDEX IF NOT EXISTS idx_study_notes_subject_lesson
            ON study_notes(subject_id, lesson_id, order_index);

        CREATE TABLE IF NOT EXISTS users (
            uid VARCHAR(128) PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            telephone_no VARCHAR(50),
            role VARCHAR(50) DEFAULT 'USER' CHECK (role IN ('ADMIN', 'EDITOR', 'USER')),
            avatar_url TEXT,
            school_name VARCHAR(255),
            district VARCHAR(100),
            stream VARCHAR(50),
            grade VARCHAR(50),
            attempt VARCHAR(50),
            is_premium BOOLEAN DEFAULT FALSE,
            current_streak_days INT DEFAULT 0,
            longest_streak_days INT DEFAULT 0,
            total_solved_count INT DEFAULT 0,
            total_study_time_seconds INT DEFAULT 0,
            last_active_date DATE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
    )

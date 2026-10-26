"""
Google Cloud SQL (PostgreSQL) connection pool and idempotent schema lifecycle management via asyncpg.
Configured specifically for Google Cloud Run Unix domain socket connectivity.
"""

import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional
import asyncpg

from app.core.config import settings

logger = logging.getLogger("maths_dd.database")

_pool: Optional[asyncpg.Pool] = None
_schema_initialized: bool = False
_init_lock = asyncio.Lock()

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def resolve_cloudsql_socket_dir() -> str:
    """
    Resolves the Cloud SQL Unix domain socket directory on Google Cloud Run.
    1. Uses explicit DB_HOST if it points to a /cloudsql/... socket path.
    2. Uses /cloudsql/<INSTANCE_CONNECTION_NAME>.
    3. Auto-discovers any mounted instance inside /cloudsql if the configured name differs.
    """
    if settings.DB_HOST and settings.DB_HOST.strip().startswith("/"):
        return settings.DB_HOST.strip()

    socket_root = (settings.DB_SOCKET_DIR or "/cloudsql").rstrip("/")
    instance_name = settings.INSTANCE_CONNECTION_NAME.strip()
    primary_socket_dir = f"{socket_root}/{instance_name}"

    if os.path.exists(primary_socket_dir):
        return primary_socket_dir

    # If /cloudsql exists on Cloud Run, inspect mounted instance sockets
    if os.path.isdir(socket_root):
        try:
            entries = [
                os.path.join(socket_root, entry)
                for entry in os.listdir(socket_root)
                if not entry.startswith(".")
            ]
            if entries:
                return entries[0]
        except OSError:
            pass

    return primary_socket_dir


def _get_connection_kwargs() -> Dict[str, Any]:
    """
    Builds connection parameters for Google Cloud SQL on Cloud Run.
    Always prioritizes the Cloud SQL Unix domain socket (/cloudsql/<INSTANCE_CONNECTION_NAME>)
    and ignores accidental loopback DB_HOST values (127.0.0.1 / localhost).
    """
    socket_dir = resolve_cloudsql_socket_dir()
    explicit_host = settings.DB_HOST.strip() if settings.DB_HOST else ""

    # Only use TCP host/port if a non-loopback remote IP/hostname is explicitly set
    # AND the Cloud SQL Unix socket directory is not mounted.
    if (
        explicit_host
        and not explicit_host.startswith("/")
        and explicit_host.lower() not in _LOOPBACK_HOSTS
        and not os.path.exists(socket_dir)
    ):
        return {
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
            "database": settings.DB_NAME,
            "host": explicit_host,
            "port": settings.DB_PORT,
        }

    return {
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
        "database": settings.DB_NAME,
        "host": socket_dir,
    }


async def init_db_pool() -> Optional[asyncpg.Pool]:
    """
    Initializes the global asyncpg connection pool, creates/migrates all database tables,
    and applies idempotent reference seeds. Safe under concurrent requests via _init_lock.
    """
    global _pool, _schema_initialized

    if _pool is not None and _schema_initialized:
        return _pool

    async with _init_lock:
        if _pool is not None and _schema_initialized:
            return _pool

        conn_kwargs = _get_connection_kwargs()
        safe_target = conn_kwargs.get("host", "")

        try:
            if _pool is None:
                logger.info(
                    "Initializing Cloud SQL connection pool (target=%s, db=%s, user=%s)...",
                    safe_target,
                    settings.DB_NAME,
                    settings.DB_USER,
                )
                _pool = await asyncpg.create_pool(
                    min_size=settings.DB_POOL_MIN_SIZE,
                    max_size=settings.DB_POOL_MAX_SIZE,
                    command_timeout=30.0,
                    **conn_kwargs,
                )

            if not _schema_initialized and _pool is not None:
                async with _pool.acquire() as conn:
                    await ensure_schema(conn)
                    try:
                        from app.core.seed import seed_database

                        await seed_database(conn)
                    except Exception as seed_exc:
                        logger.error(
                            "Non-fatal error during seed_database (schema is intact): %s",
                            seed_exc,
                        )
                _schema_initialized = True
                logger.info(
                    "Cloud SQL connection pool ready, schema created/verified, and seed applied."
                )

            return _pool
        except Exception as exc:
            logger.error(
                "Cloud SQL initialization failed (target=%s, db=%s, user=%s): %s",
                safe_target,
                settings.DB_NAME,
                settings.DB_USER,
                exc,
            )
            if _pool is not None and not _schema_initialized:
                try:
                    await _pool.close()
                except Exception:
                    pass
                _pool = None
            return None


async def close_db_pool() -> None:
    """Gracefully closes the active asyncpg connection pool."""
    global _pool, _schema_initialized
    if _pool is not None:
        await _pool.close()
        _pool = None
        _schema_initialized = False
        logger.info("Cloud SQL connection pool closed.")


async def get_db_connection() -> asyncpg.Connection:
    """Acquires a direct Cloud SQL connection and ensures schema exists if not yet initialized."""
    global _schema_initialized
    conn_kwargs = _get_connection_kwargs()
    conn = await asyncpg.connect(command_timeout=30.0, **conn_kwargs)
    if not _schema_initialized:
        try:
            await ensure_schema(conn)
            from app.core.seed import seed_database

            await seed_database(conn)
            _schema_initialized = True
        except Exception as exc:
            logger.error("Failed to initialize schema on direct connection: %s", exc)
            await conn.close()
            raise
    return conn


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency that yields a Cloud SQL connection with guaranteed schema initialization.
    """
    if _pool is None or not _schema_initialized:
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


async def list_public_tables(conn: asyncpg.Connection) -> List[str]:
    """Returns all table names in the public schema for readiness verification."""
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name ASC;
        """
    )
    return [str(r["table_name"]) for r in rows]


async def ensure_schema(conn: asyncpg.Connection) -> None:
    """
    Idempotently creates and evolves all core production tables, columns, and indexes in Cloud SQL.
    """
    # 1. Subjects table
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
        """
    )
    await conn.execute(
        """
        ALTER TABLE subjects ADD COLUMN IF NOT EXISTS sinhala_name VARCHAR(255);
        ALTER TABLE subjects ADD COLUMN IF NOT EXISTS code VARCHAR(50);
        ALTER TABLE subjects ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE subjects ADD COLUMN IF NOT EXISTS description TEXT;
        ALTER TABLE subjects ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        ALTER TABLE subjects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        """
    )

    # 2. Syllabus Lessons table
    await conn.execute(
        """
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
        """
    )
    await conn.execute(
        """
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS sinhala_title VARCHAR(255);
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS description TEXT;
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS question_count INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS premium_count INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        ALTER TABLE syllabus_lessons ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        """
    )

    # 3. Questions table
    await conn.execute(
        """
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
        """
    )
    await conn.execute(
        """
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS lesson_id VARCHAR(100);
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS content_text TEXT NOT NULL DEFAULT '';
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS type VARCHAR(50) NOT NULL DEFAULT 'SHORT';
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS difficulty VARCHAR(50) NOT NULL DEFAULT 'MEDIUM';
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS schedule VARCHAR(50) NOT NULL DEFAULT 'REGULAR';
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'PAST_PAPER';
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS source_details TEXT DEFAULT '';
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS allocated_marks INTEGER NOT NULL DEFAULT 25;
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT TRUE;
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS scheduled_date DATE;
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        """
    )

    # 4. Marking Schemes table
    await conn.execute(
        """
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
        """
    )

    # 5. Study Notes table & indexes
    await conn.execute(
        """
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
        """
    )
    await conn.execute(
        """
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS description TEXT;
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS lesson_id VARCHAR(100);
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS content_text TEXT NOT NULL DEFAULT '';
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS pdf_url TEXT;
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS author VARCHAR(255);
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        ALTER TABLE study_notes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

        CREATE INDEX IF NOT EXISTS idx_study_notes_subject_order
            ON study_notes(subject_id, order_index, created_at);
        CREATE INDEX IF NOT EXISTS idx_study_notes_subject_lesson
            ON study_notes(subject_id, lesson_id, order_index);
        """
    )

    # 6. Users table & indexes
    await conn.execute(
        """
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
            xp INT DEFAULT 0,
            streak_count INT DEFAULT 0,
            accuracy_rate DOUBLE PRECISION DEFAULT 0.0,
            questions_solved INT DEFAULT 0,
            is_premium BOOLEAN DEFAULT FALSE,
            premium_expiry DATE,
            current_streak_days INT DEFAULT 0,
            longest_streak_days INT DEFAULT 0,
            total_solved_count INT DEFAULT 0,
            total_study_time_seconds INT DEFAULT 0,
            last_active_date DATE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    await conn.execute(
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS telephone_no VARCHAR(50);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'USER';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS school_name VARCHAR(255);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS district VARCHAR(100);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stream VARCHAR(50);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS grade VARCHAR(50);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS attempt VARCHAR(50);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_count INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS accuracy_rate DOUBLE PRECISION DEFAULT 0.0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS questions_solved INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_expiry DATE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak_days INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS longest_streak_days INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS total_solved_count INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS total_study_time_seconds INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_date DATE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
        ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
    )

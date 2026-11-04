"""
Database connection, engine configuration, and pool lifecycle using SQLAlchemy 2.0 AsyncEngine.
"""

import logging
from typing import AsyncGenerator, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger("maths_dd.database")

# Construct async connection URL using config property
_raw_url = getattr(settings, "SQLALCHEMY_DATABASE_URI", "") or settings.DATABASE_URL or ""
if _raw_url.startswith("postgresql://"):
    _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    _async_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    _async_url = _raw_url or "sqlite+aiosqlite:///:memory:"

# Configure connection pooling
_engine_kwargs = {
    "echo": False,
    "future": True,
}

if "sqlite" not in _async_url:
    _engine_kwargs.update(
        {
            "pool_size": getattr(settings, "DATABASE_POOL_SIZE", getattr(settings, "DB_POOL_MAX_SIZE", 5)),
            "max_overflow": getattr(settings, "DATABASE_MAX_OVERFLOW", getattr(settings, "DB_MAX_OVERFLOW", 10)),
            "pool_timeout": getattr(settings, "DATABASE_POOL_TIMEOUT", 30),
            "pool_recycle": getattr(settings, "DATABASE_POOL_RECYCLE", 1800),
            "pool_pre_ping": True,
        }
    )

engine = create_async_engine(_async_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency providing an isolated AsyncSession per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


get_db = get_db_session  # Backward-compatible alias for dependency injection


async def init_db() -> None:
    """
    Initializes database tables and default seeds on application startup.
    Idempotent and safe across multiple instances.
    """
    try:
        async with engine.begin() as conn:
            # Import models so they are registered with Base.metadata
            from app import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)

            # PostgreSQL legacy schema reconciliation (ensures newly normalized columns exist)
            if conn.dialect.name == "postgresql":
                await conn.execute(text("""
                    DO $$
                    BEGIN
                        -- 1. users.district_id
                        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'users' AND column_name = 'district_id'
                            ) THEN
                                ALTER TABLE users ADD COLUMN district_id INTEGER REFERENCES districts(id) ON DELETE SET NULL;
                                CREATE INDEX IF NOT EXISTS ix_users_district_id ON users (district_id);
                            END IF;
                        END IF;

                        -- 2. syllabus_lessons.parent_lesson_id
                        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'syllabus_lessons') THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'syllabus_lessons' AND column_name = 'parent_lesson_id'
                            ) THEN
                                ALTER TABLE syllabus_lessons ADD COLUMN parent_lesson_id VARCHAR(100) REFERENCES syllabus_lessons(id) ON DELETE CASCADE;
                                CREATE INDEX IF NOT EXISTS ix_syllabus_lessons_parent_lesson_id ON syllabus_lessons (parent_lesson_id);
                            END IF;
                        END IF;

                        -- 3. questions.exam_paper_id & is_deleted
                        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'questions') THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'questions' AND column_name = 'exam_paper_id'
                            ) THEN
                                ALTER TABLE questions ADD COLUMN exam_paper_id VARCHAR(36);
                                CREATE INDEX IF NOT EXISTS ix_questions_exam_paper_id ON questions (exam_paper_id);
                            END IF;
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'questions' AND column_name = 'is_deleted'
                            ) THEN
                                ALTER TABLE questions ADD COLUMN is_deleted BOOLEAN DEFAULT false NOT NULL;
                            END IF;
                        END IF;

                        -- 4. marking_schemes.description_si
                        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'marking_schemes') THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'marking_schemes' AND column_name = 'description_si'
                            ) THEN
                                ALTER TABLE marking_schemes ADD COLUMN description_si TEXT;
                            END IF;
                        END IF;

                        -- 5. study_notes.is_deleted
                        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'study_notes') THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'study_notes' AND column_name = 'is_deleted'
                            ) THEN
                                ALTER TABLE study_notes ADD COLUMN is_deleted BOOLEAN DEFAULT false NOT NULL;
                                CREATE INDEX IF NOT EXISTS idx_study_notes_is_deleted ON study_notes (is_deleted);
                            END IF;
                        END IF;
                    END $$;
                """))

        logger.info("SQLAlchemy database tables verified/created successfully.")

        try:
            async with async_session_factory() as session:
                from app.core.seed import seed_database
                await seed_database(session)
        except Exception as seed_exc:
            logger.error("Non-fatal error during seed_database: %s", seed_exc)
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise


async def init_db_pool() -> None:
    """Backward-compatible alias for init_db."""
    await init_db()


async def check_db_health() -> bool:
    """Executes a fast ping against the database for health checks."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        return False


async def list_public_tables(session: AsyncSession) -> List[str]:
    """Returns all table names in the public schema for readiness verification."""
    result = await session.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name ASC;
            """
        )
    )
    return [str(row[0]) for row in result.fetchall()]


async def close_db_pool() -> None:
    """Gracefully closes the active SQLAlchemy async engine pool."""
    await engine.dispose()
    logger.info("SQLAlchemy connection engine disposed.")

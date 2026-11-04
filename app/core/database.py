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


async def _repair_schema_anomalies(conn) -> None:
    """
    Auto-repairs legacy schema naming anomalies (e.g. users.id -> users.uid)
    to ensure seamless compatibility with existing databases without requiring table drops.
    """
    try:
        # Check if users table exists and whether primary key is 'id' instead of 'uid'
        res = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name IN ('id', 'uid')"
            )
        )
        cols = {row[0] for row in res.fetchall()}
        if "id" in cols and "uid" not in cols:
            logger.info("Repairing legacy 'users.id' column -> renaming to 'users.uid'...")
            await conn.execute(text("ALTER TABLE users RENAME COLUMN id TO uid;"))

        # Ensure backward-compatible profile columns exist on users
        for col_name, col_def in [
            ("school_name", "VARCHAR(255)"),
            ("stream", "VARCHAR(50)"),
            ("grade", "VARCHAR(50)"),
            ("attempt", "VARCHAR(50)"),
        ]:
            await conn.execute(
                text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_def};")
            )

        # Check student_profiles primary key anomaly
        res_sp = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'student_profiles' AND column_name = 'id'"
            )
        )
        if res_sp.fetchall():
            logger.info("Repairing student_profiles table schema...")
            await conn.execute(text("ALTER TABLE student_profiles DROP COLUMN IF EXISTS id CASCADE;"))
            await conn.execute(text("ALTER TABLE student_profiles ADD PRIMARY KEY (user_id);"))

        # Ensure daily_challenges has subject_id column
        await conn.execute(
            text("ALTER TABLE daily_challenges ADD COLUMN IF NOT EXISTS subject_id VARCHAR(100);")
        )

        # Ensure daily_challenge_questions and marking_scheme_steps allow varchar(100) IDs
        await conn.execute(
            text("ALTER TABLE daily_challenge_questions ALTER COLUMN id TYPE VARCHAR(100);")
        )
        await conn.execute(
            text("ALTER TABLE marking_scheme_steps ALTER COLUMN id TYPE VARCHAR(100);")
        )

        # Ensure xp_transactions has reason and attempt columns
        await conn.execute(
            text("ALTER TABLE xp_transactions ADD COLUMN IF NOT EXISTS reason VARCHAR(64) DEFAULT 'QUESTION_SOLVED';")
        )
        await conn.execute(
            text("ALTER TABLE xp_transactions ADD COLUMN IF NOT EXISTS attempt_id VARCHAR(255);")
        )
        await conn.execute(
            text("ALTER TABLE xp_transactions ADD COLUMN IF NOT EXISTS question_id VARCHAR(100);")
        )
        await conn.execute(
            text("ALTER TABLE xp_transactions ADD COLUMN IF NOT EXISTS description_en VARCHAR(255);")
        )
    except Exception as repair_exc:
        logger.debug("Schema anomaly auto-repair skipped or not applicable (e.g. SQLite): %s", repair_exc)


async def init_db() -> None:
    """
    Initializes database tables and default seeds on application startup.
    Idempotent and safe across multiple instances and local/cloud environments.
    """
    try:
        async with engine.begin() as conn:
            # Auto-repair any schema discrepancies on existing databases
            await _repair_schema_anomalies(conn)

            # Import models so they are registered with Base.metadata
            from app import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)

        logger.info("SQLAlchemy database tables verified/created successfully.")

        try:
            async with async_session_factory() as session:
                from app.core.seed import seed_database
                await seed_database(session)
        except Exception as seed_exc:
            logger.exception("Error during seed_database: %s", seed_exc)
    except Exception as e:
        logger.exception("Database initialization encountered an issue: %s", e)


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

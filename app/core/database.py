"""
Google Cloud SQL (PostgreSQL) connection pool and SQLAlchemy 2.0 ORM lifecycle management.
Optimized for Google Cloud Run and local development.
"""

import logging
from typing import AsyncGenerator, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger("maths_dd.database")


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


# Asynchronous engine configuration
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    pool_size=settings.DB_POOL_MIN_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an isolated AsyncSession per request,
    handling rollback on error and proper cleanup.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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

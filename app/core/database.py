"""
Database connection, engine configuration, and pool lifecycle using SQLAlchemy 2.0 AsyncEngine.
"""

import logging
from typing import AsyncGenerator, List
from sqlalchemy import inspect, select
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
    Initializes database tables and default seeds on application startup
    using 100% SQLAlchemy 2.0 metadata & ORM APIs (zero raw SQL strings).
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
            logger.exception("Error during seed_database: %s", seed_exc)
    except Exception as e:
        logger.exception("Database initialization encountered an issue: %s", e)


async def init_db_pool() -> None:
    """Backward-compatible alias for init_db."""
    await init_db()


async def check_db_health() -> bool:
    """Executes a fast ping against the database using SQLAlchemy `select(1)`."""
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        return True
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        return False


async def list_public_tables(session: AsyncSession) -> List[str]:
    """Returns all table names using SQLAlchemy's native `inspect()` API (zero raw SQL)."""
    conn = await session.connection()
    table_names = await conn.run_sync(
        lambda sync_conn: inspect(sync_conn).get_table_names()
    )
    return sorted(str(t) for t in table_names)


async def close_db_pool() -> None:
    """Gracefully closes the active SQLAlchemy async engine pool."""
    await engine.dispose()
    logger.info("SQLAlchemy connection engine disposed.")

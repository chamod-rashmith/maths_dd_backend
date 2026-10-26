"""
System health and Cloud SQL readiness probes for Google Cloud Run.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import (
    ensure_schema,
    get_db_connection,
    init_db_pool,
    list_public_tables,
)
from app.core.seed import seed_database

logger = logging.getLogger("maths_dd.health")

router = APIRouter(tags=["System & Health"])


@router.get("/health")
def health_check() -> Dict[str, str]:
    """Liveness probe for Google Cloud Run."""
    return {
        "status": "healthy",
        "service": "maths_dd_backend",
        "version": settings.VERSION,
    }


@router.get("/db-test")
async def test_database() -> Any:
    """
    Readiness probe verifying live connectivity to Google Cloud SQL (PostgreSQL)
    and ensuring the production database schema and seed data are initialized.
    """
    try:
        pool = await init_db_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                await ensure_schema(conn)
                await seed_database(conn)
                tables = await list_public_tables(conn)
        else:
            conn = await get_db_connection()
            try:
                tables = await list_public_tables(conn)
            finally:
                await conn.close()

        return {
            "status": "success",
            "database": "connected",
            "schema_initialized": True,
            "tables_count": len(tables),
            "tables": tables,
        }
    except Exception as exc:
        logger.error("Cloud SQL readiness probe (/db-test) failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "unavailable",
                "detail": str(exc),
            },
        )

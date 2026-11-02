"""
System health and Cloud SQL readiness probes for Google Cloud Run.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import (
    async_session_factory,
    check_db_health,
    list_public_tables,
)

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
    Readiness probe verifying live connectivity to Google Cloud SQL (PostgreSQL).
    Executes a fast ping and reports table availability without running dangerous DDL operations.
    """
    try:
        is_healthy = await check_db_health()
        if not is_healthy:
            raise RuntimeError("Database health ping returned non-healthy status.")

        async with async_session_factory() as session:
            tables = await list_public_tables(session)

        return {
            "status": "success",
            "database": "connected",
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
                "detail": "Database connection verification failed.",
            },
        )

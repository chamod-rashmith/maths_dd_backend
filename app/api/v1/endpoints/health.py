"""
System health and Cloud SQL readiness probes for Google Cloud Run.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.deps import require_admin
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
async def test_database(
    _admin: Dict[str, Any] = Depends(require_admin),
) -> Any:
    """
    Readiness probe verifying live connectivity to Google Cloud SQL (PostgreSQL).
    Restricted to ADMIN role so database schema table names are never exposed publicly.
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


async def _execute_seed_operation() -> Any:
    """Internal helper to execute seed database."""
    try:
        from app.core.seed import seed_database
        from app.core.database import init_db

        await init_db()
        async with async_session_factory() as session:
            await seed_database(session)

        return {
            "status": "success",
            "message": "Database seeded successfully across all domains.",
        }
    except Exception as exc:
        logger.exception("Manual seed trigger (/db-seed) failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "detail": f"Database seeding failed: {str(exc)}",
            },
        )


@router.post("/db-seed", operation_id="post_trigger_db_seed")
async def post_trigger_seed_database(
    _admin: Dict[str, Any] = Depends(require_admin),
) -> Any:
    """
    Triggers idempotent reference data seeding across all 7 architectural domains (requires ADMIN role).
    Populates subjects, syllabus lessons, exam papers, subscription plans, questions, and marking rubrics.
    """
    return await _execute_seed_operation()


@router.get("/db-seed", operation_id="get_trigger_db_seed")
async def get_trigger_seed_database(
    _admin: Dict[str, Any] = Depends(require_admin),
) -> Any:
    """Convenience GET endpoint to trigger database seeding (requires ADMIN role)."""
    return await _execute_seed_operation()

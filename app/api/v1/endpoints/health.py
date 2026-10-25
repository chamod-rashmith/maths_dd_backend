"""
System health and infrastructure readiness probes.
Hardened to never leak internal schema metadata, table names, or database versions.
"""

from typing import Dict, Any
import asyncpg
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_db

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
async def test_database(conn: asyncpg.Connection = Depends(get_db)) -> Any:
    """
    Readiness probe verifying live connectivity to Google Cloud SQL (PostgreSQL).
    Does not expose internal table names, database versions, or exception stack traces.
    """
    try:
        await conn.fetchval("SELECT 1;")
        return {
            "status": "success",
            "database": "connected",
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "unavailable",
            },
        )

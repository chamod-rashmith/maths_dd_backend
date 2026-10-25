"""
System health and infrastructure readiness probes.
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
    """Liveness and readiness probe for Google Cloud Run."""
    return {
        "status": "healthy",
        "service": "maths_dd_backend",
        "version": settings.VERSION,
    }


@router.get("/db-test")
async def test_database(conn: asyncpg.Connection = Depends(get_db)) -> Any:
    """Tests live connectivity to Google Cloud SQL (PostgreSQL)."""
    try:
        version = await conn.fetchval("SELECT version();")
        now = await conn.fetchval("SELECT NOW();")
        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            LIMIT 15;
            """
        )

        return {
            "status": "success",
            "message": "Connected to Cloud SQL PostgreSQL successfully!",
            "database": settings.DB_NAME,
            "postgres_version": version,
            "server_timestamp": str(now),
            "tables_found": [r["table_name"] for r in tables],
        }
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": "Failed to connect to Cloud SQL database",
                "details": str(exc),
            },
        )

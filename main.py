"""
Maths DD - Content Automation & Management Backend
Designed for deployment on Google Cloud Run with Cloud SQL (PostgreSQL).
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import get_db_connection

# Initialize FastAPI application
app = FastAPI(
    title="Maths DD Backend API",
    description="Backend microservice for Maths DD content management, database automation, and AI workflows.",
    version="1.0.0",
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """
    Root endpoint for basic service discovery.
    """
    return {
        "service": "Maths DD Backend",
        "status": "online",
        "environment": os.environ.get("ENV", "production"),
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """
    Liveness and readiness probe for Google Cloud Run.
    """
    return {"status": "healthy", "service": "maths_dd_backend"}


@app.get("/db-test")
async def test_database():
    """
    Tests live connectivity to Google Cloud SQL (PostgreSQL).
    Executes sample queries to verify credentials, database name, and public tables.
    """
    try:
        conn = await get_db_connection()
        version = await conn.fetchval("SELECT version();")
        now = await conn.fetchval("SELECT NOW();")
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 15;"
        )
        await conn.close()

        return {
            "status": "success",
            "message": "Connected to Cloud SQL PostgreSQL successfully! 🐘🚀",
            "database": os.environ.get("DB_NAME", "math-master-981fe-database"),
            "postgres_version": version,
            "server_timestamp": str(now),
            "tables_found": [r["table_name"] for r in tables],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to connect to Cloud SQL database",
            "details": str(e),
        }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

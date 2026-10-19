"""
Database connection manager for Cloud SQL (PostgreSQL).
Supports Cloud Run Unix socket connection as well as local TCP fallback.
"""

import os
import asyncpg

DB_USER = os.environ.get("DB_USER", "chamod_rashmith")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "math-master-981fe-database")
INSTANCE_CONNECTION_NAME = os.environ.get(
    "INSTANCE_CONNECTION_NAME",
    "math-master-981fe:asia-south1:math-master-981fe-instance",
)


async def get_db_connection() -> asyncpg.Connection:
    """
    Establishes an asynchronous connection to Cloud SQL PostgreSQL.
    In Cloud Run, it connects via the internal Unix domain socket.
    Locally, it connects via TCP host/port.
    """
    cloudsql_socket_dir = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"

    if os.path.exists(cloudsql_socket_dir):
        # Cloud Run internal Unix domain socket path
        return await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=cloudsql_socket_dir,
        )
    else:
        # Local development / TCP fallback
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = int(os.environ.get("DB_PORT", 5432))
        return await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=db_host,
            port=db_port,
        )

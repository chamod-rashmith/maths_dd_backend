"""
Centralized application configuration & environment settings for Google Cloud Run.
Resilient against empty-string environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_INSTANCE_CONNECTION_NAME = (
    "math-master-981fe:asia-south1:math-master-981fe-instance"
)


def _env_str(key: str, default: str) -> str:
    val = os.environ.get(key, "").strip()
    return val if val else default


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _parse_cors_origins(raw: str) -> List[str]:
    if not raw or raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration loaded from environment variables."""

    PROJECT_NAME: str = _env_str("PROJECT_NAME", "Maths DD API")
    VERSION: str = _env_str("API_VERSION", "1.0.0")
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = _env_str("ENVIRONMENT", "production")

    # Server (Cloud Run injects PORT, defaults to 8080)
    HOST: str = _env_str("HOST", "0.0.0.0")
    PORT: int = _env_int("PORT", 8080)

    # CORS
    CORS_ORIGINS: List[str] = field(
        default_factory=lambda: _parse_cors_origins(
            os.environ.get("CORS_ORIGINS", "*")
        )
    )

    # Google Cloud SQL (PostgreSQL via Cloud Run Unix Domain Socket)
    DB_USER: str = _env_str("DB_USER", "postgres")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_NAME: str = _env_str("DB_NAME", "math-master-981fe-database")
    INSTANCE_CONNECTION_NAME: str = _env_str(
        "INSTANCE_CONNECTION_NAME",
        _DEFAULT_INSTANCE_CONNECTION_NAME,
    )
    DB_SOCKET_DIR: str = _env_str("DB_SOCKET_DIR", "/cloudsql")
    DB_HOST: str = os.environ.get("DB_HOST", "").strip()
    DB_PORT: int = _env_int("DB_PORT", 5432)
    DB_POOL_MIN_SIZE: int = _env_int("DB_POOL_MIN_SIZE", 1)
    DB_POOL_MAX_SIZE: int = _env_int("DB_POOL_MAX_SIZE", 10)

    # Firebase & Google Cloud Storage
    FIREBASE_PROJECT_ID: str = _env_str("FIREBASE_PROJECT_ID", "math-master-981fe")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    ).strip()
    STORAGE_BUCKET_NAME: str = _env_str(
        "STORAGE_BUCKET_NAME",
        "math-master-981fe.firebasestorage.app",
    )

    # Upstash Serverless Redis
    UPSTASH_REDIS_REST_URL: str = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    UPSTASH_REDIS_REST_TOKEN: str = os.environ.get(
        "UPSTASH_REDIS_REST_TOKEN", ""
    ).strip()


settings = Settings()

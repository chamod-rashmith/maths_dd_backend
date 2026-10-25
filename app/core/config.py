"""
Centralized application configuration & environment settings.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _parse_cors_origins(raw: str) -> List[str]:
    if not raw or raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration loaded from environment variables."""

    PROJECT_NAME: str = os.environ.get("PROJECT_NAME", "Maths DD API")
    VERSION: str = os.environ.get("API_VERSION", "1.0.0")
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "production")

    # Server
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8080"))

    # CORS
    CORS_ORIGINS: List[str] = field(
        default_factory=lambda: _parse_cors_origins(os.environ.get("CORS_ORIGINS", "*"))
    )

    # Cloud SQL / PostgreSQL Database
    DB_USER: str = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_NAME: str = os.environ.get("DB_NAME", "math-master-981fe-database")
    DB_HOST: str = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.environ.get("DB_PORT", "5432"))
    INSTANCE_CONNECTION_NAME: str = os.environ.get("INSTANCE_CONNECTION_NAME", "")
    DB_POOL_MIN_SIZE: int = int(os.environ.get("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(os.environ.get("DB_POOL_MAX_SIZE", "10"))

    # Firebase & Google Cloud Storage
    FIREBASE_PROJECT_ID: str = os.environ.get("FIREBASE_PROJECT_ID", "math-master-981fe")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )
    STORAGE_BUCKET_NAME: str = os.environ.get(
        "STORAGE_BUCKET_NAME",
        "math-master-981fe.firebasestorage.app",
    )


settings = Settings()

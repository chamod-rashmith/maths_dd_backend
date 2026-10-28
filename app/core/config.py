"""
Centralized application configuration & environment settings for Google Cloud Run.
Resilient against empty-string environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote_plus
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

    # Database Configuration (PostgreSQL with asyncpg & SQLAlchemy 2.0)
    DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL", "").strip() or None
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
    DB_POOL_MIN_SIZE: int = _env_int("DB_POOL_MIN_SIZE", 2)
    DB_POOL_MAX_SIZE: int = _env_int("DB_POOL_MAX_SIZE", 10)
    DB_MAX_OVERFLOW: int = _env_int("DB_MAX_OVERFLOW", 10)
    DB_POOL_PRE_PING: bool = True

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

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Constructs an asyncpg-compatible SQLAlchemy database URI."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        encoded_password = quote_plus(self.DB_PASSWORD)
        user = quote_plus(self.DB_USER)

        socket_dir = f"{self.DB_SOCKET_DIR.rstrip('/')}/{self.INSTANCE_CONNECTION_NAME.strip()}"
        if os.path.exists(socket_dir):
            return f"postgresql+asyncpg://{user}:{encoded_password}@/{self.DB_NAME}?host={socket_dir}"

        host = self.DB_HOST.strip() if self.DB_HOST else "127.0.0.1"
        return f"postgresql+asyncpg://{user}:{encoded_password}@{host}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()

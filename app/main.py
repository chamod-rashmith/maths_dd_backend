"""
Maths DD - FastAPI Application Factory & Lifespan Management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import close_db_pool, init_db_pool


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle resources."""
    await init_db_pool()
    yield
    await close_db_pool()


def create_app() -> FastAPI:
    """Constructs and configures the FastAPI application instance."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Production REST API service for Maths DD mobile & web ecosystem.",
        version=settings.VERSION,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Infrastructure & readiness probes (/health, /db-test)
    application.include_router(health_router)

    # Versioned v1 REST API (/api/v1/...)
    application.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return application


app = create_app()

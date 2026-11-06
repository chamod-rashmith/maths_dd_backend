"""
Maths DD - FastAPI Application Factory, Lifespan & Global Exception Handlers.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import uuid4
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import close_db_pool, init_db_pool
from app.core.exception_handlers import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle resources on Cloud Run."""
    if os.environ.get("TESTING") != "1":
        await init_db_pool()
        yield
        await close_db_pool()
    else:
        yield


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

    @application.middleware("http")
    async def add_request_id(request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Register global domain exception handlers
    register_exception_handlers(application)

    # Infrastructure & readiness probes (/health, /db-test)
    application.include_router(health_router)

    # Versioned v1 REST API (/api/v1/...)
    application.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return application


app = create_app()

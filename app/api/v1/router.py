"""
Central API v1 Router aggregating all feature endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_security,
    curriculum,
    districts,
    leaderboard,
    progress,
    questions,
    study_notes,
    subscriptions,
    users,
)
from app.schemas.common import ErrorResponse

api_v1_router = APIRouter(
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request / Domain Validation Error"},
        401: {"model": ErrorResponse, "description": "Authentication Required"},
        403: {"model": ErrorResponse, "description": "Forbidden / Insufficient Entitlements"},
        404: {"model": ErrorResponse, "description": "Resource Not Found"},
        422: {"model": ErrorResponse, "description": "Unprocessable Entity / Request Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)
api_v1_router.include_router(users.router)
api_v1_router.include_router(districts.router)
api_v1_router.include_router(subscriptions.router)
api_v1_router.include_router(curriculum.router)
api_v1_router.include_router(questions.router)
api_v1_router.include_router(study_notes.router)
api_v1_router.include_router(progress.router)
api_v1_router.include_router(leaderboard.router)
api_v1_router.include_router(admin_security.router)

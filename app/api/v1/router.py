"""
Central API v1 Router aggregating all feature endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    curriculum,
    districts,
    progress,
    questions,
    study_notes,
    users,
)

api_v1_router = APIRouter()
api_v1_router.include_router(users.router)
api_v1_router.include_router(districts.router)
api_v1_router.include_router(curriculum.router)
api_v1_router.include_router(questions.router)
api_v1_router.include_router(study_notes.router)
api_v1_router.include_router(progress.router)

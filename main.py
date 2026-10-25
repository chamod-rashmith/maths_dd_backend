"""
Maths DD - Backend Microservice (Google Cloud Run + Cloud SQL PostgreSQL).
Production-grade REST API architecture with v1 versioning.
"""

import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
from users_router import router as users_v1_router

# Initialize FastAPI application
app = FastAPI(
    title="Maths DD API",
    description="Production REST API service for Maths DD mobile & web ecosystem.",
    version="1.0.0",
)

# Enable CORS for local development and client apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register v1 Clean Architecture API Routers
app.include_router(users_v1_router)


# -----------------------------------------------------------------------------
# System & Infrastructure Probes
# -----------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """
    Liveness and readiness probe for Google Cloud Run.
    """
    return {"status": "healthy", "service": "maths_dd_backend", "version": "1.0.0"}


@app.get("/db-test")
async def test_database():
    """
    Tests live connectivity to Google Cloud SQL (PostgreSQL).
    """
    try:
        conn = await database.get_db_connection()
        version = await conn.fetchval("SELECT version();")
        now = await conn.fetchval("SELECT NOW();")
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 15;"
        )
        await conn.close()

        return {
            "status": "success",
            "message": "Connected to Cloud SQL PostgreSQL successfully!",
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


# -----------------------------------------------------------------------------
# Curriculum & Questions API (v1 Compatibility)
# -----------------------------------------------------------------------------

class SubjectCreate(BaseModel):
    id: str
    name: str
    sinhala_name: Optional[str] = ""
    code: str
    order_index: int = 1
    description: Optional[str] = ""


class LessonCreate(BaseModel):
    id: str
    subject_id: str
    title: str
    sinhala_title: Optional[str] = ""
    order_index: int = 1
    description: Optional[str] = ""


class QuestionCreate(BaseModel):
    title: str
    custom_id: Optional[str] = None
    subject_id: str
    lesson_id: Optional[str] = None
    content_text: str
    solution_text: str
    solution_title: str = "Official Marking Scheme"
    question_type: str = "SHORT"
    difficulty: str = "MEDIUM"
    schedule: str = "REGULAR"
    source: str = "PAST_PAPER"
    source_details: Optional[str] = ""
    allocated_marks: int = 25
    is_premium: bool = False
    is_published: bool = True
    scheduled_date: Optional[str] = None


@app.get("/api/v1/curriculum/subjects")
@app.get("/api/subjects")
async def list_subjects():
    """Fetches syllabus subjects (Combined Maths: Pure & Applied)."""
    try:
        return await database.get_subjects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/curriculum/subjects")
@app.post("/api/subjects")
async def add_subject(sub: SubjectCreate):
    """Creates a new syllabus subject."""
    try:
        return await database.create_subject(
            id=sub.id,
            name=sub.name,
            sinhala_name=sub.sinhala_name or "",
            code=sub.code,
            order_index=sub.order_index,
            description=sub.description or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/curriculum/lessons")
@app.get("/api/lessons")
async def list_lessons(subject_id: Optional[str] = Query(None)):
    """Fetches syllabus lessons, optionally filtered by subject ID."""
    try:
        return await database.get_lessons(subject_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/curriculum/lessons")
@app.post("/api/lessons")
async def add_lesson(les: LessonCreate):
    """Creates or updates a syllabus lesson."""
    try:
        return await database.create_lesson(
            id=les.id,
            subject_id=les.subject_id,
            title=les.title,
            sinhala_title=les.sinhala_title or "",
            order_index=les.order_index,
            description=les.description or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/questions/recent")
@app.get("/api/questions/recent")
async def list_recent_questions(limit: int = 15):
    """Fetches the latest questions stored in Cloud SQL."""
    try:
        return await database.get_recent_questions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/questions")
@app.post("/api/questions")
async def add_question(q: QuestionCreate):
    """Creates a new question with its corresponding marking scheme in Cloud SQL."""
    try:
        return await database.create_question_with_solution(
            title=q.title,
            subject_id=q.subject_id,
            lesson_id=q.lesson_id,
            content_text=q.content_text,
            solution_text=q.solution_text,
            solution_title=q.solution_title,
            question_type=q.question_type,
            difficulty=q.difficulty,
            schedule=q.schedule,
            source=q.source,
            source_details=q.source_details or "",
            allocated_marks=q.allocated_marks,
            is_premium=q.is_premium,
            is_published=q.is_published,
            scheduled_date=q.scheduled_date,
            custom_id=q.custom_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
async def seed_database():
    """Seeds default Pure & Applied Maths curriculum taxonomy if empty."""
    try:
        return await database.seed_default_curriculum()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

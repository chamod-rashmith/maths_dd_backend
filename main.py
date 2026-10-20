"""
Maths DD - Content Automation & Management Backend
Designed for deployment on Google Cloud Run with Cloud SQL (PostgreSQL).
"""

import os
from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import database

# Initialize FastAPI application
app = FastAPI(
    title="Maths DD Content Studio API",
    description="Backend microservice for Maths DD content studio, curriculum management, and study notes automation.",
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

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


# -----------------------------------------------------------------------------
# Pydantic Request Models
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


class StudyNoteCreate(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    subject_id: str
    lesson_id: Optional[str] = None
    content_text: str = ""
    pdf_url: Optional[str] = None
    is_premium: bool = False
    order_index: int = 0
    author: Optional[str] = ""


# -----------------------------------------------------------------------------
# Web UI Endpoints
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
def serve_admin_studio():
    """
    Renders the modern Maths DD Question Studio Admin UI.
    """
    html_path = TEMPLATES_DIR / "admin.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Admin studio template not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/notes", response_class=HTMLResponse)
@app.get("/admin/notes", response_class=HTMLResponse)
def serve_notes_studio():
    """
    Renders the modern Maths DD Study Notes Studio (Light Theme & Mobile Responsive).
    """
    html_path = TEMPLATES_DIR / "notes.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Notes studio template not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


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


@app.get("/storage-test")
def test_storage():
    """
    Tests live connectivity to Google Cloud Storage (Firebase Storage) bucket.
    """
    try:
        import storage as storage_helper
        bucket = storage_helper.get_storage_bucket()
        exists = bucket.exists()
        
        return {
            "status": "success" if exists else "error",
            "message": "Connected to Google Cloud Storage bucket successfully! 🪣🚀" if exists else "Bucket not found or permission denied",
            "bucket_name": bucket.name,
            "exists": exists,
            "location": bucket.location if exists else None,
            "storage_class": bucket.storage_class if exists else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to connect to Cloud Storage bucket",
            "details": str(e),
        }


# -----------------------------------------------------------------------------
# REST API: Curriculum & Content Management
# -----------------------------------------------------------------------------

@app.get("/api/subjects")
async def list_subjects():
    """Fetches all master subjects from Cloud SQL."""
    try:
        return await database.get_subjects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subjects")
async def add_subject(sub: SubjectCreate):
    """Creates or updates a subject."""
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


@app.post("/api/subjects/cleanup")
async def cleanup_empty():
    """Deletes empty or accidental subject entries (id = '' or order_index = 0)."""
    try:
        return await database.cleanup_empty_subjects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/subjects/{subject_id}")
async def remove_subject(subject_id: str):
    """Deletes a subject by ID."""
    try:
        return await database.delete_subject(subject_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lessons")
async def list_lessons(subject_id: Optional[str] = Query(None)):
    """Fetches syllabus lessons, optionally filtered by subject ID."""
    try:
        return await database.get_lessons(subject_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/questions/recent")
async def list_recent_questions(limit: int = 15):
    """Fetches the latest questions stored in Cloud SQL."""
    try:
        return await database.get_recent_questions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
async def seed_database():
    """Seeds default Pure & Applied Maths curriculum taxonomy if empty."""
    try:
        return await database.seed_default_curriculum()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# REST API: Study Notes Management (Conforming to Data Connect Schema)
# -----------------------------------------------------------------------------

@app.get("/api/notes")
async def list_study_notes(
    subject_id: Optional[str] = Query(None),
    lesson_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = 50,
    offset: int = 0,
):
    """Fetches study notes according to Data Connect schema filters."""
    try:
        return await database.get_study_notes(
            subject_id=subject_id,
            lesson_id=lesson_id,
            search=search,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/{note_id}")
async def get_study_note(note_id: str):
    """Fetches single study note details by ID."""
    try:
        note = await database.get_study_note_by_id(note_id)
        if not note:
            raise HTTPException(status_code=404, detail=f"Study note '{note_id}' not found")
        return note
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes")
async def save_study_note(note: StudyNoteCreate):
    """Creates or updates a study note."""
    try:
        return await database.create_or_update_study_note(
            id=note.id,
            title=note.title,
            subject_id=note.subject_id,
            lesson_id=note.lesson_id,
            content_text=note.content_text,
            description=note.description or "",
            pdf_url=note.pdf_url,
            is_premium=note.is_premium,
            order_index=note.order_index,
            author=note.author or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/notes/{note_id}")
async def remove_study_note(note_id: str):
    """Deletes a study note by ID."""
    try:
        return await database.delete_study_note(note_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

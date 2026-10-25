# Maths DD Backend Service (Google Cloud Run + Cloud SQL PostgreSQL)

Production-grade FastAPI microservice for the **Maths DD** mobile & web ecosystem, engineered with **Strict Clean Architecture** (`API -> DI Container -> Abstract Domain Repositories -> Concrete PostgreSQL Repositories -> Database Pool`).

---

## 📁 Industry-Standard Clean Architecture Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI Application Factory & Lifespan
│   ├── core/                          # Core Infrastructure & Cross-Cutting Concerns
│   │   ├── __init__.py
│   │   ├── config.py                  # Centralized Environment Configuration (Settings)
│   │   ├── database.py                # asyncpg Connection Pool & Idempotent DDL Schema
│   │   ├── security.py                # Firebase Admin SDK & Bearer JWT Dependency
│   │   └── storage.py                 # Google Cloud / Firebase Storage Client
│   ├── domain/                        # Pure Domain Layer (Ports / Contracts)
│   │   ├── __init__.py
│   │   └── repositories/              # Abstract Base Classes (ABC)
│   │       ├── __init__.py
│   │       ├── curriculum_repository.py   # `CurriculumRepository(ABC)`
│   │       ├── question_repository.py     # `QuestionRepository(ABC)`
│   │       ├── study_note_repository.py   # `StudyNoteRepository(ABC)`
│   │       └── user_repository.py         # `UserRepository(ABC)`
│   ├── repositories/                  # Data / Infrastructure Layer (Concrete Adapters)
│   │   ├── __init__.py
│   │   ├── curriculum_repository.py   # `PostgresCurriculumRepository(CurriculumRepository)`
│   │   ├── question_repository.py     # `PostgresQuestionRepository(QuestionRepository)`
│   │   ├── study_note_repository.py   # `PostgresStudyNoteRepository(StudyNoteRepository)`
│   │   └── user_repository.py         # `PostgresUserRepository(UserRepository)`
│   ├── schemas/                       # Strict Pydantic Request & Response DTOs
│   │   ├── __init__.py
│   │   ├── curriculum.py              # Subject & Syllabus Lesson DTOs
│   │   ├── question.py                # Question & Marking Scheme DTOs
│   │   ├── study_note.py              # Study Note DTOs
│   │   └── user.py                    # User Profile & Telemetry DTOs
│   └── api/                           # Presentation / HTTP Routing & DI Layer
│       ├── __init__.py
│       ├── deps.py                    # Centralized Dependency Injection Providers
│       └── v1/
│           ├── __init__.py
│           ├── router.py              # Aggregated /api/v1 Router
│           └── endpoints/
│               ├── __init__.py
│               ├── curriculum.py      # /api/v1/curriculum/*
│               ├── health.py          # /health & /db-test Probes
│               ├── questions.py       # /api/v1/questions/*
│               ├── study_notes.py     # /api/v1/study-notes/*
│               └── users.py           # /api/v1/users/*
├── tests/                             # Automated Backend Verification Suite
│   ├── __init__.py
│   └── test_health.py
├── main.py                            # Root Uvicorn / Cloud Run Entrypoint
├── requirements.txt                   # Pinned Production Dependencies
├── Dockerfile                         # Non-Root Hardened Container Recipe
├── .env.example                       # Environment Variable Template
├── .dockerignore                      # Container Build Exclusions
├── .gitignore                         # Git Exclusions
└── README.md                          # Architecture & Deployment Documentation
```

---

## 💻 1. Running Locally

### Step 1: Configure Environment
Copy `.env.example` to `.env` and fill in your local PostgreSQL / Firebase credentials:
```bash
cp .env.example .env
```

### Step 2: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Start the Server
```bash
uvicorn app.main:app --reload --port 8080
```
*(Or `python main.py`)*

---

## 🧪 2. Running Tests

```bash
cd backend
python -m unittest discover -s tests -v
```

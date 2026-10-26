"""baseline_schema

Revision ID: e904747c0713
Revises: 
Create Date: 2026-10-26 02:16:47.461526

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e904747c0713"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create baseline production schema in Cloud SQL PostgreSQL."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            sinhala_name VARCHAR(255),
            code VARCHAR(50) UNIQUE NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS syllabus_lessons (
            id VARCHAR(100) PRIMARY KEY,
            subject_id VARCHAR(100) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            sinhala_title VARCHAR(255),
            order_index INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            question_count INTEGER NOT NULL DEFAULT 0,
            premium_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS questions (
            id VARCHAR(100) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            subject_id VARCHAR(100) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            lesson_id VARCHAR(100) REFERENCES syllabus_lessons(id) ON DELETE SET NULL,
            content_text TEXT NOT NULL,
            type VARCHAR(50) NOT NULL DEFAULT 'SHORT' CHECK (type IN ('SHORT', 'ESSAY')),
            difficulty VARCHAR(50) NOT NULL DEFAULT 'MEDIUM' CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
            schedule VARCHAR(50) NOT NULL DEFAULT 'REGULAR' CHECK (schedule IN ('REGULAR', 'DAILY', 'WEEKLY', 'MONTHLY')),
            source VARCHAR(50) NOT NULL DEFAULT 'PAST_PAPER' CHECK (source IN ('PAST_PAPER', 'MODEL_PAPER', 'PROVINCIAL', 'SCHOOL_PAPER')),
            source_details TEXT DEFAULT '',
            allocated_marks INTEGER NOT NULL DEFAULT 25,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            is_published BOOLEAN NOT NULL DEFAULT TRUE,
            scheduled_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS marking_schemes (
            id UUID PRIMARY KEY,
            question_id VARCHAR(100) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL DEFAULT 'Official Marking Scheme',
            content_text TEXT NOT NULL,
            total_marks INTEGER NOT NULL DEFAULT 25,
            is_official BOOLEAN NOT NULL DEFAULT TRUE,
            is_premium_only BOOLEAN NOT NULL DEFAULT FALSE,
            order_index INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS study_notes (
            id VARCHAR(100) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            subject_id VARCHAR(100) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            lesson_id VARCHAR(100) REFERENCES syllabus_lessons(id) ON DELETE SET NULL,
            content_text TEXT NOT NULL DEFAULT '',
            pdf_url TEXT,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            order_index INTEGER NOT NULL DEFAULT 0,
            author VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_study_notes_subject_order
            ON study_notes(subject_id, order_index, created_at);
        CREATE INDEX IF NOT EXISTS idx_study_notes_subject_lesson
            ON study_notes(subject_id, lesson_id, order_index);

        CREATE TABLE IF NOT EXISTS users (
            uid VARCHAR(128) PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            telephone_no VARCHAR(50),
            role VARCHAR(50) DEFAULT 'USER' CHECK (role IN ('ADMIN', 'EDITOR', 'USER')),
            avatar_url TEXT,
            school_name VARCHAR(255),
            district VARCHAR(100),
            stream VARCHAR(50),
            grade VARCHAR(50),
            attempt VARCHAR(50),
            xp INT DEFAULT 0,
            streak_count INT DEFAULT 0,
            accuracy_rate DOUBLE PRECISION DEFAULT 0.0,
            questions_solved INT DEFAULT 0,
            is_premium BOOLEAN DEFAULT FALSE,
            premium_expiry DATE,
            current_streak_days INT DEFAULT 0,
            longest_streak_days INT DEFAULT 0,
            total_solved_count INT DEFAULT 0,
            total_study_time_seconds INT DEFAULT 0,
            last_active_date DATE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
    )


def downgrade() -> None:
    """Drop baseline tables in reverse dependency order."""
    op.execute(
        """
        DROP TABLE IF EXISTS marking_schemes CASCADE;
        DROP TABLE IF EXISTS questions CASCADE;
        DROP TABLE IF EXISTS study_notes CASCADE;
        DROP TABLE IF EXISTS syllabus_lessons CASCADE;
        DROP TABLE IF EXISTS subjects CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        """
    )

"""
Database operations for Maths DD Content Studio & Cloud SQL (PostgreSQL).
"""

import os
import uuid
from typing import List, Dict, Any, Optional
import asyncpg

DB_USER = os.environ.get("DB_USER", "chamod_rashmith")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "math-master-981fe-database")
INSTANCE_CONNECTION_NAME = os.environ.get(
    "INSTANCE_CONNECTION_NAME",
    "math-master-981fe:asia-south1:math-master-981fe-instance",
)


async def get_db_connection() -> asyncpg.Connection:
    """
    Establishes connection to Cloud SQL PostgreSQL.
    In Cloud Run: uses Unix domain socket.
    Locally: uses TCP fallback.
    """
    cloudsql_socket_dir = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"

    if os.path.exists(cloudsql_socket_dir):
        return await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=cloudsql_socket_dir,
        )
    else:
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = int(os.environ.get("DB_PORT", 5432))
        return await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=db_host,
            port=db_port,
        )


async def get_subjects() -> List[Dict[str, Any]]:
    conn = await get_db_connection()
    try:
        rows = await conn.fetch(
            "SELECT id, name, sinhala_name, code, order_index, description FROM subjects ORDER BY order_index ASC;"
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_lessons(subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = await get_db_connection()
    try:
        if subject_id:
            rows = await conn.fetch(
                """
                SELECT id, subject_id, title, sinhala_title, order_index, description 
                FROM syllabus_lessons 
                WHERE subject_id = $1 
                ORDER BY order_index ASC;
                """,
                subject_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, subject_id, title, sinhala_title, order_index, description 
                FROM syllabus_lessons 
                ORDER BY subject_id, order_index ASC;
                """
            )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def create_subject(id: str, name: str, sinhala_name: str, code: str, order_index: int, description: str = "") -> Dict[str, Any]:
    conn = await get_db_connection()
    try:
        query = """
        INSERT INTO subjects (id, name, sinhala_name, code, order_index, description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            sinhala_name = EXCLUDED.sinhala_name,
            code = EXCLUDED.code,
            order_index = EXCLUDED.order_index,
            description = EXCLUDED.description,
            updated_at = NOW()
        RETURNING *;
        """
        row = await conn.fetchrow(query, id, name, sinhala_name, code, order_index, description)
        return dict(row)
    finally:
        await conn.close()


async def create_lesson(id: str, subject_id: str, title: str, sinhala_title: str, order_index: int, description: str = "") -> Dict[str, Any]:
    conn = await get_db_connection()
    try:
        query = """
        INSERT INTO syllabus_lessons (id, subject_id, title, sinhala_title, order_index, description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            subject_id = EXCLUDED.subject_id,
            title = EXCLUDED.title,
            sinhala_title = EXCLUDED.sinhala_title,
            order_index = EXCLUDED.order_index,
            description = EXCLUDED.description,
            updated_at = NOW()
        RETURNING *;
        """
        row = await conn.fetchrow(query, id, subject_id, title, sinhala_title, order_index, description)
        return dict(row)
    finally:
        await conn.close()


async def create_question_with_solution(
    title: str,
    subject_id: str,
    lesson_id: Optional[str],
    content_text: str,
    solution_text: str,
    solution_title: str = "Official Marking Scheme",
    question_type: str = "SHORT",
    difficulty: str = "MEDIUM",
    schedule: str = "REGULAR",
    source: str = "PAST_PAPER",
    source_details: str = "",
    allocated_marks: int = 25,
    is_premium: bool = False,
    is_published: bool = True,
    scheduled_date: Optional[str] = None,
    custom_id: Optional[str] = None,
) -> Dict[str, Any]:
    conn = await get_db_connection()
    async with conn.transaction():
        # Generate question ID
        q_id = custom_id.strip() if (custom_id and custom_id.strip()) else f"q_{uuid.uuid4().hex[:10]}"

        # Insert question
        q_query = """
        INSERT INTO questions (
            id, title, subject_id, lesson_id, content_text,
            type, difficulty, schedule, source, source_details,
            allocated_marks, is_premium, is_published, scheduled_date,
            created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12, $13, $14::date,
            NOW(), NOW()
        )
        RETURNING id, title, subject_id, lesson_id, created_at;
        """
        q_row = await conn.fetchrow(
            q_query,
            q_id, title, subject_id, lesson_id, content_text,
            question_type, difficulty, schedule, source, source_details,
            allocated_marks, is_premium, is_published, scheduled_date
        )

        # Insert marking scheme / solution
        sol_id = uuid.uuid4()
        sol_query = """
        INSERT INTO marking_schemes (
            id, question_id, title, content_text, total_marks,
            is_official, is_premium_only, order_index, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            true, false, 1, NOW(), NOW()
        )
        RETURNING id, question_id, title;
        """
        sol_row = await conn.fetchrow(
            sol_query,
            sol_id, q_id, solution_title, solution_text, allocated_marks
        )

        return {
            "question": dict(q_row),
            "marking_scheme": dict(sol_row),
        }


async def get_recent_questions(limit: int = 10) -> List[Dict[str, Any]]:
    conn = await get_db_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT q.id, q.title, q.subject_id, q.type, q.difficulty, q.schedule, 
                   q.source, q.allocated_marks, q.is_published, q.created_at,
                   s.name as subject_name, l.title as lesson_title
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN syllabus_lessons l ON q.lesson_id = l.id
            ORDER BY q.created_at DESC
            LIMIT $1;
            """,
            limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def seed_default_curriculum():
    """
    Populates default Pure Maths and Applied Maths subjects and essential syllabus lessons
    if the database is currently empty.
    """
    conn = await get_db_connection()
    try:
        subject_count = await conn.fetchval("SELECT count(*) FROM subjects;")
        if subject_count > 0:
            return {"status": "skipped", "message": "Subjects already exist."}

        # Seed Subjects
        await conn.execute("""
            INSERT INTO subjects (id, name, sinhala_name, code, order_index, description, created_at, updated_at) VALUES
            ('pure_maths', 'Pure Mathematics', 'ශුද්ධ ගණිතය', 'PM', 1, 'Algebra, Calculus, Trigonometry, and Geometry', NOW(), NOW()),
            ('applied_maths', 'Applied Mathematics', 'භාවිත ගණිතය', 'AM', 2, 'Mechanics, Vectors, Probability, and Statistics', NOW(), NOW()),
            ('general_helper', 'General Helper', 'සාමාන්‍ය මාර්ගෝපදේශ', 'GH', 3, 'Formula sheets, examination tips', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """)

        # Seed Initial Pure Maths Lessons
        await conn.execute("""
            INSERT INTO syllabus_lessons (id, subject_id, title, sinhala_title, order_index, description, created_at, updated_at) VALUES
            ('pure_quadratic_equations', 'pure_maths', 'Quadratic Equations & Expressions', 'වර්ගජ සමීකරණ හා ප්‍රකාශන', 1, 'Roots, discriminants, sign diagrams', NOW(), NOW()),
            ('pure_differentiation', 'pure_maths', 'Differentiation', 'අවකලනය', 2, 'First principles, product rule, chain rule', NOW(), NOW()),
            ('pure_integration', 'pure_maths', 'Integration', 'අනුකලනය', 3, 'Standard integrals, by parts, substitution', NOW(), NOW()),
            ('pure_trigonometry', 'pure_maths', 'Trigonometry', 'ත්‍රිකෝණමිතිය', 4, 'Trigonometric identities, equations', NOW(), NOW()),
            ('pure_matrices', 'pure_maths', 'Matrices & Determinants', 'න්‍යාස හා නිශ්චායක', 5, 'Matrix operations, determinants, inverses', NOW(), NOW()),
            ('pure_complex_numbers', 'pure_maths', 'Complex Numbers', 'සංකීර්ණ සංඛ්‍යා', 6, 'Argand diagrams, modulus, argument', NOW(), NOW()),
            ('applied_vectors', 'applied_maths', 'Vectors in a Plane', 'තලයක දෛශික', 1, 'Vector addition, dot product', NOW(), NOW()),
            ('applied_kinematics', 'applied_maths', 'Straight Line Motion', 'සරල රේඛීය චලිතය', 2, 'Displacement-time, velocity-time graphs', NOW(), NOW()),
            ('applied_projectiles', 'applied_maths', 'Projectiles', 'ප්‍රක්ෂිප්ත', 3, 'Motion under gravity, trajectories', NOW(), NOW()),
            ('applied_equilibrium', 'applied_maths', 'Equilibrium of Coplanar Forces', 'තල බල සමතුලිතතාව', 4, 'Lami theorem, resolving forces', NOW(), NOW()),
            ('applied_probability', 'applied_maths', 'Probability', 'සම්භාවිතාව', 5, 'Independent events, conditional probability', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """)

        return {"status": "success", "message": "Standard Pure Maths and Applied Maths curriculum seeded successfully!"}
    finally:
        await conn.close()

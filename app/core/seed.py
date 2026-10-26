"""
Database seed script for Maths DD.
Populates initial Subjects, Lessons, Study Notes, and default Admin user idempotently.
Safe against existing unique constraints (email, subject code) and foreign keys.
"""

import logging
from typing import Dict
import asyncpg

logger = logging.getLogger("maths_dd.seed")

DEFAULT_ADMIN_UID = "admin_master_001"
DEFAULT_ADMIN_EMAIL = "admin@mathsdd.lk"
DEFAULT_ADMIN_NAME = "Super Admin"

SUBJECTS_SEED = [
    {
        "id": "subj_pmat",
        "name": "Pure Mathematics",
        "sinhala_name": "ශුද්ධ ගණිතය",
        "code": "PMAT",
        "order_index": 1,
        "description": "Pure Mathematics syllabus for G.C.E. A/L Combined Mathematics",
    },
    {
        "id": "subj_amat",
        "name": "Applied Mathematics",
        "sinhala_name": "ව්‍යවහාරික ගණිතය",
        "code": "AMAT",
        "order_index": 2,
        "description": "Applied Mathematics mechanics and statistics syllabus",
    },
]

LESSONS_SEED = [
    # Pure Mathematics Lessons
    {
        "id": "lesson_pmat_real_num",
        "subject_id": "subj_pmat",
        "title": "Real Numbers & Inequalities",
        "sinhala_title": "තාත්වික සංඛ්‍යා සහ අසමානතා",
        "order_index": 1,
        "description": "Properties of real numbers, modulus functions and solving inequalities.",
    },
    {
        "id": "lesson_pmat_poly",
        "subject_id": "subj_pmat",
        "title": "Polynomials & Quadratic Equations",
        "sinhala_title": "බහුපද සහ වර්ගජ සමීකරණ",
        "order_index": 2,
        "description": "Remainder theorem, quadratic roots, and discriminant analysis.",
    },
    {
        "id": "lesson_pmat_trig",
        "subject_id": "subj_pmat",
        "title": "Trigonometry",
        "sinhala_title": "ත්‍රිකෝණමිතිය",
        "order_index": 3,
        "description": "Compound angles, general solutions, and identities.",
    },
    {
        "id": "lesson_pmat_diff",
        "subject_id": "subj_pmat",
        "title": "Differentiation",
        "sinhala_title": "අවකලනය",
        "order_index": 4,
        "description": "Limits, derivatives from first principles, and applications of calculus.",
    },
    {
        "id": "lesson_pmat_int",
        "subject_id": "subj_pmat",
        "title": "Integration",
        "sinhala_title": "අනුකලනය",
        "order_index": 5,
        "description": "Techniques of integration, substitution, parts, and definite integrals.",
    },
    # Applied Mathematics Lessons
    {
        "id": "lesson_amat_vectors",
        "subject_id": "subj_amat",
        "title": "Vectors",
        "sinhala_title": "දෛශික",
        "order_index": 1,
        "description": "Vector addition, resolution, dot product and geometric proofs.",
    },
    {
        "id": "lesson_amat_straight_line",
        "subject_id": "subj_amat",
        "title": "Rectilinear Motion",
        "sinhala_title": "සරල රේඛීය චලිතය",
        "order_index": 2,
        "description": "Velocity-time graphs, equations of motion with constant acceleration.",
    },
    {
        "id": "lesson_amat_newton",
        "subject_id": "subj_amat",
        "title": "Newton's Laws & Friction",
        "sinhala_title": "නිව්ටන් නියම සහ ඝර්ෂණය",
        "order_index": 3,
        "description": "Forces, equilibrium, dynamics of connected particles, and friction.",
    },
    {
        "id": "lesson_amat_circular",
        "subject_id": "subj_amat",
        "title": "Circular Motion",
        "sinhala_title": "වෘත්ත චලිතය",
        "order_index": 4,
        "description": "Centripetal force, banked tracks, and conical pendulum.",
    },
]

STUDY_NOTES_SEED = [
    {
        "id": "note_pmat_induction_full",
        "title": "Mathematical Induction - Full Revision Note",
        "description": "Complete breakdown of mathematical induction with solved step-by-step proofs for A/L.",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_poly",
        "content_text": r"""# Mathematical Induction (ගණිත අභ්‍යුහනය)

The Principle of Mathematical Induction is used to prove that a proposition $P(n)$ is true for all natural numbers $n \ge 1$.

---

### Three Core Steps:
1. **Base Case**: Verify that $P(1)$ is true.
2. **Induction Hypothesis**: Assume that $P(k)$ is true for some positive integer $k$.
3. **Inductive Step**: Prove that $P(k+1)$ is true using the hypothesis.

$$ \sum_{r=1}^{n} r = \frac{n(n+1)}{2} $$

### Important Exam Tips:
* Always state the induction hypothesis clearly: *"Assume true for $n=k$"*.
* Substitute $k+1$ and express it in terms of the assumed formula.
* Conclude with the formal mathematical statement.
""",
        "pdf_url": None,
        "is_premium": False,
        "order_index": 1,
        "author": "Maths DD Academic Team",
    },
    {
        "id": "note_pmat_diff_shortcuts",
        "title": "Calculus Differentiation Formulas & Speed Tricks",
        "description": "Essential standard derivatives, chain rule, product rule, and parametric equations.",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_diff",
        "content_text": r"""# Differentiation Quick Reference (අවකලනය සූත්‍ර)

Standard derivatives that every student must memorize:

* $\frac{d}{dx}(x^n) = n x^{n-1}$
* $\frac{d}{dx}(\sin x) = \cos x$
* $\frac{d}{dx}(\cos x) = -\sin x$
* $\frac{d}{dx}(e^x) = e^x$
* $\frac{d}{dx}(\ln x) = \frac{1}{x}$

---

### Chain Rule (දාම නීතිය)
$$ \frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx} $$

### Product & Quotient Rules
$$ (uv)' = u'v + uv' $$
$$ \left(\frac{u}{v}\right)' = \frac{u'v - uv'}{v^2} $$
""",
        "pdf_url": None,
        "is_premium": False,
        "order_index": 2,
        "author": "Dr. S. K. Jayasinghe",
    },
    {
        "id": "note_amat_circular_motion",
        "title": "Circular Motion Principles & Centripetal Acceleration",
        "description": "Equations of horizontal and vertical circular motion, tension analysis and energy conservation.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_circular",
        "content_text": r"""# Circular Motion (වෘත්ත චලිතය)

When a particle moves in a circle of radius $r$ with constant speed $v$:

* Angular velocity: $\omega = \frac{v}{r}$
* Centripetal acceleration: $a = \frac{v^2}{r} = \omega^2 r$
* Central force: $F = m \frac{v^2}{r} = m \omega^2 r$

---

### Vertical Circular Motion
Conserve mechanical energy:
$$ \frac{1}{2}mv_0^2 = \frac{1}{2}mv^2 + mgh $$

At the top of the circle, for string not to slacken:
$$ v_{\text{top}} \ge \sqrt{gr} $$
$$ v_{\text{bottom}} \ge \sqrt{5gr} $$
""",
        "pdf_url": None,
        "is_premium": False,
        "order_index": 1,
        "author": "Eng. N. Perera",
    },
    {
        "id": "note_amat_projectile_pdf",
        "title": "Projectiles - Comprehensive Theory Guide (PDF)",
        "description": "Official past paper theory compilation and trajectory derivations.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_straight_line",
        "content_text": "",
        "pdf_url": "https://storage.googleapis.com/math-master-notes/applied/projectiles_theory_guide.pdf",
        "is_premium": True,
        "order_index": 2,
        "author": "Eng. N. Perera",
    },
]


async def seed_database(conn: asyncpg.Connection) -> None:
    """
    Seeds initial reference data if tables are empty or updates existing seeds idempotently.
    Resolves unique keys (users.email, subjects.code) prior to upsert to prevent constraint errors.
    """
    # 1. Seed Default Admin User (handle conflict on either uid or email)
    existing_admin_uid = await conn.fetchval(
        "SELECT uid FROM users WHERE uid = $1 OR LOWER(email) = LOWER($2) LIMIT 1;",
        DEFAULT_ADMIN_UID,
        DEFAULT_ADMIN_EMAIL,
    )
    if existing_admin_uid:
        await conn.execute(
            """
            UPDATE users
            SET role = 'ADMIN', is_premium = TRUE, updated_at = NOW()
            WHERE uid = $1;
            """,
            existing_admin_uid,
        )
    else:
        await conn.execute(
            """
            INSERT INTO users (uid, email, name, role, is_premium)
            VALUES ($1, $2, $3, 'ADMIN', TRUE)
            ON CONFLICT (uid) DO NOTHING;
            """,
            DEFAULT_ADMIN_UID,
            DEFAULT_ADMIN_EMAIL,
            DEFAULT_ADMIN_NAME,
        )

    # 2. Seed Subjects (resolve by id or code to avoid unique constraint violations on subjects.code)
    subject_id_map: Dict[str, str] = {}
    for s in SUBJECTS_SEED:
        existing_subj_id = await conn.fetchval(
            "SELECT id FROM subjects WHERE id = $1 OR UPPER(code) = UPPER($2) LIMIT 1;",
            s["id"],
            s["code"],
        )
        target_subj_id = existing_subj_id or s["id"]
        subject_id_map[s["id"]] = target_subj_id

        await conn.execute(
            """
            INSERT INTO subjects (id, name, sinhala_name, code, order_index, description)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                sinhala_name = EXCLUDED.sinhala_name,
                code = EXCLUDED.code,
                order_index = EXCLUDED.order_index,
                description = EXCLUDED.description,
                updated_at = NOW();
            """,
            target_subj_id,
            s["name"],
            s["sinhala_name"],
            s["code"],
            s["order_index"],
            s["description"],
        )

    # 3. Seed Lessons (using resolved subject_id)
    lesson_id_map: Dict[str, str] = {}
    for l in LESSONS_SEED:
        resolved_subj_id = subject_id_map.get(l["subject_id"], l["subject_id"])
        lesson_id_map[l["id"]] = l["id"]

        await conn.execute(
            """
            INSERT INTO syllabus_lessons (id, subject_id, title, sinhala_title, order_index, description)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE
            SET subject_id = EXCLUDED.subject_id,
                title = EXCLUDED.title,
                sinhala_title = EXCLUDED.sinhala_title,
                order_index = EXCLUDED.order_index,
                description = EXCLUDED.description,
                updated_at = NOW();
            """,
            l["id"],
            resolved_subj_id,
            l["title"],
            l["sinhala_title"],
            l["order_index"],
            l["description"],
        )

    # 4. Seed Study Notes (using resolved subject_id and lesson_id)
    for n in STUDY_NOTES_SEED:
        resolved_subj_id = subject_id_map.get(n["subject_id"], n["subject_id"])
        resolved_lesson_id = (
            lesson_id_map.get(n["lesson_id"], n["lesson_id"])
            if n.get("lesson_id")
            else None
        )

        await conn.execute(
            """
            INSERT INTO study_notes (id, title, description, subject_id, lesson_id, content_text, pdf_url, is_premium, order_index, author)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title,
                description = EXCLUDED.description,
                subject_id = EXCLUDED.subject_id,
                lesson_id = EXCLUDED.lesson_id,
                content_text = EXCLUDED.content_text,
                pdf_url = EXCLUDED.pdf_url,
                is_premium = EXCLUDED.is_premium,
                order_index = EXCLUDED.order_index,
                author = EXCLUDED.author,
                updated_at = NOW();
            """,
            n["id"],
            n["title"],
            n["description"],
            resolved_subj_id,
            resolved_lesson_id,
            n["content_text"],
            n["pdf_url"],
            n["is_premium"],
            n["order_index"],
            n["author"],
        )

    logger.info("Database seeding completed successfully.")

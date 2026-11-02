"""
Database seed script for Maths DD.
Populates initial Subjects, Lessons, Study Notes, and default Admin user idempotently.
Safe against existing unique constraints (email, subject code) and foreign keys.
"""

import logging
from typing import Dict
import datetime
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Subject, SyllabusLesson, Question, MarkingScheme, StudyNote, User, UserStats, UserSubscription

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

QUESTIONS_SEED = [
    {
        "id": "q_pmat_poly_daily_01",
        "title": "Quadratic Roots & Symmetric Functions Challenge",
        "description": "Find the quadratic equation whose roots are α²/β and β²/α given 2x² - 5x + 4 = 0.",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_poly",
        "content_text": r"""# Quadratic Roots & Symmetric Functions

Let $\alpha$ and $\beta$ be the roots of the quadratic equation:
$$ 2x^2 - 5x + 4 = 0 $$

1. Without solving the equation, find the values of $\alpha + \beta$, $\alpha\beta$, and $\alpha^3 + \beta^3$.
2. Hence, form a quadratic equation with integer coefficients whose roots are $\frac{\alpha^2}{\beta}$ and $\frac{\beta^2}{\alpha}$.
""",
        "solution_text": r"""# Official Marking Scheme (25 Marks)

### Step 1: Sum and Product of Roots (05 Marks)
From $2x^2 - 5x + 4 = 0$:
$$ \alpha + \beta = \frac{5}{2}, \quad \alpha\beta = 2 $$

### Step 2: Evaluate $\alpha^3 + \beta^3$ (10 Marks)
Using the identity $\alpha^3 + \beta^3 = (\alpha + \beta)^3 - 3\alpha\beta(\alpha + \beta)$:
$$ \alpha^3 + \beta^3 = \left(\frac{5}{2}\right)^3 - 3(2)\left(\frac{5}{2}\right) = \frac{125}{8} - 15 = \frac{5}{8} $$

### Step 3: New Sum and Product of Roots (10 Marks)
* **Sum ($S$):**
  $$ S = \frac{\alpha^2}{\beta} + \frac{\beta^2}{\alpha} = \frac{\alpha^3 + \beta^3}{\alpha\beta} = \frac{5/8}{2} = \frac{5}{16} $$
* **Product ($P$):**
  $$ P = \left(\frac{\alpha^2}{\beta}\right)\left(\frac{\beta^2}{\alpha}\right) = \alpha\beta = 2 $$

Required equation is $x^2 - Sx + P = 0 \implies 16x^2 - 5x + 32 = 0$.
""",
        "solution_id": "11111111-1111-4111-8111-111111111101",
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "DAILY",
        "source": "PAST_PAPER",
        "source_details": "G.C.E. A/L Combined Maths (Part A)",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "use_today_scheduled_date": True,
    },
    {
        "id": "q_pmat_diff_essay_01",
        "title": "First Principles & Stationary Points Analysis",
        "description": "Differentiate sin(2x) from first principles and analyze the stationary points of f(x).",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_diff",
        "content_text": r"""# Differentiation Structured Essay

**(a)** Using first principles, find the derivative of $f(x) = \sin(2x)$ with respect to $x$.

**(b)** Let $y = x^3 - 6x^2 + 9x + 1$.
1. Find $\frac{dy}{dx}$ and $\frac{d^2y}{dx^2}$.
2. Determine the coordinates of the stationary points and classify their nature.
3. Sketch the curve $y = f(x)$ showing all turning points and the $y$-intercept.
""",
        "solution_text": r"""# Official Marking Scheme (150 Marks)

### Part (a): First Principles (50 Marks)
$$ f'(x) = \lim_{h \to 0} \frac{\sin(2x + 2h) - \sin(2x)}{h} $$
$$ = \lim_{h \to 0} \frac{2\cos(2x + h)\sin(h)}{h} = 2\cos(2x) $$

### Part (b): Stationary Points (100 Marks)
* $\frac{dy}{dx} = 3x^2 - 12x + 9 = 3(x - 1)(x - 3)$
* $\frac{d^2y}{dx^2} = 6x - 12$
* At $x = 1$: $y = 5$ and $\frac{d^2y}{dx^2} = -6 < 0 \implies$ **Local Maximum** at $(1, 5)$.
* At $x = 3$: $y = 1$ and $\frac{d^2y}{dx^2} = +6 > 0 \implies$ **Local Minimum** at $(3, 1)$.
""",
        "solution_id": "11111111-1111-4111-8111-111111111102",
        "type": "ESSAY",
        "difficulty": "HARD",
        "schedule": "REGULAR",
        "source": "PAST_PAPER",
        "source_details": "2023 G.C.E. A/L Pure Maths Part B",
        "allocated_marks": 150,
        "is_premium": True,
        "is_published": True,
        "use_today_scheduled_date": False,
    },
    {
        "id": "q_amat_circular_short_01",
        "title": "Vertical Circular Motion of a Particle on a String",
        "description": "Calculate minimum projection speed and string tension for a particle in vertical circular motion.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_circular",
        "content_text": r"""# Vertical Circular Motion

A particle of mass $m$ is attached to one end of a light inextensible string of length $l$, whose other end is fixed at a point $O$. The particle hangs in equilibrium at the lowest point $A$ and is given a horizontal velocity $u = \sqrt{6gl}$.

1. Find the speed $v$ of the particle and the tension $T$ in the string when the string makes an angle $\theta$ with the downward vertical $OA$.
2. Show that the particle completes full vertical circles and find the ratio of the maximum tension to the minimum tension in the string.
""",
        "solution_text": r"""# Official Marking Scheme (25 Marks)

### 1. Energy Conservation & Radial Equation (15 Marks)
By conservation of mechanical energy:
$$ \frac{1}{2}mu^2 = \frac{1}{2}mv^2 + mgl(1 - \cos\theta) \implies v^2 = 4gl + 2gl\cos\theta $$

Applying $F = ma$ radially towards $O$:
$$ T - mg\cos\theta = \frac{mv^2}{l} \implies T = mg(4 + 3\cos\theta) $$

### 2. Tension Ratio (10 Marks)
* At the lowest point ($\theta = 0$): $T_{\max} = 7mg$
* At the highest point ($\theta = \pi$): $T_{\min} = mg > 0$ (completes full circle)
* Required ratio: $T_{\max} : T_{\min} = 7 : 1$.
""",
        "solution_id": "11111111-1111-4111-8111-111111111103",
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "REGULAR",
        "source": "MODEL_PAPER",
        "source_details": "Royal College Model Paper",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "use_today_scheduled_date": False,
    },
]


async def seed_database(session: AsyncSession) -> None:
    """
    Seeds initial reference data if tables are empty or updates existing seeds idempotently.
    Uses modern SQLAlchemy ORM models.
    """
    # 1. Seed Default Admin User
    admin = (
        await session.execute(
            select(User).where(
                (User.uid == DEFAULT_ADMIN_UID) | (func.lower(User.email) == DEFAULT_ADMIN_EMAIL.lower())
            )
        )
    ).scalar_one_or_none()

    admin_uid = DEFAULT_ADMIN_UID
    if admin:
        admin.role = "ADMIN"
        admin_uid = admin.uid
    else:
        session.add(
            User(
                uid=DEFAULT_ADMIN_UID,
                email=DEFAULT_ADMIN_EMAIL,
                name=DEFAULT_ADMIN_NAME,
                role="ADMIN",
            )
        )
    await session.flush()

    # Seed UserStats for Admin if not present
    admin_stats = (
        await session.execute(
            select(UserStats).where(UserStats.user_id == admin_uid)
        )
    ).scalar_one_or_none()
    if not admin_stats:
        session.add(UserStats(user_id=admin_uid))
    await session.flush()

    # Seed Lifetime UserSubscription for Admin if not present
    admin_sub = (
        await session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == admin_uid,
                UserSubscription.status == "ACTIVE",
            )
        )
    ).scalar_one_or_none()
    if not admin_sub:
        session.add(
            UserSubscription(
                user_id=admin_uid,
                plan_id="LIFETIME",
                status="ACTIVE",
                provider="MANUAL_ADMIN",
                admin_notes="Default seeded Master Admin entitlement",
                starts_at=datetime.datetime.now(ZoneInfo("UTC")),
                expires_at=None,
                is_auto_renew=False,
            )
        )
    await session.flush()

    # 2. Seed Subjects
    subject_id_map: Dict[str, str] = {}
    for s in SUBJECTS_SEED:
        existing_subj = (
            await session.execute(
                select(Subject).where(
                    (Subject.id == s["id"]) | (func.upper(Subject.code) == s["code"].upper())
                )
            )
        ).scalar_one_or_none()

        if existing_subj:
            existing_subj.name = s["name"]
            existing_subj.sinhala_name = s["sinhala_name"]
            existing_subj.code = s["code"]
            existing_subj.order_index = s["order_index"]
            existing_subj.description = s["description"]
            subject_id_map[s["id"]] = existing_subj.id
        else:
            session.add(
                Subject(
                    id=s["id"],
                    name=s["name"],
                    sinhala_name=s["sinhala_name"],
                    code=s["code"],
                    order_index=s["order_index"],
                    description=s["description"],
                )
            )
            subject_id_map[s["id"]] = s["id"]
    await session.flush()

    # 3. Seed Lessons
    lesson_id_map: Dict[str, str] = {}
    for l in LESSONS_SEED:
        resolved_subj_id = subject_id_map.get(l["subject_id"], l["subject_id"])
        lesson_id_map[l["id"]] = l["id"]

        existing_lesson = (
            await session.execute(select(SyllabusLesson).where(SyllabusLesson.id == l["id"]))
        ).scalar_one_or_none()

        if existing_lesson:
            existing_lesson.subject_id = resolved_subj_id
            existing_lesson.title = l["title"]
            existing_lesson.sinhala_title = l["sinhala_title"]
            existing_lesson.order_index = l["order_index"]
            existing_lesson.description = l["description"]
        else:
            session.add(
                SyllabusLesson(
                    id=l["id"],
                    subject_id=resolved_subj_id,
                    title=l["title"],
                    sinhala_title=l["sinhala_title"],
                    order_index=l["order_index"],
                    description=l["description"],
                )
            )
    await session.flush()

    # 4. Seed Study Notes
    for n in STUDY_NOTES_SEED:
        resolved_subj_id = subject_id_map.get(n["subject_id"], n["subject_id"])
        resolved_lesson_id = (
            lesson_id_map.get(n["lesson_id"], n["lesson_id"])
            if n.get("lesson_id")
            else None
        )

        existing_note = (
            await session.execute(select(StudyNote).where(StudyNote.id == n["id"]))
        ).scalar_one_or_none()

        if existing_note:
            existing_note.title = n["title"]
            existing_note.description = n.get("description")
            existing_note.subject_id = resolved_subj_id
            existing_note.lesson_id = resolved_lesson_id
            existing_note.content_text = n.get("content_text", "")
            existing_note.pdf_url = n.get("pdf_url")
            existing_note.is_premium = n["is_premium"]
            existing_note.order_index = n["order_index"]
            existing_note.author = n.get("author")
        else:
            session.add(
                StudyNote(
                    id=n["id"],
                    title=n["title"],
                    description=n.get("description"),
                    subject_id=resolved_subj_id,
                    lesson_id=resolved_lesson_id,
                    content_text=n.get("content_text", ""),
                    pdf_url=n.get("pdf_url"),
                    is_premium=n["is_premium"],
                    order_index=n["order_index"],
                    author=n.get("author"),
                )
            )
    await session.flush()

    # 5. Seed Questions & Marking Schemes
    today_colombo = datetime.datetime.now(ZoneInfo("Asia/Colombo")).date()

    for q in QUESTIONS_SEED:
        resolved_subj_id = subject_id_map.get(q["subject_id"], q["subject_id"])
        resolved_lesson_id = (
            lesson_id_map.get(q["lesson_id"], q["lesson_id"])
            if q.get("lesson_id")
            else None
        )
        sched_date = today_colombo if q.get("use_today_scheduled_date") else None

        existing_q = (
            await session.execute(select(Question).where(Question.id == q["id"]))
        ).scalar_one_or_none()

        if existing_q:
            existing_q.title = q["title"]
            existing_q.description = q.get("description", "")
            existing_q.subject_id = resolved_subj_id
            existing_q.lesson_id = resolved_lesson_id
            existing_q.content_text = q.get("content_text", "")
            existing_q.type = q["type"]
            existing_q.difficulty = q["difficulty"]
            existing_q.schedule = q["schedule"]
            existing_q.source = q["source"]
            existing_q.source_details = q.get("source_details", "")
            existing_q.allocated_marks = q["allocated_marks"]
            existing_q.is_premium = q["is_premium"]
            existing_q.is_published = q["is_published"]
            if sched_date:
                existing_q.scheduled_date = sched_date
        else:
            session.add(
                Question(
                    id=q["id"],
                    title=q["title"],
                    description=q.get("description", ""),
                    subject_id=resolved_subj_id,
                    lesson_id=resolved_lesson_id,
                    content_text=q.get("content_text", ""),
                    type=q["type"],
                    difficulty=q["difficulty"],
                    schedule=q["schedule"],
                    source=q["source"],
                    source_details=q.get("source_details", ""),
                    allocated_marks=q["allocated_marks"],
                    is_premium=q["is_premium"],
                    is_published=q["is_published"],
                    scheduled_date=sched_date,
                )
            )
        await session.flush()

        sol_uuid = uuid.UUID(q["solution_id"])
        existing_ms = (
            await session.execute(select(MarkingScheme).where(MarkingScheme.id == sol_uuid))
        ).scalar_one_or_none()

        if existing_ms:
            existing_ms.content_text = q["solution_text"]
            existing_ms.total_marks = q["allocated_marks"]
            existing_ms.is_premium_only = q["is_premium"]
        else:
            session.add(
                MarkingScheme(
                    id=sol_uuid,
                    question_id=q["id"],
                    title="Official Marking Scheme",
                    content_text=q["solution_text"],
                    total_marks=q["allocated_marks"],
                    is_official=True,
                    is_premium_only=q["is_premium"],
                    order_index=1,
                )
            )

    await session.commit()
    logger.info("Database seeding completed successfully via SQLAlchemy.")

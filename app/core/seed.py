"""
Database seed script for Maths DD.
Populates initial Subjects, Lessons (with hierarchy), Exam Papers, Study Notes, Questions,
Marking Schemes (with steps), Subscription Plans (with prices), Daily Challenges, and default Admin user idempotently.

===============================================================================
දත්ත සමුදාය ආරම්භක දත්ත පිරවීම (Database Seed Script):
-------------------------------------------------------------------------------
1. ශ්‍රී ලංකා පරිපාලන දිස්ත්‍රික්ක 25 (Districts 1-25).
2. A/L සංයුක්ත ගණිතය විෂයයන් (Pure Maths, Applied Maths).
3. විෂය නිර්දේශයේ ප්‍රධාන Units සහ උප-පාඩම් (Hierarchical Lessons).
4. පසුගිය විභාග ප්‍රශ්න පත්‍ර (Exam Papers 2022, 2023).
5. ගෙවීම් පැකේජ සහ මිල ගණන් (Subscription Plans & Plan Prices in minor cents).
6. දිනපතා අභ්‍යාස මාලාව (Daily Challenges 1 to 5).
7. විවරණ සහ ලකුණු දීමේ පටිපාටි පියවර (Marking Schemes & Rubric Steps).
8. සුපිරි පරිපාලක ගිණුම (Admin User, Stats & StudentProfile).
===============================================================================
"""

import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    District,
    Subject,
    SyllabusLesson,
    Question,
    MarkingScheme,
    StudyNote,
    ExamPaper,
    User,
    StudentProfile,
    UserStats,
    UserSubscription,
    SubscriptionPlan,
    PlanPrice,
    DailyChallenge,
    DailyChallengeQuestion,
)

logger = logging.getLogger("maths_dd.seed")

DEFAULT_ADMIN_UID = "admin_master_001"
DEFAULT_ADMIN_EMAIL = "admin@mathsdd.lk"
DEFAULT_ADMIN_NAME = "Super Admin"

DISTRICTS_SEED = [
    # Western Province
    {"id": 1, "code": "COLOMBO", "name_en": "Colombo", "name_si": "කොළඹ", "name_ta": "கொழும்பு", "province": "WESTERN", "display_order": 1},
    {"id": 2, "code": "GAMPAHA", "name_en": "Gampaha", "name_si": "ගම්පහ", "name_ta": "கம்பஹா", "province": "WESTERN", "display_order": 2},
    {"id": 3, "code": "KALUTARA", "name_en": "Kalutara", "name_si": "කළුතර", "name_ta": "களுத்துறை", "province": "WESTERN", "display_order": 3},
    # Central Province
    {"id": 4, "code": "KANDY", "name_en": "Kandy", "name_si": "මහනුවර", "name_ta": "கண்டி", "province": "CENTRAL", "display_order": 4},
    {"id": 5, "code": "MATALE", "name_en": "Matale", "name_si": "මාතලේ", "name_ta": "மாத்தளை", "province": "CENTRAL", "display_order": 5},
    {"id": 6, "code": "NUWARA_ELIYA", "name_en": "Nuwara Eliya", "name_si": "නුවරඑළිය", "name_ta": "நுவரெலியா", "province": "CENTRAL", "display_order": 6},
    # Southern Province
    {"id": 7, "code": "GALLE", "name_en": "Galle", "name_si": "ගාල්ල", "name_ta": "காலி", "province": "SOUTHERN", "display_order": 7},
    {"id": 8, "code": "MATARA", "name_en": "Matara", "name_si": "මාතර", "name_ta": "மாத்தறை", "province": "SOUTHERN", "display_order": 8},
    {"id": 9, "code": "HAMBANTOTA", "name_en": "Hambantota", "name_si": "හම්බන්තොට", "name_ta": "அம்பாந்தோட்டை", "province": "SOUTHERN", "display_order": 9},
    # Northern Province
    {"id": 10, "code": "JAFFNA", "name_en": "Jaffna", "name_si": "යාපනය", "name_ta": "யாழ்ப்பாணம்", "province": "NORTHERN", "display_order": 10},
    {"id": 11, "code": "KILINOCHCHI", "name_en": "Kilinochchi", "name_si": "කිලිනොච්චිය", "name_ta": "கிளிநொச்சி", "province": "NORTHERN", "display_order": 11},
    {"id": 12, "code": "MANNAR", "name_en": "Mannar", "name_si": "මන්නාරම", "name_ta": "மன்னார்", "province": "NORTHERN", "display_order": 12},
    {"id": 13, "code": "VAVUNIYA", "name_en": "Vavuniya", "name_si": "වවුනියාව", "name_ta": "வவுனியா", "province": "NORTHERN", "display_order": 13},
    {"id": 14, "code": "MULLAITIVU", "name_en": "Mullaitivu", "name_si": "මුලතිව්", "name_ta": "முல்லைத்தீவு", "province": "NORTHERN", "display_order": 14},
    # Eastern Province
    {"id": 15, "code": "BATTICALOA", "name_en": "Batticaloa", "name_si": "මඩකලපුව", "name_ta": "மட்டக்களப்பு", "province": "EASTERN", "display_order": 15},
    {"id": 16, "code": "AMPARA", "name_en": "Ampara", "name_si": "අම්පාර", "name_ta": "அம்பாறை", "province": "EASTERN", "display_order": 16},
    {"id": 17, "code": "TRINCOMALEE", "name_en": "Trincomalee", "name_si": "ත්‍රිකුණාමලය", "name_ta": "திருகோணமலை", "province": "EASTERN", "display_order": 17},
    # North Western Province
    {"id": 18, "code": "KURUNEGALA", "name_en": "Kurunegala", "name_si": "කුරුණෑගල", "name_ta": "குருணாகல்", "province": "NORTH_WESTERN", "display_order": 18},
    {"id": 19, "code": "PUTTALAM", "name_en": "Puttalam", "name_si": "පුත්තලම", "name_ta": "புத்தளம்", "province": "NORTH_WESTERN", "display_order": 19},
    # North Central Province
    {"id": 20, "code": "ANURADHAPURA", "name_en": "Anuradhapura", "name_si": "අනුරාධපුරය", "name_ta": "அனுராதபுரம்", "province": "NORTH_CENTRAL", "display_order": 20},
    {"id": 21, "code": "POLONNARUWA", "name_en": "Polonnaruwa", "name_si": "පොළොන්නරුව", "name_ta": "பொலன்னறுவை", "province": "NORTH_CENTRAL", "display_order": 21},
    # Uva Province
    {"id": 22, "code": "BADULLA", "name_en": "Badulla", "name_si": "බදුල්ල", "name_ta": "பதுளை", "province": "UVA", "display_order": 22},
    {"id": 23, "code": "MONARAGALA", "name_en": "Monaragala", "name_si": "මොනරාගල", "name_ta": "மொணරාகலை", "province": "UVA", "display_order": 23},
    # Sabaragamuwa Province
    {"id": 24, "code": "RATNAPURA", "name_en": "Ratnapura", "name_si": "රත්නපුර", "name_ta": "இரத்தினபுரி", "province": "SABARAGAMUWA", "display_order": 24},
    {"id": 25, "code": "KEGALLE", "name_en": "Kegalle", "name_si": "කෑගල්ල", "name_ta": "கேகாலை", "province": "SABARAGAMUWA", "display_order": 25},
]

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

# Lessons and Hierarchical Sub-lessons (Main Units: parent_lesson_id = None)
LESSONS_SEED = [
    # -------------------------------------------------------------------------
    # Pure Mathematics Units & Sub-lessons
    # -------------------------------------------------------------------------
    {
        "id": "lesson_pmat_real_num",
        "subject_id": "subj_pmat",
        "parent_lesson_id": None,
        "title": "Real Numbers & Inequalities",
        "sinhala_title": "තාත්වික සංඛ්‍යා සහ අසමානතා",
        "order_index": 1,
        "description": "Properties of real numbers, modulus functions and solving inequalities.",
    },
    {
        "id": "lesson_pmat_poly",
        "subject_id": "subj_pmat",
        "parent_lesson_id": None,
        "title": "Polynomials & Quadratic Equations",
        "sinhala_title": "බහුපද සහ වර්ගජ සමීකරණ",
        "order_index": 2,
        "description": "Remainder theorem, quadratic roots, and discriminant analysis.",
    },
    {
        "id": "lesson_pmat_poly_roots",
        "subject_id": "subj_pmat",
        "parent_lesson_id": "lesson_pmat_poly",
        "title": "Roots of Quadratic Equations",
        "sinhala_title": "වර්ගජ සමීකරණවල මූල සහ සම්බන්ධතා",
        "order_index": 1,
        "description": "Symmetric functions of roots, sign of quadratic expressions.",
    },
    {
        "id": "lesson_pmat_poly_induction",
        "subject_id": "subj_pmat",
        "parent_lesson_id": "lesson_pmat_poly",
        "title": "Mathematical Induction",
        "sinhala_title": "ගණිත අභ්‍යුහන මූලධර්මය",
        "order_index": 2,
        "description": "Principle of mathematical induction proofs for series and divisibility.",
    },
    {
        "id": "lesson_pmat_trig",
        "subject_id": "subj_pmat",
        "parent_lesson_id": None,
        "title": "Trigonometry",
        "sinhala_title": "ත්‍රිකෝණමිතිය",
        "order_index": 3,
        "description": "Compound angles, general solutions, and identities.",
    },
    {
        "id": "lesson_pmat_trig_identities",
        "subject_id": "subj_pmat",
        "parent_lesson_id": "lesson_pmat_trig",
        "title": "Trigonometric Identities & Compound Angles",
        "sinhala_title": "ත්‍රිකෝණමිතික සර්වසාම්‍ය සහ සංයුක්ත කෝණ",
        "order_index": 1,
        "description": "Sin(A+B), Cos(A+B), double and half angle expansions.",
    },
    {
        "id": "lesson_pmat_trig_equations",
        "subject_id": "subj_pmat",
        "parent_lesson_id": "lesson_pmat_trig",
        "title": "General Solutions of Trig Equations",
        "sinhala_title": "ත්‍රිකෝණමිතික සමීකරණ සහ සාමාන්‍ය විසඳුම්",
        "order_index": 2,
        "description": "Finding general solutions in radians for periodic functions.",
    },
    {
        "id": "lesson_pmat_diff",
        "subject_id": "subj_pmat",
        "parent_lesson_id": None,
        "title": "Differentiation",
        "sinhala_title": "අවකලනය",
        "order_index": 4,
        "description": "Limits, derivatives from first principles, and applications of calculus.",
    },
    {
        "id": "lesson_pmat_diff_first_principles",
        "subject_id": "subj_pmat",
        "parent_lesson_id": "lesson_pmat_diff",
        "title": "Derivatives from First Principles",
        "sinhala_title": "ප්‍රථම මූලධර්මයෙන් අවකලනය",
        "order_index": 1,
        "description": "Formal limit definition of derivatives for algebraic and trigonometric functions.",
    },
    {
        "id": "lesson_pmat_diff_max_min",
        "subject_id": "subj_pmat",
        "parent_lesson_id": "lesson_pmat_diff",
        "title": "Stationary Points & Curve Sketching",
        "sinhala_title": "නිශ්චල ලක්ෂ්‍ය සහ ප්‍රස්තාර ඇඳීම",
        "order_index": 2,
        "description": "First and second derivative tests, concavity and turning point classification.",
    },
    {
        "id": "lesson_pmat_int",
        "subject_id": "subj_pmat",
        "parent_lesson_id": None,
        "title": "Integration",
        "sinhala_title": "අනුකලනය",
        "order_index": 5,
        "description": "Techniques of integration, substitution, parts, and definite integrals.",
    },

    # -------------------------------------------------------------------------
    # Applied Mathematics Units & Sub-lessons
    # -------------------------------------------------------------------------
    {
        "id": "lesson_amat_vectors",
        "subject_id": "subj_amat",
        "parent_lesson_id": None,
        "title": "Vectors",
        "sinhala_title": "දෛශික",
        "order_index": 1,
        "description": "Vector addition, resolution, dot product and geometric proofs.",
    },
    {
        "id": "lesson_amat_straight_line",
        "subject_id": "subj_amat",
        "parent_lesson_id": None,
        "title": "Rectilinear Motion",
        "sinhala_title": "සරල රේඛීය චලිතය",
        "order_index": 2,
        "description": "Velocity-time graphs, equations of motion with constant acceleration.",
    },
    {
        "id": "lesson_amat_vt_graphs",
        "subject_id": "subj_amat",
        "parent_lesson_id": "lesson_amat_straight_line",
        "title": "Velocity-Time (v-t) Graphs",
        "sinhala_title": "ප්‍රවේග-කාල ප්‍රස්තාර භාවිතය",
        "order_index": 1,
        "description": "Using area for displacement and gradient for acceleration in multi-stage motion.",
    },
    {
        "id": "lesson_amat_newton",
        "subject_id": "subj_amat",
        "parent_lesson_id": None,
        "title": "Newton's Laws & Friction",
        "sinhala_title": "නිව්ටන් නියම සහ ඝර්ෂණය",
        "order_index": 3,
        "description": "Forces, equilibrium, dynamics of connected particles, and friction.",
    },
    {
        "id": "lesson_amat_circular",
        "subject_id": "subj_amat",
        "parent_lesson_id": None,
        "title": "Circular Motion",
        "sinhala_title": "වෘත්ත චලිතය",
        "order_index": 4,
        "description": "Centripetal force, banked tracks, and conical pendulum.",
    },
    {
        "id": "lesson_amat_circular_vert",
        "subject_id": "subj_amat",
        "parent_lesson_id": "lesson_amat_circular",
        "title": "Vertical Circular Motion",
        "sinhala_title": "සිරස් තලයක වෘත්ත චලිතය",
        "order_index": 1,
        "description": "Energy conservation and radial string tension analysis.",
    },
    {
        "id": "lesson_amat_kinematics",
        "subject_id": "subj_amat",
        "parent_lesson_id": None,
        "title": "Relative Velocity & Kinematics",
        "sinhala_title": "සාපේක්ෂ ප්‍රවේගය සහ චාලක විද්‍යාව",
        "order_index": 5,
        "description": "Relative motion, shortest distance, wind-plane problems and collisions.",
    },
]

EXAM_PAPERS_SEED = [
    {
        "id": "paper_2023_al_combined_p1",
        "subject_id": "subj_pmat",
        "type": "AL_GOVT",
        "year": 2023,
        "part": "PART_I",
        "title_si": "2023 අ.පො.ස. (උ.පෙළ) - සංයුක්ත ගණිතය I (ශුද්ධ ගණිතය)",
        "title_en": "2023 G.C.E. A/L Combined Mathematics I (Pure Maths)",
        "source_pdf_url": "https://storage.googleapis.com/math-master-papers/al_2023_p1.pdf",
    },
    {
        "id": "paper_2023_al_combined_p2",
        "subject_id": "subj_amat",
        "type": "AL_GOVT",
        "year": 2023,
        "part": "PART_II_A",
        "title_si": "2023 අ.පො.ස. (උ.පෙළ) - සංයුක්ත ගණිතය II (ව්‍යවහාරික ගණිතය)",
        "title_en": "2023 G.C.E. A/L Combined Mathematics II (Applied Maths)",
        "source_pdf_url": "https://storage.googleapis.com/math-master-papers/al_2023_p2.pdf",
    },
    {
        "id": "paper_2022_al_combined_p1",
        "subject_id": "subj_pmat",
        "type": "AL_GOVT",
        "year": 2022,
        "part": "PART_I",
        "title_si": "2022 අ.පො.ස. (උ.පෙළ) - සංයුක්ත ගණිතය I (ශුද්ධ ගණිතය)",
        "title_en": "2022 G.C.E. A/L Combined Mathematics I (Pure Maths)",
        "source_pdf_url": "https://storage.googleapis.com/math-master-papers/al_2022_p1.pdf",
    },
]

SUBSCRIPTION_PLANS_SEED = [
    {
        "id": "plan_monthly_pro",
        "code": "COMBINED_PRO_MONTHLY",
        "name_si": "මාසික Pro සාමාජිකත්වය (දින 30)",
        "name_en": "Combined Maths Pro Monthly",
        "interval": "MONTH",
        "duration_days": 30,
        "features": [
            "සියලුම පසුගිය විභාග වීඩියෝ විවරණ",
            "දිනපතා අභ්‍යාස අසීමිත ප්‍රවේශය",
            "විශේෂිත සංශෝධන සටහන් (PDF)",
        ],
        "display_order": 1,
        "amount_minor": 150000,  # Rs. 1,500.00
    },
    {
        "id": "plan_yearly_pro",
        "code": "COMBINED_PRO_YEARLY",
        "name_si": "වාර්ෂික Pro සාමාජිකත්වය (වසර 1)",
        "name_en": "Combined Maths Pro Yearly",
        "interval": "YEAR",
        "duration_days": 365,
        "features": [
            "සම්පූර්ණ විෂය නිර්දේශ ආවරණය",
            "සියලුම Marking Schemes සහ පියවර ලකුණු",
            "පෞද්ගලික ප්‍රගති වාර්තා සහ Streak ආරක්ෂාව",
        ],
        "display_order": 2,
        "amount_minor": 1200000,  # Rs. 12,000.00
    },
    {
        "id": "plan_al_batch_pass",
        "code": "AL_BATCH_PASS",
        "name_si": "A/L විභාගය දක්වා Full Batch Pass",
        "name_en": "Complete A/L Batch Access Pass",
        "interval": "FIXED_EXAM_DATE",
        "duration_days": 730,
        "features": [
            "විභාගය දක්වා අඛණ්ඩ ප්‍රවේශය",
            "ආදර්ශ ප්‍රශ්න පත්‍ර සාකච්ඡා",
            "ගුරුවරුන්ගෙන් කෙළින්ම ගැටළු විසඳා ගැනීම",
        ],
        "display_order": 3,
        "amount_minor": 1800000,  # Rs. 18,000.00
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

# Fixed series anchor date: Day 1 of the Combined Maths Challenge started on 2026-11-04.
# All subsequent challenge days advance sequentially by 1 calendar day per day_number.
SERIES_START_DATE = datetime.date(2026, 11, 4)


def _compute_challenge_date(day_number: Optional[int]) -> Optional[datetime.date]:
    """Computes fixed calendar date for a given sequential daily challenge day."""
    if day_number is not None and day_number >= 1:
        return SERIES_START_DATE + datetime.timedelta(days=day_number - 1)
    return None


QUESTIONS_SEED = [
    {
        "id": "q_pmat_poly_daily_01",
        "title": "Quadratic Roots & Symmetric Functions Challenge",
        "description": "Find the quadratic equation whose roots are α²/β and β²/α given 2x² - 5x + 4 = 0.",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_poly",
        "exam_paper_id": "paper_2023_al_combined_p1",
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
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 5, "description_si": "මූලවල එකතුව සහ ගුණිතය ලිවීම: $\\alpha+\\beta=5/2, \\alpha\\beta=2$"},
            {"step_number": 2, "step_type": "METHOD", "marks": 10, "description_si": "සර්වසාම්‍ය භාවිතයෙන් $\\alpha^3+\\beta^3 = 5/8$ අගය ලබා ගැනීම"},
            {"step_number": 3, "step_type": "FINAL", "marks": 10, "description_si": "නව සමීකරණය ගොඩනැගීම: $16x^2 - 5x + 32 = 0$"},
        ],
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "DAILY",
        "source": "PAST_PAPER",
        "source_details": "2023 G.C.E. A/L Combined Maths (Part A)",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "day_number": 1,
    },
    {
        "id": "q_pmat_diff_essay_01",
        "title": "First Principles & Stationary Points Analysis",
        "description": "Differentiate sin(2x) from first principles and analyze the stationary points of f(x).",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_diff",
        "exam_paper_id": "paper_2023_al_combined_p1",
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
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 25, "description_si": "ප්‍රථම මූලධර්ම සීමා ප්‍රකාශනය ලිවීම: $\\lim_{h \\to 0} \\frac{\\sin(2x+2h)-\\sin(2x)}{h}$"},
            {"step_number": 2, "step_type": "ACCURACY", "marks": 25, "description_si": "සූත්‍ර භාවිතයෙන් සරල කර අවකලන සංගුණකය $2\\cos(2x)$ ලෙස ලබා ගැනීම"},
            {"step_number": 3, "step_type": "METHOD", "marks": 50, "description_si": "පළමු සහ දෙවන අවකලන ලබාගෙන නිශ්චල ලක්ෂ්‍ය $(1, 5)$ සහ $(3, 1)$ සෙවීම"},
            {"step_number": 4, "step_type": "FINAL", "marks": 50, "description_si": "දෙවන අවකලනයේ ලකුණ අනුව උපරිම/අවම නිගමනය සහ ප්‍රස්තාර සටහන"},
        ],
        "type": "ESSAY",
        "difficulty": "HARD",
        "schedule": "DAILY",
        "source": "PAST_PAPER",
        "source_details": "2023 G.C.E. A/L Pure Maths Part B",
        "allocated_marks": 150,
        "is_premium": False,
        "is_published": True,
        "day_number": 1,
    },
    {
        "id": "q_amat_circular_short_01",
        "title": "Vertical Circular Motion of a Particle on a String",
        "description": "Calculate minimum projection speed and string tension for a particle in vertical circular motion.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_circular",
        "exam_paper_id": "paper_2023_al_combined_p2",
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
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 10, "description_si": "යාන්ත්‍රික ශක්ති සංස්ථිති මූලධර්මය යොදා $v^2$ සෙවීම"},
            {"step_number": 2, "step_type": "METHOD", "marks": 5, "description_si": "කේන්ද්‍රය දෙසට චලිත සමීකරණයෙන් තෙරපුම $T$ සඳහා ප්‍රකාශනය ගැනීම"},
            {"step_number": 3, "step_type": "FINAL", "marks": 10, "description_si": "උපරිම හා අවම ආතති අනුපාතය $7:1$ බව පෙන්වීම"},
        ],
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "DAILY",
        "source": "MODEL_PAPER",
        "source_details": "Royal College Model Paper",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "day_number": 1,
    },
    {
        "id": "q_amat_relvel_essay_01",
        "title": "Relative Velocity & Shortest Distance Interception",
        "description": "Two ships A and B moving with uniform velocities. Find shortest distance and closest approach time.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_kinematics",
        "exam_paper_id": "paper_2023_al_combined_p2",
        "content_text": r"""# Relative Velocity Structured Essay (Part B)

Ship $A$ is steaming due North at a constant speed of $20\text{ km/h}$. At 12:00 noon, ship $B$ is $40\text{ km}$ due East of $A$ and is steaming North-$60^\circ$-West at $20\sqrt{3}\text{ km/h}$.

1. Find the velocity of $B$ relative to $A$ in magnitude and direction.
2. Find the shortest distance between the two ships during their subsequent motion.
3. Determine the time at which the ships are closest to each other.
""",
        "solution_text": r"""# Official Marking Scheme (50 Marks)

### Step 1: Relative Velocity Vector (15 Marks)
$$\mathbf{v}_A = 20\mathbf{j}$$
$$\mathbf{v}_B = -20\sqrt{3}\sin(60^\circ)\mathbf{i} + 20\sqrt{3}\cos(60^\circ)\mathbf{j} = -30\mathbf{i} + 10\sqrt{3}\mathbf{j}$$
$$\mathbf{v}_{B/A} = \mathbf{v}_B - \mathbf{v}_A = -30\mathbf{i} + (10\sqrt{3} - 20)\mathbf{j}$$

### Step 2: Magnitude & Direction (15 Marks)
$$|\mathbf{v}_{B/A}| = \sqrt{(-30)^2 + (10\sqrt{3} - 20)^2} = 30.1\text{ km/h}$$

### Step 3: Shortest Distance & Closest Time (20 Marks)
Using relative position triangle: $d_{\min} = 40 \times \sin(\theta) = 3.56\text{ km}$.
Time: $t = 12:00 + \frac{40\cos\theta}{|\mathbf{v}_{B/A}|} \approx 1:19\text{ PM}$.
""",
        "solution_id": "11111111-1111-4111-8111-111111111104",
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 15, "description_si": "දෛශික මඟින් $A$ ට සාපේක්ෂව $B$ හි සාපේක්ෂ ප්‍රවේගය ලිවීම"},
            {"step_number": 2, "step_type": "ACCURACY", "marks": 15, "description_si": "සාපේක්ෂ ප්‍රවේගයේ විශාලත්වය සහ දිශාව ගණනය කිරීම"},
            {"step_number": 3, "step_type": "FINAL", "marks": 20, "description_si": "ලම්බ දුර මඟින් කෙටිම දුර සහ ආසන්නතම වේලාව නිවැරදිව ලබා ගැනීම"},
        ],
        "type": "ESSAY",
        "difficulty": "HARD",
        "schedule": "DAILY",
        "source": "PAST_PAPER",
        "source_details": "G.C.E. A/L Applied Maths Part B",
        "allocated_marks": 50,
        "is_premium": False,
        "is_published": True,
        "day_number": 1,
    },

    # --- DAY 2 CHALLENGE QUESTIONS (Tomorrow) ---
    {
        "id": "q_pmat_trig_daily_02",
        "title": "Trigonometric Equations & General Solutions",
        "description": "Find all general solutions in radians satisfying cos(3x) + cos(x) = 0.",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_trig",
        "exam_paper_id": "paper_2022_al_combined_p1",
        "content_text": r"""# Trigonometric Equations & General Solutions

Find all real values of $\theta \in [0, 2\pi)$ satisfying the equation:
$$ \cos(3\theta) + \cos(\theta) = 0 $$

1. Express $\cos(3\theta) + \cos(\theta)$ as a product of trigonometric functions.
2. Hence, determine the general solution for $\theta \in \mathbb{R}$.
3. State the exact solutions in the interval $[0, 2\pi)$.
""",
        "solution_text": r"""# Official Marking Scheme (25 Marks)

### Step 1: Sum-to-Product Identity (10 Marks)
Using $\cos A + \cos B = 2\cos\left(\frac{A+B}{2}\right)\cos\left(\frac{A-B}{2}\right)$:
$$ \cos(3\theta) + \cos(\theta) = 2\cos(2\theta)\cos(\theta) = 0 $$

### Step 2: General Solutions (10 Marks)
Either $\cos(2\theta) = 0$ or $\cos(\theta) = 0$:
* $\cos(2\theta) = 0 \implies 2\theta = (2n + 1)\frac{\pi}{2} \implies \theta = (2n + 1)\frac{\pi}{4}, \quad n \in \mathbb{Z}$
* $\cos(\theta) = 0 \implies \theta = (2k + 1)\frac{\pi}{2}, \quad k \in \mathbb{Z}$

### Step 3: Interval $[0, 2\pi)$ (05 Marks)
$$ \theta \in \left\{ \frac{\pi}{4}, \frac{3\pi}{4}, \frac{\pi}{2}, \frac{5\pi}{4}, \frac{7\pi}{4}, \frac{3\pi}{2} \right\} $$
""",
        "solution_id": "11111111-1111-4111-8111-111111111105",
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 10, "description_si": "ගුණිත සූත්‍රය යොදා $2\\cos(2\\theta)\\cos(\\theta) = 0$ ආකෘතියට පත් කිරීම"},
            {"step_number": 2, "step_type": "METHOD", "marks": 10, "description_si": "කාණ්ඩ දෙක සඳහාම සාමාන්‍ය විසඳුම් වෙන් වෙන්ව ලිවීම"},
            {"step_number": 3, "step_type": "FINAL", "marks": 5, "description_si": "$[0, 2\\pi)$ පරාසයේ නිශ්චිත විසඳුම් ලැයිස්තුගත කිරීම"},
        ],
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "DAILY",
        "source": "PAST_PAPER",
        "source_details": "G.C.E. A/L Combined Maths (Part A)",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "day_number": 2,
    },
    {
        "id": "q_amat_newton_daily_02",
        "title": "Connected Particles on an Inclined Plane",
        "description": "Calculate system acceleration and string tension for connected blocks on a rough incline.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_newton",
        "exam_paper_id": "paper_2023_al_combined_p2",
        "content_text": r"""# Connected Particles on an Inclined Plane

A block $A$ of mass $3m$ lies on a rough plane inclined at an angle $\alpha$ to the horizontal, where $\tan\alpha = \frac{3}{4}$. The coefficient of friction between $A$ and the plane is $\mu = \frac{1}{4}$.
A light inextensible string attached to $A$ passes over a smooth pulley at the top of the plane and supports a hanging particle $B$ of mass $2m$.

1. Assuming the system is released from rest with $B$ descending, mark all forces acting on each particle.
2. Find the acceleration $a$ of the system in terms of $g$.
3. Calculate the tension $T$ in the string.
""",
        "solution_text": r"""# Official Marking Scheme (25 Marks)

### Step 1: Equations of Motion (15 Marks)
From $\tan\alpha = 3/4 \implies \sin\alpha = 3/5, \cos\alpha = 4/5$.
* Normal reaction on $A$: $R = 3mg\cos\alpha = 3mg(4/5) = \frac{12}{5}mg$
* Friction: $F = \mu R = \frac{1}{4}\left(\frac{12}{5}mg\right) = \frac{3}{5}mg$

Equations along motion:
* For $B$ (downwards): $2mg - T = 2ma$
* For $A$ (up the incline): $T - 3mg\sin\alpha - F = 3ma \implies T - \frac{9}{5}mg - \frac{3}{5}mg = 3ma \implies T - \frac{12}{5}mg = 3ma$

### Step 2: Solve for Acceleration and Tension (10 Marks)
Adding the two equations:
$$ 2mg - \frac{12}{5}mg = 5ma \implies -\frac{2}{5}mg = 5ma \implies a = -\frac{2}{25}g $$
Since $a < 0$, the assumed downward motion of $B$ does not occur; the system remains in static equilibrium or accelerates downwards along the incline if friction allows.
Limiting equilibrium check: $2mg < 3mg\sin\alpha + \mu R = \frac{12}{5}mg \implies$ The system remains in **equilibrium** ($a = 0, T = 2mg$).
""",
        "solution_id": "11111111-1111-4111-8111-111111111106",
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 10, "description_si": "අභිලම්භ ප්‍රතික්‍රියාව සහ උපරිම සීමාකාරී ඝර්ෂණ බලය ගණනය කිරීම"},
            {"step_number": 2, "step_type": "METHOD", "marks": 10, "description_si": "අංශු දෙක සඳහාම නිව්ටන් දෙවන නියමයෙන් සමීකරණ ගොඩනැගීම"},
            {"step_number": 3, "step_type": "FINAL", "marks": 5, "description_si": "ත්වරණය සෘණ වීමෙන් පද්ධතිය සමතුලිතතාවයේ පවතින බව නිගමනය කිරීම"},
        ],
        "type": "SHORT",
        "difficulty": "HARD",
        "schedule": "DAILY",
        "source": "MODEL_PAPER",
        "source_details": "Ananda College Term Test Paper",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "day_number": 2,
    },

    # --- DAY 3 CHALLENGE QUESTIONS (Day after tomorrow) ---
    {
        "id": "q_pmat_int_daily_03",
        "title": "Integration by Substitution & Definite Integrals",
        "description": "Evaluate the definite integral using standard algebraic substitution.",
        "subject_id": "subj_pmat",
        "lesson_id": "lesson_pmat_int",
        "exam_paper_id": "paper_2022_al_combined_p1",
        "content_text": r"""# Integration by Substitution

Evaluate the definite integral:
$$ I = \int_{0}^{1} \frac{x}{\sqrt{4 - x^2}} \, dx $$

1. Use the substitution $u = 4 - x^2$ to transform the integral.
2. Find the new limits of integration.
3. Compute the exact value of $I$.
""",
        "solution_text": r"""# Official Marking Scheme (25 Marks)

### Step 1: Substitution (10 Marks)
Let $u = 4 - x^2 \implies du = -2x\,dx \implies x\,dx = -\frac{1}{2}du$.

### Step 2: Change Limits (05 Marks)
* When $x = 0 \implies u = 4$
* When $x = 1 \implies u = 3$

### Step 3: Evaluation (10 Marks)
$$ I = \int_{4}^{3} \frac{-\frac{1}{2}du}{\sqrt{u}} = \frac{1}{2} \int_{3}^{4} u^{-1/2} du = \left[ u^{1/2} \right]_{3}^{4} = \sqrt{4} - \sqrt{3} = 2 - \sqrt{3} $$
""",
        "solution_id": "11111111-1111-4111-8111-111111111107",
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 10, "description_si": "$u = 4 - x^2$ ආදේශය යොදා $du$ සම්බන්ධතාවය ලිවීම"},
            {"step_number": 2, "step_type": "METHOD", "marks": 5, "description_si": "නව අනුකලන සීමා $u=4$ සිට $u=3$ දක්වා නිවැරදිව පරිවර්තනය"},
            {"step_number": 3, "step_type": "FINAL", "marks": 10, "description_si": "අනුකලනය කර අවසන් අගය $2 - \\sqrt{3}$ ලෙස ලබා ගැනීම"},
        ],
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "DAILY",
        "source": "PAST_PAPER",
        "source_details": "G.C.E. A/L Combined Maths (Part A)",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "day_number": 3,
    },
    {
        "id": "q_amat_straight_daily_03",
        "title": "Velocity-Time Graph for Train Motion Between Two Stations",
        "description": "Analyze two-stage acceleration and deceleration profile on a straight track.",
        "subject_id": "subj_amat",
        "lesson_id": "lesson_amat_straight_line",
        "exam_paper_id": "paper_2023_al_combined_p2",
        "content_text": r"""# Rectilinear Motion: $(v-t)$ Graph

A train starts from rest at station $A$ and accelerates uniformly at rate $f$ for time $t_1$ until reaching maximum speed $V$.
It then immediately decelerates uniformly at rate $2f$ until coming to rest at station $B$.
The total time taken for the journey is $T$, and the total distance between the stations is $S$.

1. Sketch the velocity-time $(v-t)$ graph for the journey.
2. Show that the maximum speed is $V = \frac{2S}{T}$.
3. Express $T$ in terms of $S$ and $f$.
""",
        "solution_text": r"""# Official Marking Scheme (25 Marks)

### Step 1: Velocity-Time Graph (08 Marks)
Triangular graph with peak $(t_1, V)$ and base $[0, T]$.
* Area under graph = Distance: $\frac{1}{2} V T = S \implies V = \frac{2S}{T}$ (Proven).

### Step 2: Time components in terms of $f$ (10 Marks)
* Acceleration phase: $V = f t_1 \implies t_1 = \frac{V}{f}$
* Deceleration phase: $V = 2f t_2 \implies t_2 = \frac{V}{2f}$
* Total time: $T = t_1 + t_2 = \frac{V}{f} + \frac{V}{2f} = \frac{3V}{2f}$

### Step 3: Eliminate $V$ (07 Marks)
Substitute $V = \frac{2S}{T}$:
$$ T = \frac{3}{2f} \left(\frac{2S}{T}\right) = \frac{3S}{fT} \implies T^2 = \frac{3S}{f} \implies T = \sqrt{\frac{3S}{f}} $$
""",
        "solution_id": "11111111-1111-4111-8111-111111111108",
        "solution_steps": [
            {"step_number": 1, "step_type": "METHOD", "marks": 8, "description_si": "$(v-t)$ ප්‍රස්තාරය ඇඳ වර්ගඵලයෙන් $V = 2S/T$ සාධනය කිරීම"},
            {"step_number": 2, "step_type": "METHOD", "marks": 10, "description_si": "ත්වරණ සහ මන්දන කාල අනුපාතය $f$ ඇසුරින් ලිවීම"},
            {"step_number": 3, "step_type": "FINAL", "marks": 7, "description_si": "$V$ ආදේශ කර මුළු කාලය $T = \\sqrt{3S/f}$ බව පෙන්වීම"},
        ],
        "type": "SHORT",
        "difficulty": "MEDIUM",
        "schedule": "DAILY",
        "source": "MODEL_PAPER",
        "source_details": "Royal College Term Test",
        "allocated_marks": 25,
        "is_premium": False,
        "is_published": True,
        "day_number": 3,
    },
]

DAILY_CHALLENGES_SEED = [
    {
        "id": "dc_day_01",
        "day_number": 1,
        "offset_days": 0,
        "title": "දින 01 - ත්‍රිකෝණමිතිය සහ සරල රේඛීය චලිතය මූලික අභ්‍යාසය",
        "description": "G.C.E. A/L Combined Mathematics දින 01 මූලික ගැටළු කට්ටලය.",
        "target_duration_seconds": 5400,
        "total_marks": 250,
        "question_ids": [
            "q_pmat_poly_daily_01",
            "q_pmat_diff_essay_01",
            "q_amat_circular_short_01",
            "q_amat_relvel_essay_01",
        ],
    },
    {
        "id": "dc_day_02",
        "day_number": 2,
        "offset_days": 1,
        "title": "දින 02 - බහුපද සහ නිව්ටන් නියම අභ්‍යාසය",
        "description": "G.C.E. A/L Combined Mathematics දින 02 විශේෂ ගැටළු කට්ටලය.",
        "target_duration_seconds": 3600,
        "total_marks": 50,
        "question_ids": [
            "q_pmat_trig_daily_02",
            "q_amat_newton_daily_02",
        ],
    },
    {
        "id": "dc_day_03",
        "day_number": 3,
        "offset_days": 2,
        "title": "දින 03 - අනුකලනය සහ චලිත ප්‍රස්තාර අභ්‍යාසය",
        "description": "G.C.E. A/L Combined Mathematics දින 03 ආදර්ශ ගැටළු කට්ටලය.",
        "target_duration_seconds": 3600,
        "total_marks": 50,
        "question_ids": [
            "q_pmat_int_daily_03",
            "q_amat_straight_daily_03",
        ],
    },
]


async def seed_database(session: AsyncSession) -> None:
    """
    Seeds initial reference data if tables are empty or updates existing seeds idempotently.
    Uses modern SQLAlchemy ORM models across all domains.
    """
    # 0. Seed Sri Lankan Administrative Districts (1-25)
    for d in DISTRICTS_SEED:
        existing_d = (
            await session.execute(select(District).where(District.id == d["id"]))
        ).scalar_one_or_none()
        if existing_d:
            existing_d.code = d["code"]
            existing_d.name_en = d["name_en"]
            existing_d.name_si = d["name_si"]
            existing_d.name_ta = d["name_ta"]
            existing_d.province = d["province"]
            existing_d.display_order = d["display_order"]
        else:
            session.add(District(**d))
    await session.commit()

    # 1. Seed Default Admin User & Student Profile
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
        admin.district_id = 1
        admin_uid = admin.uid
    else:
        session.add(
            User(
                uid=DEFAULT_ADMIN_UID,
                email=DEFAULT_ADMIN_EMAIL,
                name=DEFAULT_ADMIN_NAME,
                role="ADMIN",
                district_id=1,
                school_name="Royal College, Colombo",
                stream="PHYSICAL_SCIENCE",
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

    # Seed normalized StudentProfile for Admin if not present
    admin_profile = (
        await session.execute(
            select(StudentProfile).where(StudentProfile.user_id == admin_uid)
        )
    ).scalar_one_or_none()
    if admin_profile:
        admin_profile.exam_year = 2026
        admin_profile.attempt_number = 1
        admin_profile.exam_district_id = 1
        admin_profile.school_name = "Royal College, Colombo"
        admin_profile.stream = "PHYSICAL_SCIENCE"
        admin_profile.medium = "SINHALA"
    else:
        session.add(
            StudentProfile(
                user_id=admin_uid,
                exam_year=2026,
                attempt_number=1,
                exam_district_id=1,
                school_name="Royal College, Colombo",
                stream="PHYSICAL_SCIENCE",
                medium="SINHALA",
            )
        )
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
                plan_id="plan_monthly_pro",
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

    # 3. Seed Lessons & Hierarchical Sub-lessons
    # Pass 1: Insert root units (parent_lesson_id is None)
    # Pass 2: Insert sub-lessons (parent_lesson_id references root unit)
    lesson_id_map: Dict[str, str] = {}
    for l in LESSONS_SEED:
        lesson_id_map[l["id"]] = l["id"]

    for pass_root_only in (True, False):
        for l in LESSONS_SEED:
            is_root = l.get("parent_lesson_id") is None
            if pass_root_only != is_root:
                continue

            resolved_subj_id = subject_id_map.get(l["subject_id"], l["subject_id"])
            parent_id = l.get("parent_lesson_id")

            existing_lesson = (
                await session.execute(select(SyllabusLesson).where(SyllabusLesson.id == l["id"]))
            ).scalar_one_or_none()

            if existing_lesson:
                existing_lesson.subject_id = resolved_subj_id
                existing_lesson.parent_lesson_id = parent_id
                existing_lesson.title = l["title"]
                existing_lesson.sinhala_title = l["sinhala_title"]
                existing_lesson.order_index = l["order_index"]
                existing_lesson.description = l["description"]
            else:
                session.add(
                    SyllabusLesson(
                        id=l["id"],
                        subject_id=resolved_subj_id,
                        parent_lesson_id=parent_id,
                        title=l["title"],
                        sinhala_title=l["sinhala_title"],
                        order_index=l["order_index"],
                        description=l["description"],
                    )
                )
        await session.flush()

    # 4. Seed Exam Papers
    for ep in EXAM_PAPERS_SEED:
        resolved_subj_id = subject_id_map.get(ep["subject_id"], ep["subject_id"])
        existing_paper = (
            await session.execute(select(ExamPaper).where(ExamPaper.id == ep["id"]))
        ).scalar_one_or_none()

        if existing_paper:
            existing_paper.subject_id = resolved_subj_id
            existing_paper.type = ep["type"]
            existing_paper.year = ep["year"]
            existing_paper.part = ep["part"]
            existing_paper.title_si = ep["title_si"]
            existing_paper.title_en = ep.get("title_en")
            existing_paper.source_pdf_url = ep.get("source_pdf_url")
        else:
            session.add(
                ExamPaper(
                    id=ep["id"],
                    subject_id=resolved_subj_id,
                    type=ep["type"],
                    year=ep["year"],
                    part=ep["part"],
                    title_si=ep["title_si"],
                    title_en=ep.get("title_en"),
                    source_pdf_url=ep.get("source_pdf_url"),
                    is_published=True,
                )
            )
    await session.flush()

    # 5. Seed Subscription Plans & Plan Prices (Domain 7)
    now_utc = datetime.datetime.now(ZoneInfo("UTC"))
    for sp in SUBSCRIPTION_PLANS_SEED:
        existing_plan = (
            await session.execute(
                select(SubscriptionPlan).where(
                    (SubscriptionPlan.id == sp["id"]) | (SubscriptionPlan.code == sp["code"])
                )
            )
        ).scalar_one_or_none()

        features_text = (
            "\n".join(sp["features"])
            if isinstance(sp.get("features"), list)
            else (sp.get("features") or "")
        )

        if existing_plan:
            existing_plan.name_si = sp["name_si"]
            existing_plan.name_en = sp.get("name_en")
            existing_plan.interval = sp["interval"]
            existing_plan.duration_days = sp.get("duration_days")
            existing_plan.features_si = features_text
            existing_plan.display_order = sp.get("display_order", 1)
            plan_id = existing_plan.id
        else:
            new_plan = SubscriptionPlan(
                id=sp["id"],
                code=sp["code"],
                name_si=sp["name_si"],
                name_en=sp.get("name_en"),
                interval=sp["interval"],
                duration_days=sp.get("duration_days"),
                features_si=features_text,
                display_order=sp.get("display_order", 1),
                is_active=True,
            )
            session.add(new_plan)
            plan_id = sp["id"]
        await session.flush()

        # Seed or update PlanPrice in minor units (cents)
        price_stmt = select(PlanPrice).where(
            PlanPrice.plan_id == plan_id,
            PlanPrice.is_active.is_(True),
        )
        existing_price = (await session.execute(price_stmt)).scalar_one_or_none()

        if existing_price:
            existing_price.amount_minor = sp["amount_minor"]
            existing_price.currency = "LKR"
        else:
            session.add(
                PlanPrice(
                    id=f"price_{sp['code'].lower()}",
                    plan_id=plan_id,
                    currency="LKR",
                    amount_minor=sp["amount_minor"],
                    valid_from=now_utc,
                    is_active=True,
                )
            )
    await session.flush()

    # 6. Seed Study Notes
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

    # 7. Seed Questions & Marking Schemes with Steps
    today_colombo = datetime.datetime.now(ZoneInfo("Asia/Colombo")).date()

    for q in QUESTIONS_SEED:
        resolved_subj_id = subject_id_map.get(q["subject_id"], q["subject_id"])
        resolved_lesson_id = (
            lesson_id_map.get(q["lesson_id"], q["lesson_id"])
            if q.get("lesson_id")
            else None
        )
        if q.get("day_number"):
            sched_date = _compute_challenge_date(q["day_number"])
        elif q.get("scheduled_date"):
            sched_date = q["scheduled_date"]
        else:
            sched_date = None

        existing_q = (
            await session.execute(select(Question).where(Question.id == q["id"]))
        ).scalar_one_or_none()

        if existing_q:
            existing_q.title = q["title"]
            existing_q.description = q.get("description", "")
            existing_q.subject_id = resolved_subj_id
            existing_q.lesson_id = resolved_lesson_id
            existing_q.exam_paper_id = q.get("exam_paper_id")
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
            existing_q.day_number = q.get("day_number", 1)
        else:
            session.add(
                Question(
                    id=q["id"],
                    title=q["title"],
                    description=q.get("description", ""),
                    subject_id=resolved_subj_id,
                    lesson_id=resolved_lesson_id,
                    exam_paper_id=q.get("exam_paper_id"),
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
                    day_number=q.get("day_number", 1),
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
        await session.flush()

    # 8. Seed Daily Challenges & Junction Questions
    for dc in DAILY_CHALLENGES_SEED:
        dc_sched_date = _compute_challenge_date(dc.get("day_number"))
        existing_dc = (
            await session.execute(
                select(DailyChallenge).where(
                    (DailyChallenge.id == dc["id"]) | (DailyChallenge.day_number == dc["day_number"])
                )
            )
        ).scalar_one_or_none()

        if existing_dc:
            existing_dc.title = dc["title"]
            existing_dc.description = dc.get("description")
            existing_dc.scheduled_date = dc_sched_date
            existing_dc.target_duration_seconds = dc["target_duration_seconds"]
            existing_dc.total_marks = dc["total_marks"]
            challenge_id = existing_dc.id
        else:
            new_dc = DailyChallenge(
                id=dc["id"],
                day_number=dc["day_number"],
                scheduled_date=dc_sched_date,
                title=dc["title"],
                description=dc.get("description"),
                target_duration_seconds=dc["target_duration_seconds"],
                total_marks=dc["total_marks"],
                is_published=True,
            )
            session.add(new_dc)
            challenge_id = dc["id"]
        await session.flush()

        # Link questions to daily challenge junction table
        for q_order, q_id in enumerate(dc["question_ids"], start=1):
            junction_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"dcq_{challenge_id}_{q_id}"))
            existing_junction = (
                await session.execute(
                    select(DailyChallengeQuestion).where(
                        (DailyChallengeQuestion.daily_challenge_id == challenge_id)
                        & (DailyChallengeQuestion.question_id == q_id)
                    )
                )
            ).scalar_one_or_none()

            # Look up question marks and section
            q_info = next((item for item in QUESTIONS_SEED if item["id"] == q_id), None)
            section = q_info["type"] if q_info else "SHORT"
            marks = q_info["allocated_marks"] if q_info else 25

            if existing_junction:
                existing_junction.order_index = q_order
                existing_junction.section = section
                existing_junction.allocated_marks = marks
            else:
                session.add(
                    DailyChallengeQuestion(
                        id=junction_id,
                        daily_challenge_id=challenge_id,
                        question_id=q_id,
                        order_index=q_order,
                        section=section,
                        allocated_marks=marks,
                        is_mandatory=True,
                    )
                )
        await session.flush()

    await session.commit()
    logger.info("Database seeding completed successfully via SQLAlchemy across all domains.")
    try:
        from app.core.cache import questions_cache
        questions_cache.invalidate_prefix("daily_pack")
        questions_cache.invalidate_prefix("daily_series")
        questions_cache.invalidate_prefix("daily_question")
    except Exception as cache_err:
        logger.warning("Failed to invalidate daily cache after seeding: %s", cache_err)


async def run_seed() -> None:
    """Standalone CLI entry point to run seed_database directly."""
    logger.info("Executing standalone database seed runner...")
    from app.core.database import async_session_factory, init_db
    await init_db()
    async with async_session_factory() as session:
        await seed_database(session)
    logger.info("Standalone database seed runner finished successfully.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_seed())

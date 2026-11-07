"""
Comprehensive SQL Injection (SQLi) Security Verification Suite.
Tests 7 distinct SQLi attack vectors & defensive guarantees across the entire FastAPI + SQLAlchemy 2.0 backend:
1. Static AST Codebase Audit: Zero `text()` in repositories, zero dynamic `text(f"...")` anywhere in `app/`.
2. Classic Tautology / Boolean-Based Blind SQLi (`' OR '1'='1`, `' OR 1=1--`, `" OR ""="`).
3. UNION-Based Data Exfiltration SQLi (`' UNION SELECT uid, email, role FROM users--`).
4. Stacked Queries & Destructive DDL/DML Injection (`'; DROP TABLE users; --`, `'; UPDATE user_stats SET xp=999999; --`).
5. Second-Order (Stored) SQL Injection via `POST /api/v1/users/sync` -> `GET /api/v1/leaderboard` & `/users/me`.
6. SQL `LIKE` / `ILIKE` Wildcard Injection (`?search=%`, `?search=____`, `?search=100%`) on Study Notes search.
7. Time-Based / Error-Based Blind SQLi & Zero Internal SQL Error Leakage (`DatabaseOperationError` masking).
"""

import ast
from datetime import date, datetime, timezone
import pathlib
import unittest
from urllib.parse import quote
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import require_admin_or_account_audit
from app.core.cache import curriculum_cache, districts_cache, questions_cache, study_notes_cache
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.admin_audit_log import AdminAuditLog
from app.models.district import District
from app.models.lesson import SyllabusLesson
from app.models.marking_scheme import MarkingScheme
from app.models.question import Question
from app.models.student_profile import StudentProfile
from app.models.study_note import StudyNote
from app.models.subject import Subject
from app.models.user import User
from app.models.user_stats import UserStats


class TestSQLInjectionSecurityVerification(unittest.IsolatedAsyncioTestCase):
    """End-to-end multi-vector SQL Injection verification suite."""

    async def asyncSetUp(self) -> None:
        app.dependency_overrides.clear()
        districts_cache.clear()
        curriculum_cache.clear()
        study_notes_cache.clear()
        questions_cache.clear()

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            # 1. Seed Districts
            session.add_all(
                [
                    District(
                        id=1,
                        code="COLOMBO",
                        name_en="Colombo",
                        name_si="කොළඹ",
                        name_ta="கொழும்பு",
                        province="WESTERN",
                        display_order=1,
                    ),
                    District(
                        id=4,
                        code="KANDY",
                        name_en="Kandy",
                        name_si="මහනුවර",
                        name_ta="கண்டி",
                        province="CENTRAL",
                        display_order=4,
                    ),
                ]
            )

            # 2. Seed Student & Secret Admin User
            session.add_all(
                [
                    User(
                        uid="stu_sqli_1",
                        email="student@mathsdd.lk",
                        name="Kasun Perera",
                        role="USER",
                        district_id=1,
                        grade="GRADE_13",
                    ),
                    User(
                        uid="admin_secret_99",
                        email="superadmin@mathsdd.lk",
                        name="Top Secret Admin",
                        role="ADMIN",
                        telephone_no="ENCRYPTED_SECRET_PHONE",
                    ),
                ]
            )
            session.add(
                StudentProfile(
                    user_id="stu_sqli_1",
                    exam_district_id=1,
                    school_name="Royal College",
                    exam_year=2026,
                    attempt_number=1,
                    medium="SINHALA",
                    stream="PHYSICAL_SCIENCE",
                )
            )
            session.add(
                UserStats(
                    user_id="stu_sqli_1",
                    xp=500,
                    current_streak_days=5,
                    longest_streak_days=10,
                    total_solved_count=25,
                )
            )

            # 3. Seed Curriculum, Published Question, Unpublished Secret Question, and StudyNote
            session.add(
                Subject(
                    id="sub_pmat",
                    name="Pure Mathematics",
                    sinhala_name="ශුද්ධ ගණිතය",
                    code="PMAT",
                    order_index=1,
                    description="Pure Mathematics Syllabus",
                )
            )
            session.add(
                SyllabusLesson(
                    id="les_trig",
                    subject_id="sub_pmat",
                    title="Trigonometry",
                    sinhala_title="ත්‍රිකෝණමිතිය",
                    description="Trigonometry Basics",
                    order_index=1,
                    question_count=1,
                    premium_count=0,
                )
            )
            session.add_all(
                [
                    Question(
                        id="q_pub_1",
                        title="Published Trigonometry Question",
                        subject_id="sub_pmat",
                        lesson_id="les_trig",
                        type="SHORT",
                        difficulty="MEDIUM",
                        schedule="REGULAR",
                        source="PAST_PAPER",
                        allocated_marks=25,
                        is_premium=False,
                        is_published=True,
                        content_text="Find \\sin(\\pi/6)",
                    ),
                    Question(
                        id="q_secret_unpub",
                        title="TOP SECRET UNPUBLISHED EXAM PAPER 2027",
                        subject_id="sub_pmat",
                        lesson_id="les_trig",
                        type="ESSAY",
                        difficulty="HARD",
                        schedule="REGULAR",
                        source="MODEL_PAPER",
                        allocated_marks=100,
                        is_premium=True,
                        is_published=False,
                        content_text="CONFIDENTIAL_FUTURE_EXAM_QUESTION",
                    ),
                ]
            )
            session.add(
                MarkingScheme(
                    id=uuid.uuid4(),
                    question_id="q_pub_1",
                    title="Official Marking Scheme",
                    content_text="Step 1: 1/2",
                    total_marks=25,
                    order_index=1,
                )
            )
            session.add(
                StudyNote(
                    id="note_trig_1",
                    subject_id="sub_pmat",
                    lesson_id="les_trig",
                    title="Trigonometric Identities Note",
                    description="Fundamental identities summary",
                    content_text="$$\\sin^2 x + \\cos^2 x = 1$$",
                    author="Dr. Perera",
                    is_premium=False,
                    order_index=1,
                )
            )
            session.add(
                AdminAuditLog(
                    id="aud_1",
                    actor_uid="admin_secret_99",
                    actor_email="superadmin@mathsdd.lk",
                    actor_role="ADMIN",
                    action="APPROVE_BANK_SLIP",
                    resource_type="SUBSCRIPTION",
                    resource_id="sub_001",
                    ip_address="127.0.0.1",
                    created_at=now,
                )
            )
            await session.commit()

        async def override_get_db():
            async with self.session_factory() as session:
                yield session
                await session.commit()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "stu_sqli_1",
            "email": "student@mathsdd.lk",
            "name": "Kasun Perera",
            "role": "USER",
            "email_verified": True,
        }
        self.client = TestClient(app)

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()
        districts_cache.clear()
        curriculum_cache.clear()
        study_notes_cache.clear()
        questions_cache.clear()
        await self.engine.dispose()

    def test_1_static_ast_zero_dynamic_sql_across_entire_codebase(self) -> None:
        """
        AST-level static verification across every .py file in `app/`:
        - Zero `text()` calls anywhere inside `app/repositories/`.
        - Every `text(...)` call in `app/models/` and `app/core/database.py` uses a compile-time constant string
          (zero f-strings, zero `%` formatting, zero `.format()`, zero `+` concatenation).
        - Zero usage of raw driver escape hatches (`exec_driver_sql`, `raw_connection`, `driver_connection`).
        """
        app_root = pathlib.Path(__file__).resolve().parent.parent / "app"
        forbidden_methods = {"exec_driver_sql", "raw_connection", "driver_connection"}

        for py_file in sorted(app_root.rglob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            is_repository = "repositories" in py_file.parts

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check function name
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    self.assertNotIn(
                        func_name,
                        forbidden_methods,
                        f"Forbidden raw SQL driver method '{func_name}' found in {py_file}:{node.lineno}",
                    )

                    if func_name == "text":
                        self.assertFalse(
                            is_repository,
                            f"Raw SQLAlchemy text() is forbidden in repositories ({py_file}:{node.lineno})",
                        )
                        self.assertEqual(
                            len(node.args),
                            1,
                            f"text() must take exactly 1 static string argument ({py_file}:{node.lineno})",
                        )
                        arg = node.args[0]
                        self.assertIsInstance(
                            arg,
                            ast.Constant,
                            f"text() argument in {py_file}:{node.lineno} MUST be a compile-time constant string, not {type(arg).__name__}!",
                        )

    def test_2_tautology_and_boolean_blind_sqli_blocked_everywhere(self) -> None:
        """
        Tests classic tautology payloads (`' OR '1'='1`, `' OR 1=1--`, `" OR ""="`) across all endpoints.
        Verifies unpublished questions, non-matching filters, and unauthorized rows are NEVER leaked.
        """
        tautologies = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' OR 1=1/*",
            '" OR ""="',
            "sub_pmat' OR is_published=0--",
            "q_pub_1' OR id='q_secret_unpub'--",
        ]

        for payload in tautologies:
            encoded = quote(payload, safe="")

            # 1. Questions list filter injection attempt (trying to dump unpublished q_secret_unpub)
            q_res = self.client.get(
                f"/api/v1/questions?subject_id={encoded}&lesson_id={encoded}&difficulty={encoded}"
            )
            self.assertEqual(q_res.status_code, 200)
            items = q_res.json()["items"]
            self.assertEqual(items, [], f"Tautology payload {payload!r} leaked questions: {items}")

            # 2. Question detail path parameter injection attempt
            detail_res = self.client.get(f"/api/v1/questions/{encoded}")
            self.assertIn(detail_res.status_code, (404, 422))
            self.assertNotIn("CONFIDENTIAL_FUTURE_EXAM_QUESTION", detail_res.text)

            # 3. Study notes filter & search injection attempt
            notes_res = self.client.get(
                f"/api/v1/study-notes?subject_id={encoded}&search={encoded}"
            )
            self.assertEqual(notes_res.status_code, 200)
            self.assertEqual(notes_res.json()["items"], [])

            # 4. Curriculum lessons filter injection attempt
            les_res = self.client.get(
                f"/api/v1/curriculum/lessons?subject_code={encoded}&parent_lesson_id={encoded}"
            )
            self.assertEqual(les_res.status_code, 200)
            self.assertEqual(les_res.json(), [])

            # 5. Leaderboard district_id injection attempt
            lb_res = self.client.get(f"/api/v1/leaderboard?district_id={encoded}")
            self.assertEqual(lb_res.status_code, 400)
            self.assertNotIn("ENCRYPTED_SECRET_PHONE", lb_res.text)

    def test_3_union_based_data_exfiltration_sqli_blocked(self) -> None:
        """
        Tests UNION SELECT payloads attempting to extract `users` or `admin_audit_logs` records
        through catalog, search, and leaderboard endpoints.
        """
        union_payloads = [
            "' UNION SELECT uid, email, role, telephone_no, NULL, NULL, NULL, NULL, NULL FROM users--",
            "PMAT' UNION ALL SELECT uid, email, telephone_no, role, NULL, NULL FROM users--",
            "note_trig_1' UNION SELECT id, actor_email, action, ip_address, NULL, NULL, NULL, NULL, NULL FROM admin_audit_logs--",
        ]

        for payload in union_payloads:
            encoded = quote(payload, safe="")

            for url in (
                f"/api/v1/questions?subject_id={encoded}",
                f"/api/v1/questions/{encoded}",
                f"/api/v1/study-notes?search={encoded}",
                f"/api/v1/study-notes/{encoded}",
                f"/api/v1/curriculum/lessons?subject_code={encoded}",
                f"/api/v1/leaderboard?district_id={encoded}",
            ):
                res = self.client.get(url)
                body_text = res.text
                self.assertNotIn("superadmin@mathsdd.lk", body_text)
                self.assertNotIn("ENCRYPTED_SECRET_PHONE", body_text)
                self.assertNotIn("admin_secret_99", body_text)

    async def test_4_stacked_queries_and_destructive_ddl_dml_injection_blocked(self) -> None:
        """
        Tests stacked query payloads (`'; DROP TABLE users; --`, `'; UPDATE user_stats SET xp=999999; --`,
        `'; DELETE FROM questions; --`) across GET queries and POST bodies, then verifies database integrity.
        """
        stacked_payloads = [
            "'; DROP TABLE users; --",
            "'; DELETE FROM questions; --",
            "'; UPDATE user_stats SET xp = 999999 WHERE user_id = 'stu_sqli_1'; --",
            "'; INSERT INTO admin_audit_logs (id, actor_uid, actor_role, action, target_type) VALUES ('hack', 'stu', 'ADMIN', 'HACK', 'SYSTEM'); --",
        ]

        for payload in stacked_payloads:
            encoded = quote(payload, safe="")
            self.client.get(f"/api/v1/questions?subject_id={encoded}")
            self.client.get(f"/api/v1/study-notes?search={encoded}")
            self.client.post(
                "/api/v1/progress/complete",
                json={
                    "question_id": payload,
                    "time_spent_seconds": 60,
                    "target_duration_seconds": 300,
                    "student_notes": payload,
                },
            )

        # Verify in the database that NO table was dropped, NO question was deleted, and XP is still 500
        async with self.session_factory() as session:
            user_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
            question_count = (await session.execute(select(func.count()).select_from(Question))).scalar_one()
            student_xp = (
                await session.execute(
                    select(UserStats.xp).where(UserStats.user_id == "stu_sqli_1")
                )
            ).scalar_one()

            self.assertEqual(user_count, 2, "Users table must remain intact!")
            self.assertEqual(question_count, 2, "Questions table must remain intact!")
            self.assertEqual(student_xp, 500, "Student XP must NOT be modified by stacked SQLi!")

    def test_5_second_order_stored_sqli_via_profile_sync_and_leaderboard(self) -> None:
        """
        Tests Second-Order SQL Injection:
        1. Stores a malicious SQL payload inside `school_name` and `name` via `POST /api/v1/users/sync`.
        2. Reads the stored data back through `GET /api/v1/users/me` and `GET /api/v1/leaderboard`.
        3. Verifies the payload is treated strictly as inert text and never alters SQL execution.
        """
        second_order_school = "Royal College'; UPDATE user_stats SET xp=999999 WHERE '1'='1; --"
        second_order_name = "Kasun' UNION SELECT email FROM users--"

        sync_res = self.client.post(
            "/api/v1/users/sync",
            json={
                "name": second_order_name,
                "school_name": second_order_school,
                "district_id": 1,
                "exam_district_id": 1,
                "exam_year": 2026,
                "attempt_number": 1,
                "medium": "SINHALA",
                "stream": "PHYSICAL_SCIENCE",
                "grade": "GRADE_13",
            },
        )
        self.assertEqual(sync_res.status_code, 200)
        self.assertEqual(sync_res.json()["school_name"], second_order_school)
        self.assertEqual(sync_res.json()["xp"], 500)

        # Trigger Leaderboard query which selects & orders across User + StudentProfile + UserStats
        lb_res = self.client.get("/api/v1/leaderboard")
        self.assertEqual(lb_res.status_code, 200)
        lb_data = lb_res.json()
        self.assertEqual(len(lb_data["items"]), 1)
        self.assertEqual(lb_data["items"][0]["school_name"], second_order_school)
        self.assertEqual(lb_data["items"][0]["name"], second_order_name)
        self.assertEqual(lb_data["items"][0]["xp"], 500)
        self.assertNotIn("superadmin@mathsdd.lk", lb_res.text)

    def test_6_sql_ilike_wildcard_injection_neutralized(self) -> None:
        """
        Tests SQL LIKE/ILIKE Wildcard Injection (`?search=%`, `?search=____`, `?search=%_%`).
        Verifies that `%` and `_` in user search queries are escaped as literals (`escape='\\'`)
        so `?search=%` does NOT dump all study notes when no note contains a literal `%`.
        """
        for wildcard_payload in ("%", "____", "%_%", "100%", "\\"):
            res = self.client.get(f"/api/v1/study-notes?search={quote(wildcard_payload, safe='')}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(
                res.json()["items"],
                [],
                f"Wildcard search {wildcard_payload!r} should NOT match all rows!",
            )

        # Confirm legitimate substring search still works normally
        legit_res = self.client.get("/api/v1/study-notes?search=Trigonometric")
        self.assertEqual(legit_res.status_code, 200)
        self.assertEqual(len(legit_res.json()["items"]), 1)
        self.assertEqual(legit_res.json()["items"][0]["id"], "note_trig_1")

    def test_7_admin_audit_logs_and_error_masking_against_blind_sqli(self) -> None:
        """
        Tests time-based & error-based blind SQLi payloads on Admin Audit Logs (`/api/v1/admin/security/audit-logs`)
        and verifies zero internal SQL error leakage.
        """
        app.dependency_overrides[require_admin_or_account_audit] = lambda: {
            "uid": "admin_secret_99",
            "email": "superadmin@mathsdd.lk",
            "role": "ADMIN",
        }
        blind_payloads = [
            "' AND (SELECT 1 FROM (SELECT SLEEP(5))a)--",
            "'; SELECT pg_sleep(5); --",
            "' AND 1=CAST((SELECT sqlite_version()) AS INT)--",
        ]
        for payload in blind_payloads:
            encoded = quote(payload, safe="")
            res = self.client.get(
                f"/api/v1/admin/security/audit-logs?actor_uid={encoded}&action={encoded}&resource_type={encoded}"
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["items"], [])
            self.assertEqual(res.json()["pagination"]["total"], 0)

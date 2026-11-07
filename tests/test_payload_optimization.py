"""
Unit & Integration tests verifying response payload optimizations across all student-facing endpoints.
Ensures redundant/server-side fields (`display_order`, `order_index`, `is_published`, `question_ids`,
`completed_date_key`, `description_en`, `exam_district`, `attempt`, `district_name_en`, and heavy nested
`payments`/`bank_slip` audit fields on profile/status endpoints) are stripped from HTTP JSON responses.
"""

from datetime import date, datetime, timezone
import unittest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.cache import curriculum_cache, districts_cache, questions_cache, study_notes_cache
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.district import District
from app.models.lesson import SyllabusLesson
from app.models.marking_scheme import MarkingScheme
from app.models.progress import UserDailyActivity, UserQuestionAttempt, XpTransaction
from app.models.question import Question
from app.models.student_profile import StudentProfile
from app.models.study_note import StudyNote
from app.models.subject import Subject
from app.models.subscription import (
    BankTransferSlip,
    Payment,
    PlanPrice,
    SubscriptionPlan,
    UserSubscription,
)
from app.models.user import User
from app.models.user_stats import UserStats


class TestResponsePayloadOptimization(unittest.IsolatedAsyncioTestCase):
    """End-to-end verification that all response payloads exclude server-only and duplicate fields."""

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
        today = date.today()
        today_key = today.isoformat()
        ms_uuid = uuid.uuid4()

        async with self.session_factory() as session:
            # 1. Seed District
            session.add(
                District(
                    id=1,
                    code="COLOMBO",
                    name_en="Colombo",
                    name_si="කොළඹ",
                    name_ta="கொழும்பு",
                    province="WESTERN",
                    display_order=1,
                )
            )

            # 2. Seed User, StudentProfile, UserStats
            session.add(
                User(
                    uid="stu_opt_1",
                    email="opt@mathsdd.lk",
                    name="Optimization Tester",
                    role="USER",
                    district_id=1,
                    grade="GRADE_13",
                )
            )
            session.add(
                StudentProfile(
                    user_id="stu_opt_1",
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
                    user_id="stu_opt_1",
                    xp=500,
                    current_streak_days=5,
                    longest_streak_days=10,
                    total_solved_count=25,
                )
            )

            # 3. Seed Subscription Plan, PlanPrice, Active Subscription, Payment, BankTransferSlip
            session.add(
                SubscriptionPlan(
                    id="COMBINED_PRO_MONTHLY",
                    code="COMBINED_PRO_MONTHLY",
                    name_en="Combined Maths Pro Monthly",
                    name_si="සංයුක්ත ගණිතය මාසික",
                    description_si="සියලුම පාඩම් සඳහා ප්‍රවේශය",
                    interval="MONTH",
                    duration_days=30,
                    features_si="සියලුම ප්‍රශ්න",
                    is_active=True,
                    display_order=1,
                )
            )
            session.add(
                PlanPrice(
                    id="prc_opt_1",
                    plan_id="COMBINED_PRO_MONTHLY",
                    currency="LKR",
                    amount_minor=150000,
                    is_active=True,
                )
            )
            session.add(
                UserSubscription(
                    id="sub_opt_1",
                    user_id="stu_opt_1",
                    plan_id="COMBINED_PRO_MONTHLY",
                    status="ACTIVE",
                    provider="BANK_TRANSFER",
                    starts_at=now,
                    expires_at=None,
                )
            )
            session.add(
                Payment(
                    id="pay_opt_1",
                    subscription_id="sub_opt_1",
                    user_id="stu_opt_1",
                    amount_minor=150000,
                    currency="LKR",
                    status="COMPLETED",
                    method="BANK_TRANSFER",
                )
            )
            session.add(
                BankTransferSlip(
                    payment_id="pay_opt_1",
                    slip_image_url="https://cdn.mathsdd.lk/slips/slip1.jpg",
                    deposit_reference="BOC-12345",
                    admin_feedback="Verified",
                    review_status="APPROVED",
                    reviewed_by="admin_1",
                    reviewed_at=now,
                )
            )

            # 4. Seed Curriculum (Subject, SyllabusLesson, Question, MarkingScheme, StudyNote)
            session.add(
                Subject(
                    id="sub_pmat",
                    name="Pure Mathematics",
                    sinhala_name="ශුද්ධ ගණිතය",
                    code="PMAT",
                    order_index=1,
                    description="ශුද්ධ ගණිතය පාඩම් මාලාව",
                )
            )
            session.add(
                SyllabusLesson(
                    id="les_trig",
                    subject_id="sub_pmat",
                    title="Trigonometry",
                    sinhala_title="ත්‍රිකෝණමිතිය",
                    description="ත්‍රිකෝණමිතිය මූලිකාංග",
                    order_index=1,
                    question_count=1,
                    premium_count=0,
                )
            )
            session.add(
                Question(
                    id="q_trig_1",
                    title="2023 A/L Combined Mathematics Paper I - Q1",
                    subject_id="sub_pmat",
                    lesson_id="les_trig",
                    type="SHORT",
                    source="PAST_PAPER",
                    allocated_marks=25,
                    is_premium=False,
                    is_published=True,
                    content_text="\\sin(A+B) = \\sin A \\cos B + \\cos A \\sin B",
                )
            )
            session.add(
                MarkingScheme(
                    id=ms_uuid,
                    question_id="q_trig_1",
                    title="Official Marking Scheme",
                    content_text="$$\\sin(A+B) = \\sin A \\cos B + \\cos A \\sin B$$",
                    pdf_url="https://cdn.mathsdd.lk/solutions/q_trig_1_solution.pdf",
                    total_marks=25,
                    order_index=1,
                )
            )
            session.add(
                StudyNote(
                    id="note_trig_1",
                    subject_id="sub_pmat",
                    lesson_id="les_trig",
                    title="Trigonometric Identities",
                    description="මූලික සූත්‍ර සාරාංශය",
                    content_text="$$\\sin^2 x + \\cos^2 x = 1$$",
                    is_premium=False,
                    order_index=1,
                )
            )

            # 5. Seed Progress (UserDailyActivity, UserQuestionAttempt, XpTransaction)
            session.add(
                UserDailyActivity(
                    id=f"stu_opt_1_{today_key}",
                    user_id="stu_opt_1",
                    date_key=today_key,
                    questions_solved_count=2,
                    total_time_spent_seconds=300,
                    daily_challenge_completed=True,
                )
            )
            session.add(
                UserQuestionAttempt(
                    id="stu_opt_1_q_trig_1",
                    user_id="stu_opt_1",
                    question_id="q_trig_1",
                    time_spent_seconds=300,
                    last_attempt_duration_seconds=300,
                    target_duration_seconds=300,
                    attempt_count=1,
                    completed_date=today,
                    completed_at=now,
                )
            )
            session.add(
                XpTransaction(
                    id="xpt_opt_1",
                    user_id="stu_opt_1",
                    amount=20,
                    reason="QUESTION_SOLVED",
                    question_id="q_trig_1",
                    description_si="q_trig_1 ප්‍රශ්නය විසඳීම වෙනුවෙන්",
                    description_en="Solved Short Question (+20 XP)",
                    created_at=now,
                )
            )
            await session.commit()

        async def override_get_db():
            async with self.session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "stu_opt_1",
            "email": "opt@mathsdd.lk",
            "name": "Optimization Tester",
            "role": "USER",
        }
        self.client = TestClient(app)

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()
        districts_cache.clear()
        curriculum_cache.clear()
        study_notes_cache.clear()
        questions_cache.clear()
        await self.engine.dispose()

    def test_districts_payload_excludes_display_order(self) -> None:
        res = self.client.get("/api/v1/districts")
        self.assertEqual(res.status_code, 200)
        districts = res.json()
        self.assertEqual(len(districts), 1)
        self.assertNotIn("display_order", districts[0])
        self.assertEqual(districts[0]["code"], "COLOMBO")

    def test_user_profile_excludes_duplicate_and_heavy_subscription_fields(self) -> None:
        res = self.client.get("/api/v1/users/me")
        self.assertEqual(res.status_code, 200)
        profile = res.json()
        self.assertNotIn("district_id", profile)
        self.assertNotIn("exam_district_id", profile)
        self.assertNotIn("exam_district", profile)
        self.assertNotIn("attempt", profile)
        self.assertNotIn("streak_count", profile)
        self.assertNotIn("questions_solved", profile)
        self.assertEqual(profile["current_streak_days"], 5)
        self.assertEqual(profile["total_solved_count"], 25)
        self.assertEqual(profile["district"]["id"], 1)
        self.assertEqual(profile["district"]["code"], "COLOMBO")
        self.assertNotIn("display_order", profile["district"])
        # Active subscription on /users/me uses lightweight ActiveSubscriptionSummaryResponse
        active_sub = profile["active_subscription"]
        self.assertIsNotNone(active_sub)
        self.assertEqual(active_sub["id"], "sub_opt_1")
        self.assertNotIn("payments", active_sub)
        self.assertNotIn("slip_image_url", active_sub)
        self.assertNotIn("reference_note", active_sub)
        self.assertNotIn("admin_notes", active_sub)
        self.assertNotIn("amount_minor", active_sub)

    def test_subscriptions_plans_status_and_history_payloads(self) -> None:
        # 1. Plans exclude display_order and amount_minor (exposing only amount_lkr)
        plans_res = self.client.get("/api/v1/subscriptions/plans")
        self.assertEqual(plans_res.status_code, 200)
        plan = plans_res.json()[0]
        self.assertNotIn("display_order", plan)
        self.assertNotIn("amount_minor", plan["prices"][0])
        self.assertEqual(plan["prices"][0]["amount_lkr"], 1500.0)

        # 2. Status uses lightweight ActiveSubscriptionSummaryResponse without top-level duplicate fields
        status_res = self.client.get("/api/v1/subscriptions/status")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertNotIn("plan_id", status_data)
        self.assertNotIn("provider", status_data)
        self.assertNotIn("expires_at", status_data)
        active_sub = status_data["active_subscription"]
        self.assertEqual(active_sub["plan_id"], "COMBINED_PRO_MONTHLY")
        self.assertEqual(active_sub["provider"], "BANK_TRANSFER")
        self.assertNotIn("payments", active_sub)
        self.assertNotIn("slip_image_url", active_sub)

        # 3. History includes payments + bank_slip without parent ID or amount_minor duplication
        hist_res = self.client.get("/api/v1/subscriptions/history")
        self.assertEqual(hist_res.status_code, 200)
        sub_item = hist_res.json()[0]
        self.assertNotIn("slip_image_url", sub_item)
        self.assertNotIn("amount_minor", sub_item)
        self.assertNotIn("amount_lkr", sub_item)
        payment = sub_item["payments"][0]
        self.assertNotIn("subscription_id", payment)
        self.assertNotIn("amount_minor", payment)
        self.assertEqual(payment["amount_lkr"], 1500.0)
        self.assertNotIn("payment_id", payment["bank_slip"])
        self.assertEqual(payment["bank_slip"]["deposit_reference"], "BOC-12345")

    def test_curriculum_questions_and_notes_exclude_order_index_and_is_published(self) -> None:
        subj_res = self.client.get("/api/v1/curriculum/subjects")
        self.assertEqual(subj_res.status_code, 200)
        self.assertNotIn("order_index", subj_res.json()[0])

        les_res = self.client.get("/api/v1/curriculum/lessons")
        self.assertEqual(les_res.status_code, 200)
        lesson_item = les_res.json()[0]
        self.assertNotIn("order_index", lesson_item)
        self.assertNotIn("subject_code", lesson_item)
        self.assertNotIn("subject_name", lesson_item)

        q_list_res = self.client.get("/api/v1/questions")
        self.assertEqual(q_list_res.status_code, 200)
        q_summary = q_list_res.json()["items"][0]
        self.assertNotIn("is_published", q_summary)
        self.assertNotIn("schedule", q_summary)
        self.assertNotIn("difficulty", q_summary)
        self.assertNotIn("subject_name", q_summary)
        self.assertNotIn("lesson_title", q_summary)

        q_detail_res = self.client.get("/api/v1/questions/q_trig_1")
        self.assertEqual(q_detail_res.status_code, 200)
        q_detail = q_detail_res.json()
        self.assertNotIn("is_published", q_detail)
        self.assertNotIn("schedule", q_detail)
        self.assertNotIn("difficulty", q_detail)
        self.assertNotIn("subject_name", q_detail)
        self.assertNotIn("lesson_title", q_detail)
        self.assertIsNone(q_detail["content_url"])

        ms_res = self.client.get("/api/v1/questions/q_trig_1/solution")
        self.assertEqual(ms_res.status_code, 200)
        ms_data = ms_res.json()
        self.assertNotIn("order_index", ms_data)
        self.assertNotIn("steps", ms_data)
        self.assertNotIn("description_si", ms_data)
        self.assertEqual(ms_data["content_type"], "pdf")
        self.assertIsNone(ms_data["content_text"])
        self.assertIn("q_trig_1_solution.pdf", ms_data["pdf_url"])

        notes_res = self.client.get("/api/v1/study-notes")
        self.assertEqual(notes_res.status_code, 200)
        note_item = notes_res.json()["items"][0]
        self.assertNotIn("order_index", note_item)
        self.assertNotIn("subject_name", note_item)
        self.assertNotIn("lesson_title", note_item)

    def test_progress_heatmap_and_xp_history_exclude_redundant_fields(self) -> None:
        prog_res = self.client.get("/api/v1/progress/summary")
        self.assertEqual(prog_res.status_code, 200)
        prog_data = prog_res.json()
        # Find active day in heatmap
        active_days = [
            d for d in prog_data["daily_activity"].values() if d["questions_solved_count"] > 0
        ]
        self.assertEqual(len(active_days), 1)
        self.assertNotIn("question_ids", active_days[0])
        self.assertNotIn("date_key", active_days[0])

        comp_items = list(prog_data["completed_questions"].values())
        self.assertEqual(len(comp_items), 1)
        self.assertNotIn("completed_date_key", comp_items[0])
        self.assertNotIn("question_id", comp_items[0])
        self.assertNotIn("title", comp_items[0])
        self.assertNotIn("subject", comp_items[0])
        self.assertNotIn("lesson_id", comp_items[0])
        self.assertNotIn("question_type", comp_items[0])

        xp_res = self.client.get("/api/v1/progress/xp-history")
        self.assertEqual(xp_res.status_code, 200)
        tx = xp_res.json()["transactions"][0]
        self.assertNotIn("id", tx)
        self.assertNotIn("question_id", tx)
        self.assertNotIn("description_si", tx)
        self.assertEqual(tx["description_en"], "Solved Short Question (+20 XP)")
        self.assertEqual(tx["amount"], 20)
        self.assertEqual(tx["reason"], "QUESTION_SOLVED")

    def test_leaderboard_excludes_redundant_district_fields(self) -> None:
        lb_res = self.client.get("/api/v1/leaderboard")
        self.assertEqual(lb_res.status_code, 200)
        lb_data = lb_res.json()
        entry = lb_data["items"][0]
        self.assertNotIn("user_id", entry)
        self.assertNotIn("uid", entry)
        self.assertNotIn("district_id", entry)
        self.assertNotIn("district_code", entry)
        self.assertNotIn("district_name_si", entry)
        self.assertEqual(entry["district_name_en"], "Colombo")
        my_rank = lb_data["my_rank"]
        self.assertNotIn("user_id", my_rank)
        self.assertNotIn("uid", my_rank)
        self.assertNotIn("district_name_en", my_rank)
        self.assertNotIn("district_name_si", my_rank)
        self.assertNotIn("district_code", my_rank)
        self.assertNotIn("district_id", my_rank)
        self.assertNotIn("name", my_rank)
        self.assertNotIn("avatar_url", my_rank)
        self.assertNotIn("school_name", my_rank)
        self.assertNotIn("exam_year", my_rank)

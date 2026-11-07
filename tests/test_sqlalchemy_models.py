"""
Unit tests for modern SQLAlchemy 2.0 ORM models and clean Pydantic serialization.
Verifies model properties, constraints, relationships, and DTO validations across all academic domains.
"""

import datetime
from zoneinfo import ZoneInfo
import unittest

from app.models import (
    Subject,
    SyllabusLesson,
    Question,
    MarkingScheme,
    StudyNote,
    ExamPaper,
    District,
    User,
    StudentProfile,
    UserStats,
    UserSubscription,
    ProcessedWebhookEvent,
)
from app.schemas.curriculum import SubjectResponse, LessonResponse
from app.schemas.question import (
    ExamPaperResponse,
    MarkingSchemeResponse,
    QuestionDetailResponse,
)
from app.schemas.study_note import StudyNoteDetailResponse
from app.schemas.user import DistrictResponse, UserDistrictSummary, UserProfileResponse
from app.schemas.subscription import UserSubscriptionResponse


class TestSqlAlchemyModels(unittest.TestCase):
    def test_subject_model_serialization(self) -> None:
        subject = Subject(
            id="subj_pmat",
            name="Pure Mathematics",
            sinhala_name="ශුද්ධ ගණිතය",
            code="PMAT",
            order_index=1,
            description="Pure Maths Syllabus",
        )
        self.assertEqual(subject.id, "subj_pmat")
        self.assertEqual(subject.name, "Pure Mathematics")
        self.assertEqual(subject.sinhala_name, "ශුද්ධ ගණිතය")
        self.assertEqual(subject.code, "PMAT")
        self.assertEqual(subject.order_index, 1)
        self.assertIn("Subject", repr(subject))

        dto = SubjectResponse.model_validate(subject, from_attributes=True)
        self.assertEqual(dto.id, "subj_pmat")
        self.assertEqual(dto.name, "Pure Mathematics")
        self.assertEqual(dto.code, "PMAT")

    def test_syllabus_lesson_model_serialization(self) -> None:
        lesson = SyllabusLesson(
            id="lesson_001",
            subject_id="subj_pmat",
            title="Real Numbers",
            sinhala_title="තාත්වික සංඛ්‍යා",
            order_index=1,
            description="Basics of real numbers",
            question_count=10,
            premium_count=3,
        )
        self.assertEqual(lesson.id, "lesson_001")
        self.assertEqual(lesson.subject_id, "subj_pmat")
        self.assertEqual(lesson.title, "Real Numbers")
        self.assertEqual(lesson.question_count, 10)
        self.assertEqual(lesson.premium_count, 3)
        self.assertIn("SyllabusLesson", repr(lesson))

        dto = LessonResponse.model_validate(lesson, from_attributes=True)
        self.assertEqual(dto.id, "lesson_001")
        self.assertEqual(dto.subject_id, "subj_pmat")
        self.assertEqual(dto.title, "Real Numbers")
        self.assertIsNone(dto.parent_lesson_id)

    def test_syllabus_sub_lesson_hierarchy_serialization(self) -> None:
        """Verifies hierarchical sub-lesson model attributes and DTO serialization."""
        sub_lesson = SyllabusLesson(
            id="les_trig_01",
            subject_id="subj_pmat",
            parent_lesson_id="les_trig",
            title="Trigonometric Ratios",
            sinhala_title="ත්‍රිකෝණමිතික අනුපාත",
            order_index=1,
            description="Subtopic 1",
        )
        self.assertEqual(sub_lesson.parent_lesson_id, "les_trig")
        self.assertIn("parent='les_trig'", repr(sub_lesson))

        dto = LessonResponse.model_validate(sub_lesson, from_attributes=True)
        self.assertEqual(dto.id, "les_trig_01")
        self.assertEqual(dto.parent_lesson_id, "les_trig")
        self.assertEqual(dto.sinhala_title, "ත්‍රිකෝණමිතික අනුපාත")

    def test_question_model_serialization(self) -> None:
        today = datetime.date(2026, 10, 29)
        question = Question(
            id="q_100",
            title="Integrate x^2",
            description="Standard calculus problem",
            subject_id="subj_pmat",
            lesson_id="lesson_001",
            exam_paper_id="paper_2023_01",
            content_text=r"Evaluate $\int x^2 dx$",
            content_url="https://example.com/q.pdf",
            type="SHORT",
            source="PAST_PAPER",
            scheduled_date=today,
            is_premium=False,
            is_published=True,
            allocated_marks=25,
        )
        self.assertEqual(question.id, "q_100")
        self.assertEqual(question.title, "Integrate x^2")
        self.assertEqual(question.exam_paper_id, "paper_2023_01")
        self.assertFalse(question.is_premium)
        self.assertFalse(question.is_deleted)
        self.assertEqual(question.allocated_marks, 25)
        self.assertIn("Question", repr(question))

        dto = QuestionDetailResponse.model_validate(question, from_attributes=True)
        self.assertEqual(dto.id, "q_100")
        self.assertEqual(dto.title, "Integrate x^2")
        self.assertEqual(dto.exam_paper_id, "paper_2023_01")
        self.assertEqual(dto.content_type, "pdf")
        self.assertFalse(dto.is_premium)

        # Verify image and markdown content_type resolution on Question
        q_image = Question(
            id="q_101",
            title="Diagram Question",
            subject_id="subj_pmat",
            content_url="https://example.com/diagram.png",
            type="SHORT",
            source="PAST_PAPER",
            allocated_marks=25,
            is_premium=False,
        )
        self.assertEqual(
            QuestionDetailResponse.model_validate(q_image, from_attributes=True).content_type,
            "image",
        )
        q_md = Question(
            id="q_102",
            title="Markdown Question",
            subject_id="subj_pmat",
            content_text=r"$$\sin^2 x + \cos^2 x = 1$$",
            type="SHORT",
            source="PAST_PAPER",
            allocated_marks=25,
            is_premium=False,
        )
        self.assertEqual(
            QuestionDetailResponse.model_validate(q_md, from_attributes=True).content_type,
            "markdown",
        )

    def test_exam_paper_model_and_dto(self) -> None:
        """Verify ExamPaper model and DTO serialization."""
        paper = ExamPaper(
            id="paper_2023_01",
            subject_id="subj_pmat",
            type="AL_GOVT",
            year=2023,
            part="PART_I",
            title_si="2023 අ.පො.ස. උසස් පෙළ සංයුක්ත ගණිතය I",
            title_en="2023 G.C.E. A/L Combined Mathematics I",
            source_pdf_url="https://storage.googleapis.com/papers/2023_al_pmat_1.pdf",
            is_published=True,
        )
        self.assertEqual(paper.id, "paper_2023_01")
        self.assertEqual(paper.year, 2023)
        self.assertEqual(paper.part, "PART_I")
        self.assertIn("ExamPaper", repr(paper))

        dto = ExamPaperResponse.model_validate(paper, from_attributes=True)
        self.assertEqual(dto.id, "paper_2023_01")
        self.assertEqual(dto.year, 2023)
        self.assertEqual(dto.title_si, "2023 අ.පො.ස. උසස් පෙළ සංයුක්ත ගණිතය I")

    def test_marking_scheme_model_serialization_markdown_and_pdf(self) -> None:
        """Verify MarkingScheme supports both Markdown+LaTeX and PDF without a steps table."""
        from app.core.database import Base

        self.assertNotIn("marking_scheme_steps", Base.metadata.tables)

        scheme_pdf = MarkingScheme(
            id="scheme_01",
            question_id="q_100",
            title="Official Marking Scheme",
            total_marks=25,
            content_text=r"Use power rule $\int x^n dx = \frac{x^{n+1}}{n+1} + C$",
            pdf_url="https://example.com/ms.pdf",
            is_official=True,
            is_premium_only=False,
            order_index=1,
        )
        self.assertEqual(scheme_pdf.id, "scheme_01")
        self.assertIn("MarkingScheme", repr(scheme_pdf))

        dto_pdf = MarkingSchemeResponse.model_validate(scheme_pdf, from_attributes=True)
        self.assertEqual(dto_pdf.id, "scheme_01")
        self.assertEqual(dto_pdf.total_marks, 25)
        self.assertEqual(dto_pdf.content_type, "pdf")
        self.assertEqual(dto_pdf.pdf_url, "https://example.com/ms.pdf")
        self.assertNotIn("steps", dto_pdf.model_dump())

        scheme_md = MarkingScheme(
            id="scheme_02",
            question_id="q_100",
            title="Worked Solution",
            total_marks=25,
            content_text=r"$$\int x^2 dx = \frac{x^3}{3} + C$$",
            pdf_url=None,
            is_official=True,
            is_premium_only=False,
            order_index=1,
        )
        dto_md = MarkingSchemeResponse.model_validate(scheme_md, from_attributes=True)
        self.assertEqual(dto_md.content_type, "markdown")
        self.assertIsNone(dto_md.pdf_url)

    def test_study_note_model_serialization(self) -> None:
        note = StudyNote(
            id="note_001",
            title="Calculus Summary",
            description="Integration and differentiation rules",
            subject_id="subj_pmat",
            lesson_id="lesson_001",
            content_text="# Calculus Rules",
            pdf_url="https://example.com/note.pdf",
            is_premium=True,
            order_index=1,
            author="Maths DD Editorial",
        )
        self.assertEqual(note.id, "note_001")
        self.assertEqual(note.title, "Calculus Summary")
        self.assertTrue(note.is_premium)
        self.assertFalse(note.is_deleted)
        self.assertEqual(note.author, "Maths DD Editorial")
        self.assertIn("StudyNote", repr(note))

        dto = StudyNoteDetailResponse.model_validate(note, from_attributes=True)
        self.assertEqual(dto.id, "note_001")
        self.assertEqual(dto.title, "Calculus Summary")
        self.assertTrue(dto.is_premium)

    def test_user_and_user_stats_model_serialization(self) -> None:
        district = District(
            id=1,
            code="COLOMBO",
            name_en="Colombo",
            name_si="කොළඹ",
            name_ta="கொழும்பு",
            province="WESTERN",
            display_order=1,
        )
        user = User(
            uid="usr_007",
            email="student@mathsdd.lk",
            name="Kasun Perera",
            role="USER",
            school_name="Ananda College",
            district_id=1,
            stream="PHYSICAL_SCIENCE",
            grade="GRADE_13",
            attempt="FIRST",
        )
        user.district = district
        stats = UserStats(
            user_id="usr_007",
            xp=150,
            current_streak_days=5,
            longest_streak_days=10,
            total_solved_count=20,
            total_study_time_seconds=600,
        )
        user.stats = stats

        self.assertEqual(user.uid, "usr_007")
        self.assertEqual(user.email, "student@mathsdd.lk")
        self.assertEqual(user.role, "USER")
        self.assertEqual(user.school_name, "Ananda College")
        self.assertEqual(user.district_id, 1)
        self.assertEqual(user.district.code, "COLOMBO")
        self.assertEqual(user.district.name_en, "Colombo")
        self.assertEqual(user.district.name_si, "කොළඹ")
        self.assertEqual(user.district.province, "WESTERN")
        self.assertFalse(user.is_premium)
        self.assertIsNone(user.active_subscription)
        self.assertIn("User", repr(user))
        self.assertIn("UserStats", repr(stats))
        self.assertIn("District", repr(district))

        profile = StudentProfile(
            user_id="usr_007",
            exam_year=2026,
            attempt_number=1,
            exam_district_id=1,
            school_name="Ananda College",
            stream="PHYSICAL_SCIENCE",
            medium="SINHALA",
        )
        user.student_profile = profile

        self.assertEqual(user.exam_year, 2026)
        self.assertEqual(user.attempt_number, 1)
        self.assertEqual(user.exam_district_id, 1)
        self.assertIn("StudentProfile", repr(profile))

        dto = UserProfileResponse(
            uid=user.uid,
            email=user.email,
            name=user.name,
            role=user.role,
            school_name=user.school_name,
            district=UserDistrictSummary.model_validate(district, from_attributes=True),
            exam_year=user.exam_year,
            attempt_number=user.attempt_number,
            medium="SINHALA",
            stream=user.stream,
            grade=user.grade,
            xp=stats.xp,
            streak_count=stats.current_streak_days,
            questions_solved=stats.total_solved_count,
            is_premium=user.is_premium,
        )
        self.assertEqual(dto.uid, "usr_007")
        self.assertEqual(dto.email, "student@mathsdd.lk")
        self.assertIsNotNone(dto.district)
        self.assertEqual(dto.district.id, 1)
        self.assertEqual(dto.district.code, "COLOMBO")
        self.assertEqual(dto.district.name_en, "Colombo")
        district_dump = dto.district.model_dump()
        self.assertNotIn("name_si", district_dump)
        self.assertNotIn("name_ta", district_dump)
        self.assertNotIn("province", district_dump)
        self.assertNotIn("district_id", dto.model_dump())
        self.assertNotIn("exam_district_id", dto.model_dump())
        self.assertEqual(dto.exam_year, 2026)
        self.assertEqual(dto.attempt_number, 1)
        self.assertEqual(dto.xp, 150)
        self.assertEqual(dto.current_streak_days, 5)
        self.assertEqual(dto.total_solved_count, 20)
        self.assertFalse(dto.is_premium)

    def test_user_subscription_lifecycle_and_entitlements(self) -> None:
        now = datetime.datetime.now(ZoneInfo("UTC"))
        user = User(
            uid="usr_008",
            email="vip@mathsdd.lk",
            name="Nimal Silva",
            role="USER",
        )
        self.assertFalse(user.is_premium)

        # 1. Bank transfer pending approval -> is_premium should still be False
        pending_sub = UserSubscription(
            id="sub_bank_01",
            user_id="usr_008",
            plan_id="COMBINED_PRO_MONTHLY",
            status="PENDING_APPROVAL",
            provider="BANK_TRANSFER",
            amount_lkr=2500.0,
            slip_image_url="https://storage.googleapis.com/mathsdd-slips/slip1.jpg",
            reference_note="CDM Bambalapitiya #1234",
            starts_at=now,
            expires_at=None,
        )
        user.subscriptions = [pending_sub]
        self.assertFalse(user.is_premium)
        self.assertIsNone(user.active_subscription)

        # 2. Approved active subscription -> is_premium should become True
        active_sub = UserSubscription(
            id="sub_rc_01",
            user_id="usr_008",
            plan_id="COMBINED_PRO_MONTHLY",
            status="ACTIVE",
            provider="REVENUECAT",
            original_transaction_id="GPA.1234-5678-9012",
            starts_at=now,
            expires_at=now + datetime.timedelta(days=30),
            is_auto_renew=True,
        )
        user.subscriptions = [active_sub, pending_sub]
        self.assertTrue(user.is_premium)
        self.assertIsNotNone(user.active_subscription)
        self.assertEqual(user.active_subscription.id, "sub_rc_01")

        # Validate DTO serialization
        sub_dto = UserSubscriptionResponse.model_validate(active_sub, from_attributes=True)
        self.assertEqual(sub_dto.id, "sub_rc_01")
        self.assertEqual(sub_dto.plan_id, "COMBINED_PRO_MONTHLY")
        self.assertEqual(sub_dto.status, "ACTIVE")
        self.assertEqual(sub_dto.provider, "REVENUECAT")

        # Processed webhook idempotency event
        evt = ProcessedWebhookEvent(
            event_id="evt_01HABCXYZ",
            event_type="INITIAL_PURCHASE",
            app_user_id="usr_008",
        )
        self.assertEqual(evt.event_id, "evt_01HABCXYZ")
        self.assertIn("ProcessedWebhookEvent", repr(evt))

    def test_all_seed_ids_and_model_defaults_are_valid_uuids(self) -> None:
        """Verify all seeded entity IDs, foreign keys, and ORM default primary keys are RFC-4122 UUIDs."""
        import uuid
        from app.core.seed import (
            DAILY_CHALLENGES_SEED,
            EXAM_PAPERS_SEED,
            LESSONS_SEED,
            QUESTIONS_SEED,
            STUDY_NOTES_SEED,
            SUBJECTS_SEED,
            SUBSCRIPTION_PLANS_SEED,
        )
        from app.models.progress import UserDailyActivity, UserQuestionAttempt
        from app.models.study_note import StudyNoteBookmark, StudyNoteVote

        def _assert_valid_uuid(val: str, label: str) -> None:
            parsed = uuid.UUID(str(val))
            self.assertEqual(str(parsed), str(val), f"{label} is not a canonical UUID: {val}")

        for s in SUBJECTS_SEED:
            _assert_valid_uuid(s["id"], "Subject.id")

        for l in LESSONS_SEED:
            _assert_valid_uuid(l["id"], "SyllabusLesson.id")
            _assert_valid_uuid(l["subject_id"], "SyllabusLesson.subject_id")
            if l.get("parent_lesson_id"):
                _assert_valid_uuid(l["parent_lesson_id"], "SyllabusLesson.parent_lesson_id")

        for ep in EXAM_PAPERS_SEED:
            _assert_valid_uuid(ep["id"], "ExamPaper.id")
            _assert_valid_uuid(ep["subject_id"], "ExamPaper.subject_id")

        for sp in SUBSCRIPTION_PLANS_SEED:
            _assert_valid_uuid(sp["id"], "SubscriptionPlan.id")

        for n in STUDY_NOTES_SEED:
            _assert_valid_uuid(n["id"], "StudyNote.id")
            _assert_valid_uuid(n["subject_id"], "StudyNote.subject_id")
            if n.get("lesson_id"):
                _assert_valid_uuid(n["lesson_id"], "StudyNote.lesson_id")

        for q in QUESTIONS_SEED:
            _assert_valid_uuid(q["id"], "Question.id")
            _assert_valid_uuid(q["subject_id"], "Question.subject_id")
            if q.get("lesson_id"):
                _assert_valid_uuid(q["lesson_id"], "Question.lesson_id")
            if q.get("exam_paper_id"):
                _assert_valid_uuid(q["exam_paper_id"], "Question.exam_paper_id")

        for dc in DAILY_CHALLENGES_SEED:
            _assert_valid_uuid(dc["id"], "DailyChallenge.id")
            for qid in dc["question_ids"]:
                _assert_valid_uuid(qid, "DailyChallenge.question_id")

        # Verify ORM column default callables generate valid UUIDv4 strings
        for model_cls in (
            Subject,
            SyllabusLesson,
            Question,
            StudyNote,
            StudyNoteVote,
            StudyNoteBookmark,
            UserQuestionAttempt,
            UserDailyActivity,
        ):
            default_fn = model_cls.__table__.c.id.default.arg
            generated = default_fn(None)
            _assert_valid_uuid(generated, f"{model_cls.__name__}.id default")


if __name__ == "__main__":
    unittest.main()


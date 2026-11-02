"""
Unit tests for SQLAlchemy 2.0 declarative models and Pydantic DTO validation contracts.
Verifies that models register with Base.metadata and validate cleanly with Pydantic v2 schemas.
"""

import datetime
import unittest
import uuid
from app.core.database import Base
from app.models import MarkingScheme, Question, StudyNote, Subject, SyllabusLesson, User, UserStats
from app.schemas.curriculum import LessonResponse, SubjectResponse
from app.schemas.question import MarkingSchemeResponse, QuestionDetailResponse
from app.schemas.study_note import StudyNoteDetailResponse
from app.schemas.user import UserProfileResponse


class TestSQLAlchemyModels(unittest.TestCase):
    """Verifies that all models register with Base.metadata and serialize accurately via Pydantic DTOs."""

    def test_metadata_tables_registration(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected_tables = {
            "subjects",
            "syllabus_lessons",
            "questions",
            "marking_schemes",
            "study_notes",
            "users",
            "user_stats",
            "user_question_attempts",
            "user_daily_activities",
        }
        self.assertTrue(expected_tables.issubset(table_names))

    def test_subject_model_serialization(self) -> None:
        subject = Subject(
            id="subj_pmat",
            name="Pure Mathematics",
            sinhala_name="ශුද්ධ ගණිතය",
            code="PMAT",
            order_index=1,
            description="Pure Mathematics syllabus",
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

    def test_question_model_serialization(self) -> None:
        today = datetime.date(2026, 10, 29)
        question = Question(
            id="q_100",
            title="Integrate x^2",
            description="Standard calculus problem",
            subject_id="subj_pmat",
            lesson_id="lesson_001",
            content_text="Evaluate $\\int x^2 dx$",
            content_url="https://example.com/q.pdf",
            type="SHORT",
            difficulty="EASY",
            schedule="DAILY",
            source="MODEL_PAPER",
            source_details="2026 Model Paper",
            allocated_marks=25,
            is_premium=False,
            is_published=True,
            scheduled_date=today,
        )
        self.assertEqual(question.id, "q_100")
        self.assertEqual(question.title, "Integrate x^2")
        self.assertEqual(question.allocated_marks, 25)
        self.assertEqual(question.scheduled_date, today)
        self.assertFalse(question.is_premium)
        self.assertTrue(question.is_published)
        self.assertIn("Question", repr(question))

        dto = QuestionDetailResponse.model_validate(question, from_attributes=True)
        self.assertEqual(dto.id, "q_100")
        self.assertEqual(dto.title, "Integrate x^2")
        self.assertEqual(dto.allocated_marks, 25)
        self.assertEqual(dto.scheduled_date, today)

    def test_marking_scheme_model_serialization(self) -> None:
        ms_id = uuid.uuid4()
        scheme = MarkingScheme(
            id=ms_id,
            question_id="q_100",
            title="Official Marking Scheme",
            content_text="Solution: $x^3/3 + C$",
            pdf_url=None,
            total_marks=25,
            is_official=True,
            is_premium_only=False,
            order_index=1,
        )
        self.assertEqual(scheme.id, ms_id)
        self.assertEqual(scheme.question_id, "q_100")
        self.assertEqual(scheme.total_marks, 25)
        self.assertTrue(scheme.is_official)
        self.assertFalse(scheme.is_premium_only)
        self.assertIn("MarkingScheme", repr(scheme))

        dto = MarkingSchemeResponse(
            id=str(scheme.id),
            question_id=scheme.question_id,
            title=scheme.title,
            content_text=scheme.content_text,
            pdf_url=scheme.pdf_url,
            total_marks=scheme.total_marks,
            is_official=scheme.is_official,
            is_premium_only=scheme.is_premium_only,
            order_index=scheme.order_index,
        )
        self.assertEqual(dto.id, str(ms_id))
        self.assertEqual(dto.total_marks, 25)

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
        self.assertEqual(note.author, "Maths DD Editorial")
        self.assertIn("StudyNote", repr(note))

        dto = StudyNoteDetailResponse.model_validate(note, from_attributes=True)
        self.assertEqual(dto.id, "note_001")
        self.assertEqual(dto.title, "Calculus Summary")
        self.assertTrue(dto.is_premium)

    def test_user_and_user_stats_model_serialization(self) -> None:
        user = User(
            uid="usr_007",
            email="student@mathsdd.lk",
            name="Kasun Perera",
            role="USER",
            school_name="Ananda College",
            district="Colombo",
            stream="PHYSICAL_SCIENCE",
            grade="GRADE_13",
            attempt="FIRST",
            is_premium=False,
        )
        stats = UserStats(
            user_id="usr_007",
            xp=150,
            current_streak_days=5,
            longest_streak_days=10,
            total_solved_count=20,
            total_study_time_seconds=600,
            accuracy_rate=95.0,
        )
        user.stats = stats

        self.assertEqual(user.uid, "usr_007")
        self.assertEqual(user.email, "student@mathsdd.lk")
        self.assertEqual(user.role, "USER")
        self.assertEqual(user.school_name, "Ananda College")
        self.assertEqual(user.district, "Colombo")
        self.assertIn("User", repr(user))
        self.assertIn("UserStats", repr(stats))

        dto = UserProfileResponse(
            uid=user.uid,
            email=user.email,
            name=user.name,
            role=user.role,
            school_name=user.school_name,
            district=user.district,
            stream=user.stream,
            grade=user.grade,
            attempt=user.attempt,
            xp=stats.xp,
            streak_count=stats.current_streak_days,
            accuracy_rate=stats.accuracy_rate,
            questions_solved=stats.total_solved_count,
            is_premium=user.is_premium,
        )
        self.assertEqual(dto.uid, "usr_007")
        self.assertEqual(dto.email, "student@mathsdd.lk")
        self.assertEqual(dto.xp, 150)
        self.assertEqual(dto.streak_count, 5)
        self.assertEqual(dto.questions_solved, 20)


if __name__ == "__main__":
    unittest.main()

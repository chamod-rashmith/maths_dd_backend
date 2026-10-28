"""
Unit tests for SQLAlchemy 2.0 declarative models and serialization contracts.
"""

import datetime
import unittest
import uuid
from app.core.database import Base
from app.models import MarkingScheme, Question, StudyNote, Subject, SyllabusLesson, User


class TestSQLAlchemyModels(unittest.TestCase):
    """Verifies that all models register with Base.metadata and serialize accurately."""

    def test_metadata_tables_registration(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected_tables = {
            "subjects",
            "syllabus_lessons",
            "questions",
            "marking_schemes",
            "study_notes",
            "users",
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
        data = subject.to_dict()
        self.assertEqual(data["id"], "subj_pmat")
        self.assertEqual(data["name"], "Pure Mathematics")
        self.assertEqual(data["sinhala_name"], "ශුද්ධ ගණිතය")
        self.assertEqual(data["code"], "PMAT")
        self.assertEqual(data["order_index"], 1)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)
        self.assertIn("Subject", repr(subject))

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
        data = lesson.to_dict()
        self.assertEqual(data["id"], "lesson_001")
        self.assertEqual(data["subject_id"], "subj_pmat")
        self.assertEqual(data["title"], "Real Numbers")
        self.assertEqual(data["question_count"], 10)
        self.assertEqual(data["premium_count"], 3)
        self.assertIn("SyllabusLesson", repr(lesson))

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
        data = question.to_dict()
        self.assertEqual(data["id"], "q_100")
        self.assertEqual(data["title"], "Integrate x^2")
        self.assertEqual(data["allocated_marks"], 25)
        self.assertEqual(data["scheduled_date"], today)
        self.assertFalse(data["is_premium"])
        self.assertTrue(data["is_published"])
        self.assertIn("Question", repr(question))

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
        data = scheme.to_dict()
        self.assertEqual(data["id"], str(ms_id))
        self.assertEqual(data["question_id"], "q_100")
        self.assertEqual(data["total_marks"], 25)
        self.assertTrue(data["is_official"])
        self.assertFalse(data["is_premium_only"])
        self.assertIn("MarkingScheme", repr(scheme))

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
        data = note.to_dict()
        self.assertEqual(data["id"], "note_001")
        self.assertEqual(data["title"], "Calculus Summary")
        self.assertTrue(data["is_premium"])
        self.assertEqual(data["author"], "Maths DD Editorial")
        self.assertIn("StudyNote", repr(note))

    def test_user_model_serialization(self) -> None:
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
            xp=150,
            streak_count=5,
            is_premium=False,
        )
        data = user.to_dict()
        self.assertEqual(data["uid"], "usr_007")
        self.assertEqual(data["email"], "student@mathsdd.lk")
        self.assertEqual(data["role"], "USER")
        self.assertEqual(data["school_name"], "Ananda College")
        self.assertEqual(data["district"], "Colombo")
        self.assertEqual(data["xp"], 150)
        self.assertEqual(data["streak_count"], 5)
        self.assertIn("User", repr(user))


if __name__ == "__main__":
    unittest.main()

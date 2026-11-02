"""
SQLAlchemy models initialization.
Exports all entity definitions for Base.metadata registration.
"""

from app.models.subject import Subject
from app.models.lesson import SyllabusLesson
from app.models.question import Question
from app.models.marking_scheme import MarkingScheme
from app.models.study_note import StudyNote
from app.models.user import User
from app.models.progress import UserQuestionAttempt, UserDailyActivity

__all__ = [
    "Subject",
    "SyllabusLesson",
    "Question",
    "MarkingScheme",
    "StudyNote",
    "User",
    "UserQuestionAttempt",
    "UserDailyActivity",
]

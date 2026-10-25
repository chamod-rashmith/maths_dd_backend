"""Abstract Repository Contracts (Ports) for the Domain Layer."""

from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.question_repository import QuestionRepository
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.domain.repositories.user_repository import UserRepository

__all__ = [
    "CurriculumRepository",
    "QuestionRepository",
    "StudyNoteRepository",
    "UserRepository",
]

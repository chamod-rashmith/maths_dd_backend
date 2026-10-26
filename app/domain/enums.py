"""
Core domain Enums for type safety, validation, and Swagger documentation.
"""

from enum import Enum


class UserRole(str, Enum):
    """User authorization roles."""

    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    USER = "USER"


class QuestionDifficulty(str, Enum):
    """Complexity / difficulty level of mathematical questions."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionType(str, Enum):
    """Format and examination structure of questions."""

    SHORT = "SHORT"
    ESSAY = "ESSAY"


class QuestionSchedule(str, Enum):
    """Cadence / schedule category for question releases."""

    REGULAR = "REGULAR"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class QuestionSource(str, Enum):
    """Origin source of the question."""

    PAST_PAPER = "PAST_PAPER"
    MODEL_PAPER = "MODEL_PAPER"
    PROVINCIAL = "PROVINCIAL"
    SCHOOL_PAPER = "SCHOOL_PAPER"

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


class Province(str, Enum):
    """Administrative Provinces of Sri Lanka."""

    WESTERN = "WESTERN"
    CENTRAL = "CENTRAL"
    SOUTHERN = "SOUTHERN"
    NORTHERN = "NORTHERN"
    EASTERN = "EASTERN"
    NORTH_WESTERN = "NORTH_WESTERN"
    NORTH_CENTRAL = "NORTH_CENTRAL"
    UVA = "UVA"
    SABARAGAMUWA = "SABARAGAMUWA"


class StudyStream(str, Enum):
    """G.C.E. A/L Study Stream."""

    PHYSICAL_SCIENCE = "PHYSICAL_SCIENCE"
    BIO_SCIENCE = "BIO_SCIENCE"
    COMMERCE = "COMMERCE"
    ARTS = "ARTS"
    TECHNOLOGY = "TECHNOLOGY"


class StudentGrade(str, Enum):
    """Academic grade or schooling stage of the student."""

    GRADE_12 = "GRADE_12"
    GRADE_13 = "GRADE_13"
    REVISION = "REVISION"


class ExamAttempt(str, Enum):
    """G.C.E. A/L examination sitting attempt."""

    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"

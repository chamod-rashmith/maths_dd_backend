"""
Core domain Enums for type safety, validation, and Swagger documentation.
"""

from enum import Enum


class UserRole(str, Enum):
    """User authorization roles."""

    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    ACCOUNT_AUDIT = "ACCOUNT_AUDIT"
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


class ContentType(str, Enum):
    """Format of question or study note content."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    IMAGE = "image"


class ExamPaperType(str, Enum):
    """Category of A/L examination paper."""

    AL_GOVT = "AL_GOVT"
    MODEL = "MODEL"
    PROVINCIAL = "PROVINCIAL"


class ExamPaperPart(str, Enum):
    """Section / part of an examination paper."""

    PART_I = "PART_I"
    PART_II_A = "PART_II_A"
    PART_II_B = "PART_II_B"
    FULL = "FULL"


class MarkingStepType(str, Enum):
    """Rubric allocation category for marking scheme steps."""

    METHOD = "METHOD"
    ACCURACY = "ACCURACY"
    FINAL = "FINAL"
    BONUS = "BONUS"


class ConfidenceLevel(str, Enum):
    """Student self-reported confidence level when completing a question."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ExamMedium(str, Enum):
    """Language medium of examination."""

    SINHALA = "SINHALA"
    ENGLISH = "ENGLISH"
    TAMIL = "TAMIL"


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

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


class QuestionType(str, Enum):
    """Format and examination structure of questions."""

    SHORT = "SHORT"
    ESSAY = "ESSAY"


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


class LeaderboardScope(str, Enum):
    """Scope of the student XP leaderboard."""

    ISLAND = "ISLAND"
    DISTRICT = "DISTRICT"


class AuditAction(str, Enum):
    """Standardized action codes for Immutable Admin Audit Logs (Ring 4)."""

    BANK_SLIP_APPROVED = "BANK_SLIP_APPROVED"
    BANK_SLIP_REJECTED = "BANK_SLIP_REJECTED"
    SUBSCRIPTIONS_EXPIRE_STALE = "SUBSCRIPTIONS_EXPIRE_STALE"
    QUESTION_UPSERTED = "QUESTION_UPSERTED"
    QUESTION_DELETED = "QUESTION_DELETED"
    STUDY_NOTE_UPSERTED = "STUDY_NOTE_UPSERTED"
    STUDY_NOTE_DELETED = "STUDY_NOTE_DELETED"
    SUBJECT_UPSERTED = "SUBJECT_UPSERTED"
    SUBJECT_DELETED = "SUBJECT_DELETED"
    LESSON_UPSERTED = "LESSON_UPSERTED"
    LESSON_DELETED = "LESSON_DELETED"
    ADMIN_TOTP_SETUP_INITIATED = "ADMIN_TOTP_SETUP_INITIATED"
    ADMIN_TOTP_ENABLED = "ADMIN_TOTP_ENABLED"
    ADMIN_SESSION_ELEVATED = "ADMIN_SESSION_ELEVATED"


class AuditResourceType(str, Enum):
    """Resource categories tracked in Immutable Admin Audit Logs (Ring 4)."""

    SUBSCRIPTION = "SUBSCRIPTION"
    QUESTION = "QUESTION"
    STUDY_NOTE = "STUDY_NOTE"
    SUBJECT = "SUBJECT"
    LESSON = "LESSON"
    ADMIN_TOTP = "ADMIN_TOTP"


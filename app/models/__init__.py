"""
SQLAlchemy models initialization.
Exports all entity definitions for Base.metadata registration.
"""

from app.models.subject import Subject
from app.models.lesson import SyllabusLesson
from app.models.question import Question
from app.models.marking_scheme import MarkingScheme
from app.models.study_note import StudyNote, StudyNoteVote, StudyNoteBookmark
from app.models.exam_paper import ExamPaper
from app.models.district import District
from app.models.user import User
from app.models.student_profile import StudentProfile
from app.models.user_stats import UserStats
from app.models.subscription import (
    SubscriptionPlan,
    PlanPrice,
    UserSubscription,
    Payment,
    BankTransferSlip,
    ProcessedWebhookEvent,
)
from app.models.progress import UserQuestionAttempt, UserDailyActivity, XpTransaction
from app.models.daily_challenge import DailyChallenge, DailyChallengeQuestion
from app.models.admin_totp import AdminTotpCredential
from app.models.admin_audit_log import AdminAuditLog

__all__ = [
    "Subject",
    "SyllabusLesson",
    "Question",
    "MarkingScheme",
    "StudyNote",
    "StudyNoteVote",
    "StudyNoteBookmark",
    "ExamPaper",
    "District",
    "User",
    "StudentProfile",
    "UserStats",
    "SubscriptionPlan",
    "PlanPrice",
    "UserSubscription",
    "Payment",
    "BankTransferSlip",
    "ProcessedWebhookEvent",
    "UserQuestionAttempt",
    "UserDailyActivity",
    "XpTransaction",
    "DailyChallenge",
    "DailyChallengeQuestion",
    "AdminTotpCredential",
    "AdminAuditLog",
]

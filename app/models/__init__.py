"""
SQLAlchemy models initialization.
Exports all entity definitions for Base.metadata registration.
"""

from app.models.subject import Subject
from app.models.lesson import SyllabusLesson
from app.models.question import Question
from app.models.marking_scheme import MarkingScheme, MarkingSchemeStep
from app.models.study_note import StudyNote
from app.models.exam_paper import ExamPaper
from app.models.district import District
from app.models.user import User
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

__all__ = [
    "Subject",
    "SyllabusLesson",
    "Question",
    "MarkingScheme",
    "MarkingSchemeStep",
    "StudyNote",
    "ExamPaper",
    "District",
    "User",
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
]

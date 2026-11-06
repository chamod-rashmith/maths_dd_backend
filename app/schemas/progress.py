"""
Pydantic v2 schemas for Student Progress Tracking, Question Attempts, Activity Heatmaps, and XP Ledger.
මෙම මොඩියුලය මඟින් ශිෂ්‍ය ප්‍රගතිය, ප්‍රශ්න විසඳීමේ කාලය, දිනපතා Heatmap, සහ Gamification XP විගණන ලේඛනය
සඳහා වන සියලුම DTO Schemas නිරවද්‍යව camelCase serialization සමඟින් කළමනාකරණය කරයි.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BaseProgressSchema(BaseModel):
    """Base schema configuring snake_case serialization and ORM mode."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class CompletedQuestionRecordSchema(BaseProgressSchema):
    """
    ශිෂ්‍යයෙකු විසඳූ ප්‍රශ්නයක සාරාංශ වාර්තාව (Completed Question Record DTO).
    `time_spent_seconds` මඟින් මෙම ප්‍රශ්නය පුහුණු වීමට වැය කළ සමස්ත කාලයත් (Cumulative Seconds),
    `last_attempt_duration_seconds` මඟින් අවසන් වරට වැය කළ කාලයත් නියෝජනය වේ.
    """

    question_id: str = Field(..., description="ප්‍රශ්නයේ හැඳුනුම් අංකය")
    title: str = Field(..., description="ප්‍රශ්නයේ මාතෘකාව")
    subject: str = Field("pureMaths", description="විෂය (pureMaths, appliedMaths)")
    lesson_id: Optional[str] = Field(None, description="අදාළ පාඩමේ ID")
    question_type: str = Field("short", description="ප්‍රශ්න වර්ගය (short, essay)")
    is_daily_question: bool = Field(False, description="දිනපතා අභ්‍යාසයක් ලෙස විසඳුවේද යන්න")
    time_spent_seconds: int = Field(0, description="සමස්ත වැය කළ කාලය (Cumulative Seconds across all attempts)")
    last_attempt_duration_seconds: int = Field(0, description="අවසන් වරට විසඳීමට වැය වූ කාලය (Most recent attempt duration)")
    target_duration_seconds: int = Field(0, description="නිර්දේශිත කාලය")
    was_overtime: bool = Field(False, description="කාලය ඉක්මවා ගියේද යන්න")
    attempt_count: int = Field(1, description="විසඳූ වාර ගණන")
    completed_date_key: str = Field(..., description="විසඳූ දිනය (YYYY-MM-DD)")
    completed_at: datetime = Field(..., description="විසඳූ නිශ්චිත වේලාව (UTC)")
    is_bookmarked: bool = Field(False, description="Bookmark කර ඇත්ද යන්න")
    confidence: Optional[str] = Field(None, description="විශ්වාසනීයත්ව මට්ටම (LOW, MEDIUM, HIGH)")
    student_notes: Optional[str] = Field(None, description="ශිෂ්‍යයාගේ සටහන්")


class DailyActivityBucketSchema(BaseProgressSchema):
    """
    දිනපතා අධ්‍යයන දත්ත (Daily Activity Heatmap Bucket DTO).
    GitHub-style Heatmap එකක් ජනනය කිරීම සඳහා අවශ්‍ය දිනපතා සංඛ්‍යාලේඛන.
    """

    date_key: str = Field(..., description="දිනය (YYYY-MM-DD Asia/Colombo)")
    questions_solved_count: int = Field(0, description="අදාළ දිනයේ විසඳූ ප්‍රශ්න ගණන")
    total_time_spent_seconds: int = Field(0, description="අදාළ දිනයේ වැය කළ මුළු කාලය (තත්පර වලින්)")
    daily_challenge_completed: bool = Field(False, description="Daily Challenge සම්පූර්ණ කළේද යන්න")
    question_ids: List[str] = Field(default_factory=list, description="එදින විසඳූ ප්‍රශ්න ලැයිස්තුව")


class XpTransactionResponse(BaseProgressSchema):
    """
    XP විගණන ගනුදෙනු විස්තරය (XP Audit Transaction Proof DTO).
    ශිෂ්‍යයාට ලැබුණු හෝ අඩු වූ සෑම XP අගයකටම අදාළ සාක්ෂිය සහ පැහැදිලි කිරීම.
    """

    id: str = Field(..., description="ගනුදෙනුවේ ID")
    amount: int = Field(..., description="ලැබුණු/අඩු වූ XP ප්‍රමාණය (+10, +25, +50, -10)")
    reason: str = Field(..., description="හේතු කේතය (QUESTION_SOLVED, DAILY_CHALLENGE_BONUS, etc.)")
    question_id: Optional[str] = Field(None, description="අදාළ ප්‍රශ්නයේ ID")
    description_si: Optional[str] = Field(None, description="සිංහල විස්තරය (e.g. 'කෙටි ප්‍රශ්නයක් විසඳීම (+10 XP)')")
    description_en: Optional[str] = Field(None, description="ඉංග්‍රීසි විස්තරය")
    created_at: datetime = Field(..., description="XP හිමි වූ දිනය සහ වේලාව")


class XpHistoryResponse(BaseProgressSchema):
    """ශිෂ්‍යයාගේ සමස්ත XP ඉතිහාසය (Complete XP History & Audit Trail)."""

    total_xp: int = Field(..., description="සමස්ත තහවුරු කළ XP අගය")
    transactions: List[XpTransactionResponse] = Field(default_factory=list, description="XP ගනුදෙනු ලැයිස්තුව")


class UserProgressSummaryResponse(BaseProgressSchema):
    """
    ශිෂ්‍යයාගේ සමස්ත ප්‍රගති සාරාංශය (Full Aggregated Progress Summary DTO).
    Mobile App එකෙහි Dashboard සහ Profile තිර සඳහා අවශ්‍ය සියලුම සංඛ්‍යාලේඛන මෙහි අඩංගු වේ.
    """

    completed_questions: Dict[str, CompletedQuestionRecordSchema] = Field(
        default_factory=dict, description="විසඳූ ප්‍රශ්න ලැයිස්තුව (question_id මඟින් key කර ඇත)"
    )
    daily_activity: Dict[str, DailyActivityBucketSchema] = Field(
        default_factory=dict, description="දිනපතා Activity Heatmap දත්ත (YYYY-MM-DD මඟින් key කර ඇත)"
    )
    solved_count_by_lesson: Dict[str, int] = Field(
        default_factory=dict, description="පාඩම් අනුව විසඳූ ප්‍රශ්න ගණන"
    )
    solved_count_by_subject: Dict[str, int] = Field(
        default_factory=dict, description="විෂය අනුව විසඳූ ප්‍රශ්න ගණන"
    )
    total_questions_solved: int = Field(0, description="විසඳූ සමස්ත ප්‍රශ්න ගණන")
    total_time_spent_seconds: int = Field(0, description="සමස්ත අධ්‍යයන කාලය (තත්පර වලින් - Accurate Cumulative)")
    current_streak_days: int = Field(0, description="වත්මන් අඛණ්ඩ දින ගණන (Current Streak)")
    longest_streak_days: int = Field(0, description="වැඩිම අඛණ්ඩ දින ගණන (Longest Streak)")
    last_active_date_key: Optional[str] = Field(None, description="අවසන් වරට ක්‍රියාකාරී වූ දිනය (YYYY-MM-DD)")
    xp: int = Field(0, description="සමස්ත අත්දැකීම් ලකුණු (Verified XP from Ledger)")
    recent_xp_transactions: Optional[List[XpTransactionResponse]] = Field(
        None, description="නවතම XP ගනුදෙනු සාක්ෂි (Recent XP Proofs)"
    )


class MarkQuestionCompletedRequest(BaseProgressSchema):
    """ප්‍රශ්නයක් විසඳූ බව සටහන් කිරීම සඳහා එවන Payload එක."""

    question_id: str = Field(..., description="විසඳූ ප්‍රශ්නයේ ID")
    time_spent_seconds: int = Field(0, ge=0, description="මෙම විසඳීම සඳහා ගත වූ කාලය (තත්පර වලින්)")
    target_duration_seconds: int = Field(0, ge=0, description="නිර්දේශිත කාලය (තත්පර වලින්)")
    was_overtime: bool = Field(False, description="කාලය ඉක්මවා ගියේද යන්න")
    is_daily_question: bool = Field(False, description="දිනපතා අභ්‍යාස ප්‍රශ්නයක්ද යන්න")
    confidence: Optional[str] = Field(None, description="විශ්වාසනීයත්වය (LOW, MEDIUM, HIGH)")
    student_notes: Optional[str] = Field(None, description="ශිෂ්‍යයාගේ සටහන්")
    is_bookmarked: Optional[bool] = Field(None, description="Bookmark කරන්නේද යන්න")


class ToggleBookmarkRequest(BaseProgressSchema):
    """ප්‍රශ්නයක් Bookmark / Star කිරීම සඳහා එවන Payload එක."""

    is_bookmarked: bool = Field(..., description="Bookmark තත්වය")

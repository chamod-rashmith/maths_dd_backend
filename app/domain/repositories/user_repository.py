"""
Abstract Repository Contract for User Profile persistence.

===============================================================================
පරිශීලක සහ ශාස්ත්‍රීය පැතිකඩ Repository අතුරුමුහුණත (User Repository Contract):
-------------------------------------------------------------------------------
Auth credentials සහ normalized `StudentProfile` (Target A/L year, attempt,
Z-score exam district) දත්ත කළමනාකරණය සඳහා interface එක.
===============================================================================
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union


class UserRepository(ABC):
    """Domain contract defining user profile persistence operations."""

    @abstractmethod
    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Fetches a user profile record by its unique Firebase UID."""
        raise NotImplementedError

    @abstractmethod
    async def sync_or_create(
        self,
        uid: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
        telephone_no: Optional[str] = None,
        school_name: Optional[str] = None,
        district_id: Optional[Union[int, str]] = None,
        district: Optional[Union[int, str]] = None,
        stream: Optional[str] = None,
        grade: Optional[str] = None,
        attempt: Optional[str] = None,
        exam_year: Optional[int] = None,
        attempt_number: Optional[int] = None,
        exam_district_id: Optional[Union[int, str]] = None,
        medium: Optional[str] = "SINHALA",
    ) -> Dict[str, Any]:
        """Idempotently creates or updates a user profile and student_profile upon authentication sync."""
        raise NotImplementedError

"""
Abstract Repository Contract for Study Notes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StudyNoteRepository(ABC):
    """Domain contract defining study notes persistence, voting, and bookmarking."""

    @abstractmethod
    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        bookmarked_only: bool = False,
    ) -> Dict[str, Any]:
        """Lists study notes with filtered items, aggregate vote counts, user state, and total count."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        note_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches a single study note by its unique ID along with vote counts and user state."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_note_states(
        self,
        user_id: str,
        note_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Fetches a mapping of note_id -> {'user_vote': int, 'is_bookmarked': bool} for the given user."""
        raise NotImplementedError

    @abstractmethod
    async def vote_note(
        self,
        note_id: str,
        user_id: str,
        vote: int,
    ) -> Optional[Dict[str, Any]]:
        """Casts, switches, or removes a vote (1, -1, 0) on a study note and updates aggregate counters."""
        raise NotImplementedError

    @abstractmethod
    async def toggle_bookmark(
        self,
        note_id: str,
        user_id: str,
        is_bookmarked: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Bookmarks or unbookmarks a study note for the given user."""
        raise NotImplementedError

    @abstractmethod
    async def upsert(
        self,
        note_id: Optional[str],
        title: str,
        subject_id: str,
        lesson_id: Optional[str],
        content_text: Optional[str] = "",
        description: Optional[str] = "",
        pdf_url: Optional[str] = None,
        is_premium: bool = False,
        order_index: int = 0,
        author: Optional[str] = "",
    ) -> Dict[str, Any]:
        """Creates or updates a study note."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, note_id: str) -> Dict[str, Any]:
        """Deletes a study note by its unique ID."""
        raise NotImplementedError


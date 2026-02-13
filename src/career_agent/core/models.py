"""Data models for library monitoring."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Type of library change detected."""
    NEW = "new"              # First time tracking
    MAJOR = "major"          # Major version bump (breaking changes likely)
    MINOR = "minor"          # Minor version bump (new features)
    PATCH = "patch"          # Patch version bump (bug fixes)
    UNKNOWN = "unknown"      # Version format not semver


class ActionType(str, Enum):
    """Recommended action for a change."""
    DEEP_DIVE = "deep_dive"      # Important, study thoroughly
    SKIM = "skim"                # Note it, review briefly
    BOOKMARK = "bookmark"        # Save for later
    URGENT = "urgent"            # Breaking change, check compatibility


class LearningConcepts(BaseModel):
    """Python concepts at different skill levels."""
    beginner: list[str] = Field(default_factory=list)
    intermediate: list[str] = Field(default_factory=list)
    advanced: list[str] = Field(default_factory=list)


class LibraryInfo(BaseModel):
    """Current state of a monitored library."""
    name: str
    display_name: str
    current_version: str
    latest_version: str
    last_checked: datetime
    homepage: Optional[str] = None
    summary: Optional[str] = None
    requires_python: Optional[str] = None
    is_outdated: bool = False


class LibraryChange(BaseModel):
    """A detected change in a library."""
    library: str
    display_name: str
    previous_version: Optional[str]
    new_version: str
    change_type: ChangeType
    detected_at: datetime
    release_date: Optional[datetime] = None
    changelog_url: Optional[str] = None

    # Learning integration
    concepts: LearningConcepts = Field(default_factory=LearningConcepts)
    relevance: list[str] = Field(default_factory=list)
    action: ActionType = ActionType.SKIM
    learning_prompt: Optional[str] = None


class StudySession(BaseModel):
    """A deep dive study session."""
    library: str
    display_name: str
    version: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    cards_created: int = 0
    completed: bool = False


class LibraryState(BaseModel):
    """Complete state of all monitored libraries."""
    libraries: dict[str, LibraryInfo] = Field(default_factory=dict)
    recent_changes: list[LibraryChange] = Field(default_factory=list)
    study_sessions: list[StudySession] = Field(default_factory=list)
    last_full_check: Optional[datetime] = None

    def get_outdated(self) -> list[LibraryInfo]:
        """Get libraries that have updates available."""
        return [lib for lib in self.libraries.values() if lib.is_outdated]

    def get_changes_since(self, since: datetime) -> list[LibraryChange]:
        """Get changes detected after a specific time."""
        return [c for c in self.recent_changes if c.detected_at > since]

    def get_active_session(self) -> Optional[StudySession]:
        """Get currently active study session if any."""
        for session in reversed(self.study_sessions):
            if not session.completed:
                return session
        return None

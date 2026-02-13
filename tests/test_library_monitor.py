"""Tests for library monitoring functionality."""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile

from career_agent.core.models import (
    LibraryState,
    LibraryInfo,
    LibraryChange,
    ChangeType,
    ActionType,
)
from career_agent.core.storage import Storage


class TestStorage:
    """Tests for Storage class."""

    def test_load_empty(self):
        """Loading non-existent file returns empty state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(Path(tmpdir) / "test.json")
            state = storage.load()
            assert state.libraries == {}
            assert state.recent_changes == []

    def test_save_and_load(self):
        """Saving and loading preserves state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(Path(tmpdir) / "test.json")

            state = LibraryState()
            state.libraries["torch"] = LibraryInfo(
                name="torch",
                display_name="PyTorch",
                current_version="2.0.0",
                latest_version="2.1.0",
                last_checked=datetime.now(),
                is_outdated=True,
            )

            storage.save(state)
            loaded = storage.load()

            assert "torch" in loaded.libraries
            assert loaded.libraries["torch"].current_version == "2.0.0"
            assert loaded.libraries["torch"].is_outdated is True


class TestModels:
    """Tests for data models."""

    def test_library_state_get_outdated(self):
        """get_outdated returns only outdated libraries."""
        state = LibraryState()
        state.libraries["torch"] = LibraryInfo(
            name="torch",
            display_name="PyTorch",
            current_version="2.0.0",
            latest_version="2.1.0",
            last_checked=datetime.now(),
            is_outdated=True,
        )
        state.libraries["numpy"] = LibraryInfo(
            name="numpy",
            display_name="NumPy",
            current_version="1.26.0",
            latest_version="1.26.0",
            last_checked=datetime.now(),
            is_outdated=False,
        )

        outdated = state.get_outdated()
        assert len(outdated) == 1
        assert outdated[0].name == "torch"

    def test_library_change_model(self):
        """LibraryChange model validates correctly."""
        change = LibraryChange(
            library="torch",
            display_name="PyTorch",
            previous_version="2.0.0",
            new_version="2.1.0",
            change_type=ChangeType.MINOR,
            detected_at=datetime.now(),
            relevance=["portfolio", "production"],
            action=ActionType.DEEP_DIVE,
        )
        assert change.library == "torch"
        assert change.change_type == ChangeType.MINOR

"""Persistent storage for library state."""

import json
from pathlib import Path
from typing import Optional

from .models import LibraryState


class Storage:
    """JSON-based storage for library monitoring state."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> LibraryState:
        """Load state from disk, or return empty state if not exists."""
        if not self.file_path.exists():
            return LibraryState()

        try:
            with open(self.file_path) as f:
                data = json.load(f)
            return LibraryState.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            # Corrupted file, start fresh but preserve backup
            backup_path = self.file_path.with_suffix(".json.bak")
            self.file_path.rename(backup_path)
            print(f"Warning: Corrupted state file backed up to {backup_path}")
            return LibraryState()

    def save(self, state: LibraryState) -> None:
        """Save state to disk."""
        self._ensure_data_dir()
        with open(self.file_path, "w") as f:
            json.dump(state.model_dump(mode="json"), f, indent=2, default=str)

    def clear(self) -> None:
        """Clear all stored state."""
        if self.file_path.exists():
            self.file_path.unlink()

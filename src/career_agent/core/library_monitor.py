"""Library monitoring via PyPI API."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from packaging import version as pkg_version

import httpx

from ..config import LIBRARIES, LIBRARY_CONTEXT, PYPI_API_URL
from .models import (
    ActionType,
    ChangeType,
    LearningConcepts,
    LibraryChange,
    LibraryInfo,
    LibraryState,
)
from .storage import Storage


class LibraryMonitor:
    """Monitor Python libraries for updates via PyPI."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self.state = storage.load()

    async def fetch_package_info(self, package: str) -> Optional[dict]:
        """Fetch package info from PyPI API."""
        url = PYPI_API_URL.format(package=package)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error fetching {package}: {e}")
                return None

    def _detect_change_type(
        self, old_version: Optional[str], new_version: str
    ) -> ChangeType:
        """Determine what type of version change occurred."""
        if old_version is None:
            return ChangeType.NEW

        try:
            old = pkg_version.parse(old_version)
            new = pkg_version.parse(new_version)

            if hasattr(old, "major") and hasattr(new, "major"):
                if new.major > old.major:
                    return ChangeType.MAJOR
                elif new.minor > old.minor:
                    return ChangeType.MINOR
                elif new.micro > old.micro:
                    return ChangeType.PATCH
        except Exception:
            pass

        return ChangeType.UNKNOWN

    def _determine_action(
        self, change_type: ChangeType, relevance: list[str]
    ) -> ActionType:
        """Determine recommended action based on change type and relevance."""
        if change_type == ChangeType.MAJOR:
            return ActionType.URGENT if "production" in relevance else ActionType.DEEP_DIVE
        elif change_type == ChangeType.MINOR:
            if "portfolio" in relevance or "interview" in relevance:
                return ActionType.DEEP_DIVE
            return ActionType.SKIM
        elif change_type == ChangeType.NEW:
            return ActionType.DEEP_DIVE
        else:
            return ActionType.BOOKMARK

    def _generate_learning_concepts(
        self, package: str, change_type: ChangeType
    ) -> LearningConcepts:
        """Generate learning concepts based on library and change type."""
        # Default concepts by library category
        concepts_map = {
            "torch": LearningConcepts(
                beginner=["tensor operations", "basic neural networks"],
                intermediate=["autograd", "custom datasets", "model saving"],
                advanced=["JIT compilation", "distributed training", "custom C++ extensions"],
            ),
            "transformers": LearningConcepts(
                beginner=["tokenization", "pre-trained models"],
                intermediate=["fine-tuning", "attention mechanisms"],
                advanced=["model parallelism", "quantization", "custom architectures"],
            ),
            "ultralytics": LearningConcepts(
                beginner=["object detection basics", "inference"],
                intermediate=["training custom models", "data augmentation"],
                advanced=["model export", "optimization", "multi-task learning"],
            ),
            "fastapi": LearningConcepts(
                beginner=["routes", "request/response"],
                intermediate=["dependency injection", "middleware", "async"],
                advanced=["OpenAPI customization", "background tasks", "websockets"],
            ),
            "opencv-python": LearningConcepts(
                beginner=["image loading", "basic transforms"],
                intermediate=["feature detection", "contours"],
                advanced=["camera calibration", "stereo vision", "GPU acceleration"],
            ),
            "ray": LearningConcepts(
                beginner=["remote functions", "actors"],
                intermediate=["object store", "task dependencies"],
                advanced=["cluster deployment", "autoscaling", "placement groups"],
            ),
            "supervision": LearningConcepts(
                beginner=["annotation visualization", "video processing"],
                intermediate=["tracking", "zone counting"],
                advanced=["custom annotators", "integration patterns"],
            ),
            "onnxruntime": LearningConcepts(
                beginner=["model loading", "inference"],
                intermediate=["execution providers", "optimization"],
                advanced=["custom operators", "quantization", "graph optimization"],
            ),
        }
        return concepts_map.get(package, LearningConcepts())

    def _generate_learning_prompt(
        self, package: str, change_type: ChangeType, new_version: str
    ) -> str:
        """Generate a learning prompt for the change."""
        context = LIBRARY_CONTEXT.get(package, {})
        display_name = context.get("display_name", package)

        if change_type == ChangeType.MAJOR:
            return f"BREAKING: {display_name} {new_version} - Review migration guide and check compatibility"
        elif change_type == ChangeType.MINOR:
            return f"NEW FEATURES: {display_name} {new_version} - Explore new capabilities and API additions"
        elif change_type == ChangeType.NEW:
            return f"START TRACKING: {display_name} {new_version} - Review current API and core features"
        else:
            return f"UPDATE: {display_name} {new_version} - Check release notes for bug fixes"

    async def check_library(self, package: str) -> Optional[LibraryChange]:
        """Check a single library for updates."""
        info = await self.fetch_package_info(package)
        if not info:
            return None

        pypi_info = info.get("info", {})
        latest_version = pypi_info.get("version")

        if not latest_version:
            return None

        context = LIBRARY_CONTEXT.get(package, {})
        display_name = context.get("display_name", package)
        relevance = context.get("relevance", [])

        # Get previous version from state
        previous_info = self.state.libraries.get(package)
        previous_version = previous_info.current_version if previous_info else None

        # Detect if there's a change
        change = None
        if previous_version != latest_version:
            change_type = self._detect_change_type(previous_version, latest_version)
            action = self._determine_action(change_type, relevance)
            concepts = self._generate_learning_concepts(package, change_type)
            learning_prompt = self._generate_learning_prompt(package, change_type, latest_version)

            change = LibraryChange(
                library=package,
                display_name=display_name,
                previous_version=previous_version,
                new_version=latest_version,
                change_type=change_type,
                detected_at=datetime.now(),
                changelog_url=pypi_info.get("project_urls", {}).get("Changelog"),
                concepts=concepts,
                relevance=relevance,
                action=action,
                learning_prompt=learning_prompt,
            )

        # Update library info in state
        self.state.libraries[package] = LibraryInfo(
            name=package,
            display_name=display_name,
            current_version=previous_version or latest_version,
            latest_version=latest_version,
            last_checked=datetime.now(),
            homepage=pypi_info.get("home_page") or pypi_info.get("project_url"),
            summary=pypi_info.get("summary"),
            requires_python=pypi_info.get("requires_python"),
            is_outdated=previous_version is not None and previous_version != latest_version,
        )

        return change

    async def check_all_libraries(
        self, libraries: Optional[list[str]] = None
    ) -> list[LibraryChange]:
        """Check all monitored libraries for updates."""
        libs_to_check = libraries or LIBRARIES
        tasks = [self.check_library(lib) for lib in libs_to_check]
        results = await asyncio.gather(*tasks)

        changes = [r for r in results if r is not None]

        # Add changes to state
        for change in changes:
            self.state.recent_changes.append(change)

        # Keep only last 100 changes
        self.state.recent_changes = self.state.recent_changes[-100:]
        self.state.last_full_check = datetime.now()

        # Save state
        self.storage.save(self.state)

        return changes

    def get_status(self) -> LibraryState:
        """Get current state of all monitored libraries."""
        return self.state

    def get_outdated(self) -> list[LibraryInfo]:
        """Get libraries with available updates."""
        return self.state.get_outdated()

    def mark_updated(self, package: str) -> bool:
        """Mark a library as updated (user has updated their local version)."""
        if package not in self.state.libraries:
            return False

        lib = self.state.libraries[package]
        lib.current_version = lib.latest_version
        lib.is_outdated = False
        self.storage.save(self.state)
        return True

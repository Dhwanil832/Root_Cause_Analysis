"""Replaceable model, version-read, and persistence ports."""
from __future__ import annotations

from typing import Any, Protocol

from .contracts import AssessmentTask, VersionSnapshot


class AssessorModel(Protocol):
    def ask(self, task: str, system: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class VersionReader(Protocol):
    def read(self, case_id: str, material_ids: tuple[str, ...]) -> VersionSnapshot: ...


class AssessmentLedger(Protocol):
    def begin(self, task: AssessmentTask, fingerprint: str) -> tuple[str, Any | None]: ...
    def finish(self, task: AssessmentTask, fingerprint: str, result: Any) -> None: ...
    def abandon(self, work_item_id: str) -> None: ...

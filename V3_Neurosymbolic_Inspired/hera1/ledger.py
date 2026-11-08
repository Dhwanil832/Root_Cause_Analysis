"""Thread-safe in-memory idempotency ledger for sandbox runs."""
from __future__ import annotations

from threading import RLock
from typing import Any


class InMemoryAssessmentLedger:
    """Replace with durable transactional storage for deployment."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._completed: dict[tuple[str, str], tuple[str, Any]] = {}
        self._active: set[str] = set()

    def begin(self, task, fingerprint: str) -> tuple[str, Any | None]:
        key = (task.work_item_id, task.event_id)
        with self._lock:
            prior = self._completed.get(key)
            if prior:
                if prior[0] != fingerprint:
                    return "conflict", None
                return "duplicate", prior[1]
            if task.work_item_id in self._active:
                return "busy", None
            self._active.add(task.work_item_id)
            return "claimed", None

    def finish(self, task, fingerprint: str, result: Any) -> None:
        with self._lock:
            key = (task.work_item_id, task.event_id)
            prior = self._completed.get(key)
            if prior and prior[0] != fingerprint:
                raise ValueError("event ID already completed with different task content")
            self._completed[key] = (fingerprint, result)
            self._active.discard(task.work_item_id)

    def abandon(self, work_item_id: str) -> None:
        with self._lock:
            self._active.discard(work_item_id)

"""Thread-safe in-memory event ledger for local runs and tests.

Production deployments should replace this with durable transactional storage.
"""
from __future__ import annotations

from threading import RLock
from typing import Any


class InMemoryWorkLedger:
    def __init__(self) -> None:
        self._lock = RLock()
        self._events: dict[tuple[str, str], Any] = {}
        self._active: set[str] = set()

    def begin(self, work_item_id: str, event_id: str, input_fingerprint: str):
        key = (work_item_id, event_id)
        with self._lock:
            if key in self._events:
                prior_fingerprint, prior_result = self._events[key]
                if prior_fingerprint != input_fingerprint:
                    return "conflict", None
                return "duplicate", prior_result
            if work_item_id in self._active:
                return "busy", None
            self._active.add(work_item_id)
            return "claimed", None

    def finish(self, work_item_id: str, event_id: str, input_fingerprint: str, result: Any) -> None:
        with self._lock:
            self._events[(work_item_id, event_id)] = (input_fingerprint, result)
            self._active.discard(work_item_id)

    def abandon(self, work_item_id: str) -> None:
        with self._lock:
            self._active.discard(work_item_id)


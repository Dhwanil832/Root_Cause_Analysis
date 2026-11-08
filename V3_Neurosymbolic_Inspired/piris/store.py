"""In-memory reference store with idempotency and content reuse."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from threading import RLock
from typing import Any

from .contracts import IntakeResult, MaterialProcessingUpdate, MaterialRecord


class InMemoryIntakeStore:
    """Thread-safe test/reference store; production should implement durable transactions."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._material_operation_locks: dict[str, RLock] = {}
        self._material_identity_locks: dict[tuple[str, str, str], RLock] = {}
        self._materials: dict[str, MaterialRecord] = {}
        # Media type is part of the extraction identity: identical bytes can
        # be parsed differently when submitted under different MIME types.
        self._digest_to_material: dict[tuple[str, str, str], str] = {}
        self._submission_fingerprints: dict[str, str] = {}
        self._submission_results: dict[str, IntakeResult] = {}
        self._active_submissions: set[str] = set()
        self._index_records: dict[str, dict[str, Any]] = {}
        self._processing_updates: list[MaterialProcessingUpdate] = []

    def begin(self, submission_id: str, fingerprint: str) -> tuple[str, IntakeResult | None]:
        with self._lock:
            old_fp = self._submission_fingerprints.get(submission_id)
            if old_fp is not None:
                if old_fp != fingerprint:
                    return "conflict", None
                if submission_id in self._submission_results:
                    return "duplicate", self._submission_results[submission_id]
                if submission_id in self._active_submissions:
                    return "busy", None
            self._submission_fingerprints[submission_id] = fingerprint
            self._active_submissions.add(submission_id)
            return "claimed", None

    def finish(self, result: IntakeResult) -> None:
        with self._lock:
            self._submission_results[result.submission_id] = result
            self._active_submissions.discard(result.submission_id)

    def abandon(self, submission_id: str) -> None:
        with self._lock:
            self._active_submissions.discard(submission_id)

    def get_material_by_digest(self, case_id: str, digest: str,
                               media_type: str = "application/octet-stream") -> MaterialRecord | None:
        with self._lock:
            material_id = self._digest_to_material.get((case_id, digest, media_type))
            return self._materials.get(material_id) if material_id else None

    def add_material_if_absent(self, material: MaterialRecord) -> tuple[MaterialRecord, bool]:
        with self._lock:
            key = (material.case_id, material.content_digest, material.media_type)
            existing_id = self._digest_to_material.get(key)
            if existing_id is not None:
                existing = self._materials[existing_id]
                return existing, False
            self._materials[material.material_id] = material
            self._digest_to_material[key] = material.material_id
            return material, True

    def add_submission_to_material(self, material_id: str, submission_id: str) -> MaterialRecord:
        with self._lock:
            material = self._materials[material_id]
            if submission_id not in material.submission_ids:
                material = replace(material, submission_ids=material.submission_ids + (submission_id,))
                self._materials[material_id] = material
            return material

    def update_material(self, material: MaterialRecord) -> None:
        with self._lock:
            self._materials[material.material_id] = material

    def get_material(self, material_id: str) -> MaterialRecord | None:
        with self._lock:
            return self._materials.get(material_id)

    def material_operation_lock(self, material_id: str) -> RLock:
        """Serialize expensive per-material operations such as indexing."""
        with self._lock:
            return self._material_operation_locks.setdefault(material_id, RLock())

    def material_identity_lock(self, case_id: str, digest: str,
                               media_type: str) -> RLock:
        """Prevent duplicate parsing when identical arrivals race."""
        key = (case_id, digest, media_type)
        with self._lock:
            return self._material_identity_locks.setdefault(key, RLock())

    def materials_for_case(self, case_id: str) -> tuple[MaterialRecord, ...]:
        with self._lock:
            return tuple(m for m in self._materials.values() if m.case_id == case_id)

    def get_material_version(self, material_id: str) -> str | None:
        with self._lock:
            material = self._materials.get(material_id)
            return material.version_id if material else None

    def index_material(self, material_id: str, record: dict[str, Any]) -> None:
        with self._lock:
            self._index_records[material_id] = dict(record)

    def indexed_record(self, material_id: str) -> dict[str, Any] | None:
        with self._lock:
            rec = self._index_records.get(material_id)
            return dict(rec) if rec is not None else None

    def record_processing_update(self, update: MaterialProcessingUpdate) -> MaterialProcessingUpdate:
        with self._lock:
            for event in self._processing_updates:
                if event.event_id == update.event_id:
                    return event
            self._processing_updates.append(update)
            return update

    def processing_updates(self) -> tuple[MaterialProcessingUpdate, ...]:
        with self._lock:
            return tuple(self._processing_updates)

    @staticmethod
    def fingerprint(payload: Any) -> str:
        # Canonical JSON makes dictionary insertion order irrelevant and fails
        # explicitly for values that cannot be represented in the input contract.
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False).encode("utf-8")
        return sha256(encoded).hexdigest()


"""Canonical input fingerprints and deterministic no-op detection."""

from __future__ import annotations

import hashlib
import json
import math
import threading
from dataclasses import dataclass, fields, is_dataclass, asdict
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping, Optional, Protocol

from .contracts import SpecialistHistory


def _canonicalize(value: Any) -> Any:
    """Convert supported Python values to stable, JSON-safe structures."""
    if is_dataclass(value):
        return _canonicalize(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("fingerprint mappings must have string keys")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (set, frozenset)):
        items = [_canonicalize(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and infinity are not valid fingerprint values")
        return value
    raise TypeError(f"unsupported fingerprint value: {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class AssignmentFingerprintInput:
    """Material assignment fields that affect Specialist behavior.

    `assignment_id` and any external idempotency key are deliberately omitted:
    they identify a delivery attempt, not its semantic input. Case/board
    snapshot IDs are fingerprinted. `history_version` is checked separately
    for snapshot compatibility; the relevant history projection is
    fingerprinted so a sequence-number-only bump does not force another call.
    """

    case_id: str
    specialist_scope_id: str
    case_snapshot_id: str
    board_version: str
    history_version: str
    mode: str
    focal_proposition_id: Optional[str]
    operation_goal: str
    lead_direction: Any
    initial_case_packet: Any
    relevant_graph: Any
    source_bundle: Any
    relevant_history: Any
    lead_feedback: Any
    assessor_annotations: Any
    changed_ids: Any
    budgets: Any
    config_version: str = "1"
    explicitly_targeted_candidate_ids: Any = ()
    available_proposition_ids: Any = ()


def compute_input_fingerprint(payload: AssignmentFingerprintInput | Mapping[str, Any]) -> str:
    """Return a SHA-256 fingerprint stable across mapping/set ordering."""
    if isinstance(payload, AssignmentFingerprintInput):
        semantic_fields = {
            field_info.name: getattr(payload, field_info.name)
            for field_info in fields(payload)
            if field_info.name != "history_version"
        }
        canonical = _canonicalize(semantic_fields)
    else:
        canonical = _canonicalize(payload)
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_history_compatibility(
    history: SpecialistHistory,
    *,
    specialist_scope_id: str,
    case_snapshot_id: str,
    board_version: str,
    history_version: str,
) -> tuple[str, ...]:
    """Return version/scope mismatches; any returned item should fail closed."""
    mismatches: list[str] = []
    expected = {
        "specialist_scope_id": (history.specialist_scope_id, specialist_scope_id),
        "case_snapshot_id": (history.case_snapshot_id, case_snapshot_id),
        "board_version": (history.board_version, board_version),
        "history_version": (history.history_version, history_version),
    }
    for name, (actual, supplied) in expected.items():
        if actual != supplied:
            mismatches.append(f"{name}: history has {actual!r}, assignment has {supplied!r}")
    return tuple(mismatches)


@dataclass(frozen=True, slots=True)
class RunRecord:
    assignment_id: str
    input_fingerprint: str
    result_reference: str
    run_status: str
    reusable: bool = True


class RunHistoryStore(Protocol):
    def find_by_assignment(self, assignment_id: str) -> Optional[RunRecord]: ...

    def find_by_fingerprint(self, input_fingerprint: str) -> Optional[RunRecord]: ...

    def record_completed(self, record: RunRecord) -> None: ...


class InMemoryRunHistoryStore:
    """Thread-safe test/default store; production should adapt durable storage."""

    def __init__(self) -> None:
        self._by_assignment: dict[str, RunRecord] = {}
        self._by_fingerprint: dict[str, RunRecord] = {}
        self._lock = threading.RLock()

    def find_by_assignment(self, assignment_id: str) -> Optional[RunRecord]:
        with self._lock:
            return self._by_assignment.get(assignment_id)

    def find_by_fingerprint(self, input_fingerprint: str) -> Optional[RunRecord]:
        with self._lock:
            record = self._by_fingerprint.get(input_fingerprint)
            return record if record and record.reusable else None

    def record_completed(self, record: RunRecord) -> None:
        if not record.assignment_id or not record.input_fingerprint:
            raise ValueError("completed run needs assignment ID and fingerprint")
        if not record.result_reference:
            raise ValueError("completed run needs a result reference")
        with self._lock:
            existing = self._by_assignment.get(record.assignment_id)
            if existing and existing.input_fingerprint != record.input_fingerprint:
                raise ValueError("assignment_id already recorded with different input")
            self._by_assignment[record.assignment_id] = record
            if record.reusable:
                self._by_fingerprint[record.input_fingerprint] = record


class NoOpDecision(str, Enum):
    RUN = "run"
    NO_OP = "no_op"
    ASSIGNMENT_ID_CONFLICT = "assignment_id_conflict"


@dataclass(frozen=True, slots=True)
class NoOpResult:
    decision: NoOpDecision
    prior_result_reference: Optional[str] = None
    prior_assignment_id: Optional[str] = None
    reason: str = ""


def detect_no_op(
    *,
    assignment_id: str,
    input_fingerprint: str,
    store: RunHistoryStore,
) -> NoOpResult:
    """Detect exact retries and semantically identical completed assignments.

    A reused assignment ID with changed content is a conflict, not a cache hit.
    Only records marked reusable are eligible; callers should not cache failed,
    stale, or partial generation errors as completed semantic work.
    """
    by_id = store.find_by_assignment(assignment_id)
    if by_id:
        if by_id.input_fingerprint != input_fingerprint:
            return NoOpResult(
                NoOpDecision.ASSIGNMENT_ID_CONFLICT,
                reason="assignment_id was already used with a different input fingerprint",
            )
        if by_id.reusable:
            return NoOpResult(
                NoOpDecision.NO_OP,
                prior_result_reference=by_id.result_reference,
                prior_assignment_id=by_id.assignment_id,
                reason="this exact assignment has already completed",
            )

    equivalent = store.find_by_fingerprint(input_fingerprint)
    if equivalent:
        return NoOpResult(
            NoOpDecision.NO_OP,
            prior_result_reference=equivalent.result_reference,
            prior_assignment_id=equivalent.assignment_id,
            reason="an identical semantic assignment has already completed",
        )
    return NoOpResult(NoOpDecision.RUN, reason="no reusable result matches this input")

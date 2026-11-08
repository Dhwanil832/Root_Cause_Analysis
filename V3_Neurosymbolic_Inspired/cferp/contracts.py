"""Typed contracts for CFERP, the case-level Lead orchestrator.

The package intentionally does not implement Specialist, Evidence Worker, or
Assessor reasoning. Those systems return versioned proposals; CFERP owns the
case ledgers and decides how those proposals enter the investigation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    SPECIALIST = "specialist"
    EVIDENCE_WORKER = "evidence_worker"
    ASSESSOR = "assessor"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETURNED = "returned"
    AWAITING_ASSESSOR = "awaiting_assessor"
    NEEDS_REVISION = "needs_revision"
    WAITING_EXTERNAL = "waiting_external"
    STALE = "stale"
    SUPERSEDED = "superseded"
    COMPLETE = "complete"
    FAILED = "failed"


class NeedState(StrEnum):
    OPEN = "open"
    PARTIALLY_RESOLVED = "partially_resolved"
    RESOLVED_BY_MATERIAL = "resolved_by_material"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SlotState(StrEnum):
    OPEN = "open"
    IN_PROCESS = "in_process"
    RESOLVED_BY_MATERIAL = "resolved_by_material"
    ANSWERED = "answered"
    DECLINED = "declined"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class RequestDisposition(StrEnum):
    PROPOSED = "proposed"
    ASSESSOR_REVIEW = "assessor_review"
    REVISION = "revision"
    REJECTED = "rejected"
    APPROVED = "approved"
    READY_TO_SEND = "ready_to_send"
    DISPATCH_PENDING = "dispatch_pending"
    SENT = "sent"
    WITHDRAWAL_PENDING = "withdrawal_pending"
    WITHDRAWN = "withdrawn"
    DISPATCH_FAILED = "dispatch_failed"
    WAITING_RESPONSE = "waiting_response"
    PARTIALLY_ANSWERED = "partially_answered"
    ANSWERED = "answered"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class VersionManifest:
    case_id: str
    case_snapshot_id: str
    board_version: int
    material_index_version: str
    source_versions: tuple[tuple[str, str, str], ...] = ()  # id, version, hash


@dataclass(frozen=True, slots=True)
class InformationSlot:
    slot_id: str
    description: str
    entity_id: str | None = None
    time_scope: str | None = None
    record_type: str | None = None
    required_fields: tuple[str, ...] = ()
    state: SlotState = SlotState.OPEN
    resolution_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Need:
    need_id: str
    origin_kind: str
    origin_id: str
    target_ids: tuple[str, ...]
    slots: tuple[InformationSlot, ...]
    state: NeedState = NeedState.OPEN
    source_scope: tuple[str, ...] = ()
    version: int = 1


@dataclass(frozen=True, slots=True)
class EvidencePacket:
    """EW search result that may be reviewed by an Assessor.

    `covered_slot_ids` is explicit so packet reuse cannot rely on topic-level
    similarity. Material/source versions are retained as immutable references.
    """
    packet_id: str
    request_id: str
    target_ids: tuple[str, ...]
    covered_slot_ids: tuple[str, ...]
    source_scope: tuple[str, ...]
    entity_ids: tuple[str, ...]
    time_scope: str | None
    record_types: tuple[str, ...]
    source_versions: tuple[tuple[str, str, str], ...]
    searched_material_index_version: str
    result_payload: Any
    parent_packet_id: str | None = None
    slot_payloads: tuple[tuple[str, Any], ...] = ()
    is_partial_reuse: bool = False


@dataclass(frozen=True, slots=True)
class OutwardRequest:
    request_id: str
    origin_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    slot_ids: tuple[str, ...]
    wording: str
    request_kind: str  # question | document_request | other
    source_scope: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    time_scope: str | None = None
    record_types: tuple[str, ...] = ()
    source_versions: tuple[tuple[str, str, str], ...] = ()
    material_index_version: str = "materials:0"
    state: RequestDisposition = RequestDisposition.PROPOSED
    current_packet_id: str | None = None
    packet_history: tuple[str, ...] = ()
    request_version: int = 1
    latest_dispatch_sequence: int = 0
    last_acknowledged_send_sequence: int = 0
    last_acknowledged_withdrawal_sequence: int = 0
    acknowledged_sent_ids: tuple[int, ...] = ()
    acknowledged_withdrawn_send_ids: tuple[int, ...] = ()
    withdrawal_required_send_ids: tuple[int, ...] = ()
    idempotency_keys: tuple[str, ...] = ()
    response_material_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkItem:
    work_id: str
    role: Role
    owner_id: str
    target_ids: tuple[str, ...]
    need_ids: tuple[str, ...]
    state: JobState
    priority_tier: int
    created_sequence: int
    estimated_cost: int = 1
    dependency_ids: tuple[str, ...] = ()
    manifest: VersionManifest | None = None
    result_ref: str | None = None
    stale_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DispatchAction:
    action_id: str
    request_id: str
    sequence: int
    action: str  # send | withdraw
    idempotency_key: str
    target_send_sequence: int | None = None


@dataclass(frozen=True, slots=True)
class LeadEvent:
    event_id: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0


@dataclass(frozen=True, slots=True)
class CandidateAction:
    action_id: str
    role: Role
    target_ids: tuple[str, ...]
    need_ids: tuple[str, ...] = ()
    priority_tier: int = 3
    cost: int = 1
    dependency_ids: tuple[str, ...] = ()
    created_sequence: int = 0
    manifest: VersionManifest | None = None

"""Standalone, versioned contracts for HERA1 Assessor runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TaskKind = Literal["evidence_review", "clarification_review", "request_review", "reassessment_triage"]


@dataclass(frozen=True, slots=True)
class EvidenceMaterial:
    material_id: str
    source_id: str
    source_version: str
    representation_id: str
    text: str
    source_kind: str = "document"
    offset_base: int = 0
    location: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssessmentTask:
    schema_version: str
    task_id: str
    work_item_id: str
    event_id: str
    case_id: str
    case_snapshot_id: str
    board_version: str
    task_kind: TaskKind
    sender_role: str
    sender_id: str
    materials: tuple[EvidenceMaterial, ...] = ()
    hypothesis: dict[str, Any] | None = None
    clarification: dict[str, Any] | None = None
    answer: dict[str, Any] | None = None
    request: dict[str, Any] | None = None
    request_history: tuple[dict[str, Any], ...] = ()
    prior_assessment_ids: tuple[str, ...] = ()
    prior_answers: tuple[dict[str, Any], ...] = ()
    context: dict[str, Any] = field(default_factory=dict)
    revision_attempt: int = 0


@dataclass(frozen=True, slots=True)
class AssessmentRoute:
    """Lead-owned routing metadata joining selected Specialist/EW work."""
    task_id: str
    work_item_id: str
    event_id: str
    case_id: str
    case_snapshot_id: str
    board_version: str
    sender_role: str = "evidence_worker"
    sender_id: str = ""
    worker_id: str = ""
    specialist_assignment_id: str = ""
    # SAHS runs on the Lead snapshot it was assigned. The Lead may commit that
    # delta before EWV3 finishes, so HERA's current board version can be newer.
    specialist_case_snapshot_id: str = ""
    specialist_board_version: str = ""
    candidate_id: str = ""
    need_id: str = ""
    slot_ids: tuple[str, ...] = ()
    hypothesis_parts: tuple[dict[str, Any], ...] = ()
    clarification_id: str = ""
    request_id: str = ""
    target_id: str = ""
    target_description: str = ""
    open_gap: str = ""
    request_history: tuple[dict[str, Any], ...] = ()
    prior_assessment_ids: tuple[str, ...] = ()
    prior_answers: tuple[dict[str, Any], ...] = ()
    revision_attempt: int = 0


@dataclass(frozen=True, slots=True)
class VersionSnapshot:
    case_snapshot_id: str
    board_version: str
    material_versions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    schema_version: str
    task_id: str
    work_item_id: str
    event_id: str
    case_id: str
    case_snapshot_id: str
    board_version: str
    task_kind: str
    status: str
    destination_role: str
    destination_id: str | None = None
    notify_lead: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()
    model_calls: int = 0
    resource_usage: dict[str, Any] = field(default_factory=dict)

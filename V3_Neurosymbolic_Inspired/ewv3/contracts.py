"""Typed contracts for the standalone V3 Evidence Worker core.

The worker returns retrieval candidates and request drafts only. It never
produces evidence-impact judgments or mutates the investigation board.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Coverage(StrEnum):
    UNSEARCHED = "unsearched"
    CANDIDATE_FOUND = "candidate_found"
    NO_MATCH_IN_SCOPE = "no_match_in_searched_scope"
    PARTIAL = "partial_search"
    NOT_SEARCHABLE = "source_not_searchable"
    AMBIGUOUS = "ambiguous_candidates"
    BUDGET_EXHAUSTED = "budget_exhausted"
    BLOCKED = "blocked"


class SearchPassStatus(StrEnum):
    NOT_STARTED = "not_started"
    COMPLETE = "bounded_pass_complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class WorkPhase(StrEnum):
    OPEN = "open"
    BLOCKED = "blocked_for_lead"
    READY = "ready"
    RUNNING = "running"
    AWAITING_ASSESSOR = "awaiting_assessor"
    AWAITING_LEAD = "awaiting_lead_action"
    WAITING_EXTERNAL = "waiting_external"
    RESUMABLE = "resumable"
    HELD = "held_for_reconciliation"
    CLOSED = "closed_by_lead"
    CANCELED = "canceled_by_lead"


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    corpus_snapshot_id: str
    material_catalog_version: str
    representation_version: str
    completeness_status: str = "registered_scope_only"
    completeness_basis: str = ""
    expected_source_ids: tuple[str, ...] = ()
    failed_source_ids: tuple[str, ...] = ()
    pending_source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceRepresentation:
    """Searchable rendition of one source (text, table text, OCR, etc.)."""
    representation_id: str
    modality: str
    text: str
    structural_context: dict[str, Any] = field(default_factory=dict)
    content_ref: str | None = None
    searchable: bool = True
    readiness: str = "ready"


@dataclass(frozen=True, slots=True)
class SourceUnit:
    source_id: str
    source_version: str
    representation_id: str
    title: str
    text: str
    source_kind: str = "case_document"
    searchable: bool = True
    readiness: str = "ready"
    origin: str = ""
    lineage: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)
    representations: tuple[SourceRepresentation, ...] = ()


@dataclass(frozen=True, slots=True)
class AnswerSlot:
    slot_id: str
    description: str
    slot_kind: str = "incident_information"
    exact_constraints: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    time_scope: str = ""
    requested_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonSpec:
    """Lead-defined alternatives to retrieve in parallel for one comparison."""
    comparison_id: str
    comparison_dimension: str
    slot_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InformationNeed:
    need_id: str
    target_claim: str
    slots: tuple[AnswerSlot, ...]
    search_objective: str = "candidate_retrieval"
    branch_id: str = ""
    comparisons: tuple[ComparisonSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateLink:
    candidate_link_id: str
    need_id: str
    slot_id: str
    source_id: str
    source_version: str
    representation_id: str
    start_offset: int | None
    end_offset: int | None
    exact_text: str
    title: str
    source_kind: str
    channel: str
    score: float
    matched_facets: tuple[str, ...] = ()
    mismatched_facets: tuple[str, ...] = ()
    matched_topic_terms: tuple[str, ...] = ()
    missing_topic_terms: tuple[str, ...] = ()
    uncertain_facets: tuple[str, ...] = ()
    structural_context: dict[str, Any] = field(default_factory=dict)
    lineage: str = "unknown"
    ocr_confidence: float | None = None
    potential_conflict_flag: bool = False
    modality: str = "text"
    retrieval_channels: tuple[str, ...] = ()
    score_semantics: str = "retrieval_rank_only"


@dataclass(frozen=True, slots=True)
class RequestDraft:
    request_id: str
    request_type: str
    slot_ids: tuple[str, ...]
    question_or_document: str
    entity_scope: tuple[str, ...] = ()
    time_scope: str = ""
    requested_fields: tuple[str, ...] = ()
    why_it_may_help: str = ""
    searched_scope: tuple[str, ...] = ()
    limits: tuple[str, ...] = ()
    parent_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class SlotResult:
    need_id: str
    slot_id: str
    coverage: Coverage
    candidate_links: tuple[CandidateLink, ...] = ()
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ComparisonSideResult:
    slot_id: str
    retrieval_coverage: str
    candidate_link_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Retrieval coverage by assigned alternative; never an evidence verdict."""
    comparison_id: str
    need_id: str
    comparison_dimension: str
    sides: tuple[ComparisonSideResult, ...]
    status: str


@dataclass(frozen=True, slots=True)
class SearchTrace:
    need_id: str
    slot_id: str
    corpus_snapshot_id: str
    material_catalog_version: str
    representation_version: str
    channel: str
    query: str
    source_ids_searched: tuple[str, ...]
    returned_source_ids: tuple[str, ...]
    stop_reason: str
    retrieval_version: str
    pass_number: int = 1
    query_origin: str = "initial"
    returned_hit_count: int = 0
    backend_count: int = 1
    backend_versions: tuple[str, ...] = ()
    reranker_version: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceAssignment:
    schema_version: str
    assignment_id: str
    work_item_id: str
    event_id: str
    case_id: str
    case_snapshot_id: str
    board_version: str
    manifest: CorpusManifest
    needs: tuple[InformationNeed, ...]
    sources: tuple[SourceUnit, ...]
    allowed_source_ids: tuple[str, ...] = ()
    pending_request_ids: tuple[str, ...] = ()
    pending_requests: tuple[RequestDraft, ...] = ()
    prior_attempt_ids: tuple[str, ...] = ()
    prior_search_traces: tuple[SearchTrace, ...] = ()
    prior_candidate_links: tuple[CandidateLink, ...] = ()
    reassessment_ids: tuple[str, ...] = ()
    changed_representation_ids: tuple[str, ...] = ()
    assessor_feedback: tuple[dict[str, Any], ...] = ()
    budgets: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceWorkerResult:
    schema_version: str
    assignment_id: str
    work_item_id: str
    event_id: str
    case_snapshot_id: str
    board_version: str
    corpus_snapshot_id: str
    material_catalog_version: str
    representation_version: str
    status: str
    work_phase: WorkPhase
    search_pass_status: SearchPassStatus
    slot_results: tuple[SlotResult, ...] = ()
    comparison_results: tuple[ComparisonResult, ...] = ()
    preserved_candidate_links: tuple[CandidateLink, ...] = ()
    request_drafts: tuple[RequestDraft, ...] = ()
    unassigned_context_links: tuple[CandidateLink, ...] = ()
    traces: tuple[SearchTrace, ...] = ()
    diagnostics: tuple[str, ...] = ()
    resource_usage: dict[str, Any] = field(default_factory=dict)

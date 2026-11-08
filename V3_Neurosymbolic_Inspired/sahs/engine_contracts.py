"""Typed inputs and outputs for the proposal/validation/ASP Specialist core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .contracts import SpecialistHistory


@dataclass(frozen=True, slots=True)
class SourceChunk:
    source_id: str
    source_version: str
    chunk_id: str
    text: str
    source_kind: str = "case_document"


@dataclass(frozen=True, slots=True)
class SourceReference:
    source_id: str
    source_version: str
    chunk_id: str
    exact_text: str
    start_offset: int
    end_offset: int
    source_kind: str
    source_relation: str


@dataclass(frozen=True, slots=True)
class Proposition:
    proposition_id: str
    text: str
    kind: str
    case_status: str
    source_refs: tuple[SourceReference, ...] = ()
    time_scope: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CausalRuleCandidate:
    rule_id: str
    antecedent_ids: tuple[str, ...]
    consequent_id: str
    relation: str
    modality: str
    conditions: tuple[str, ...] = ()
    time_constraint: Optional[str] = None
    basis: str = "model_proposed"
    source_refs: tuple[SourceReference, ...] = ()
    source_relation: Optional[str] = None
    status: str = "candidate"


@dataclass(frozen=True, slots=True)
class CausalGraph:
    propositions: tuple[Proposition, ...] = ()
    rules: tuple[CausalRuleCandidate, ...] = ()

    def proposition_map(self) -> dict[str, Proposition]:
        return {item.proposition_id: item for item in self.propositions}

    def rule_map(self) -> dict[str, CausalRuleCandidate]:
        return {item.rule_id: item for item in self.rules}


@dataclass(frozen=True, slots=True)
class SpecialistAssignment:
    schema_version: str
    assignment_id: str
    case_id: str
    specialist_scope_id: str
    case_snapshot_id: str
    board_version: str
    history_version: str
    mode: str
    operation_goal: str
    lead_direction: Any
    relevant_graph: CausalGraph
    source_bundle: tuple[SourceChunk, ...]
    history: SpecialistHistory
    focal_proposition_id: Optional[str] = None
    target_proposition_ids: tuple[str, ...] = ()
    available_proposition_ids: tuple[str, ...] = ()
    initial_case_packet: Any = None
    lead_feedback: tuple[Any, ...] = ()
    assessor_annotations: tuple[Any, ...] = ()
    changed_ids: tuple[str, ...] = ()
    explicitly_targeted_candidate_ids: tuple[str, ...] = ()
    vetted_domain_rules: tuple[CausalRuleCandidate, ...] = ()
    budgets: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClarificationItem:
    clarification_id: str
    question: str
    why_it_matters: str
    linked_proposition_ids: tuple[str, ...] = ()
    linked_rule_ids: tuple[str, ...] = ()
    linked_candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InformationGap:
    need_id: str
    unknown: str
    why_it_matters: str
    information_that_could_resolve_it: str
    linked_proposition_ids: tuple[str, ...] = ()
    linked_rule_ids: tuple[str, ...] = ()
    linked_candidate_ids: tuple[str, ...] = ()
    linked_frontier_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateExplanation:
    candidate_id: str
    target_proposition_id: str
    proposition_ids: tuple[str, ...]
    rule_ids: tuple[str, ...]
    reported_premise_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    source_refs: tuple[SourceReference, ...]
    solver_trace: tuple[str, ...]
    candidate_fingerprint: str


@dataclass(frozen=True, slots=True)
class OpenFrontier:
    proposition_id: str
    reason: str
    linked_candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RejectedFragment:
    fragment_type: str
    fragment_id: Optional[str]
    reason: str


@dataclass(frozen=True, slots=True)
class SpecialistResult:
    schema_version: str
    assignment_id: str
    case_snapshot_id: str
    board_version: str
    history_version: str
    input_fingerprint: str
    status: str
    graph_delta: CausalGraph = field(default_factory=CausalGraph)
    candidate_operations: tuple[Any, ...] = ()
    candidates: tuple[CandidateExplanation, ...] = ()
    unchanged_candidate_refs: tuple[str, ...] = ()
    rejected_fragments: tuple[RejectedFragment, ...] = ()
    clarification_items: tuple[ClarificationItem, ...] = ()
    information_gaps: tuple[InformationGap, ...] = ()
    open_frontier: tuple[OpenFrontier, ...] = ()
    solver_trace: tuple[Any, ...] = ()
    validation_warnings: tuple[str, ...] = ()
    resource_usage: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()
    prior_result_reference: Optional[str] = None
    prior_assignment_id: Optional[str] = None
    updated_history: Optional[SpecialistHistory] = None

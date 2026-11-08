"""Stateful Abductive Hypothesis Search Specialist components."""

__version__ = "0.3.0"

from .contracts import (
    CandidateLineage,
    CandidateOperation,
    CandidateStatus,
    FrontierAction,
    FrontierHistory,
    InformationNeedStatus,
    InformationNeedHistory,
    SpecialistHistory,
)
from .delta import (
    CandidateProposal,
    CandidateDelta,
    fingerprint_candidate_graph,
    build_candidate_delta,
    compute_affected_candidates,
    select_focal_candidates,
    missing_affected_dispositions,
    apply_candidate_delta,
    transition_candidate,
)
from .history import (
    AssignmentFingerprintInput,
    InMemoryRunHistoryStore,
    NoOpDecision,
    RunRecord,
    compute_input_fingerprint,
    detect_no_op,
    validate_history_compatibility,
)
from .state_controller import (
    PreparationStatus,
    RunPreparation,
    prepare_run,
    record_run_result,
)
from .workflow import (
    decide_frontier_action,
    merge_information_needs,
    record_frontier_attempt,
    transition_information_need,
)
from .engine import SpecialistEngine
from .engine_contracts import (
    CausalGraph,
    CausalRuleCandidate,
    Proposition,
    SourceChunk,
    SpecialistAssignment,
    SpecialistResult,
)
from .archive_adapter import ArchiveSpecialistAdapter
from .solver import ClingoCandidateSolver, ClingoUnavailableError

__all__ = [
    "AssignmentFingerprintInput",
    "CandidateDelta",
    "fingerprint_candidate_graph",
    "CandidateLineage",
    "CandidateOperation",
    "CandidateProposal",
    "CandidateStatus",
    "FrontierAction",
    "FrontierHistory",
    "InformationNeedHistory",
    "InformationNeedStatus",
    "InMemoryRunHistoryStore",
    "NoOpDecision",
    "PreparationStatus",
    "RunRecord",
    "RunPreparation",
    "SpecialistHistory",
    "apply_candidate_delta",
    "transition_candidate",
    "build_candidate_delta",
    "compute_affected_candidates",
    "select_focal_candidates",
    "missing_affected_dispositions",
    "compute_input_fingerprint",
    "detect_no_op",
    "prepare_run",
    "record_run_result",
    "validate_history_compatibility",
    "decide_frontier_action",
    "merge_information_needs",
    "record_frontier_attempt",
    "transition_information_need",
    "ArchiveSpecialistAdapter",
    "CausalGraph",
    "CausalRuleCandidate",
    "ClingoCandidateSolver",
    "ClingoUnavailableError",
    "Proposition",
    "SourceChunk",
    "SpecialistAssignment",
    "SpecialistEngine",
    "SpecialistResult",
]

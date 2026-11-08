"""Versioned, immutable history records used by SAHS state management.

These records describe Specialist workflow state only. They are not evidence
verdicts and must not be used as a substitute for the shared investigation
board maintained by the Lead.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class CandidateOperation(StrEnum):
    CREATE = "create"
    REVISE = "revise"
    SUPERSEDE = "supersede"
    REOPEN = "reopen"
    UNCHANGED = "unchanged"
    PARK = "park"
    MERGE = "merge"


class CandidateStatus(StrEnum):
    ACTIVE = "active"
    PARKED = "parked"
    SUPERSEDED = "superseded"


class FrontierAction(StrEnum):
    WAIT = "wait"
    EXPAND = "expand"
    DEFER = "defer"
    PARK = "park"
    REOPEN = "reopen"
    REOPEN_AND_EXPAND = "reopen_and_expand"


class InformationNeedStatus(StrEnum):
    PROPOSED = "proposed"
    PENDING = "pending"
    ANSWERED = "answered"
    CLOSED = "closed"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class CandidateLineage:
    candidate_id: str
    parent_candidate_ids: tuple[str, ...] = ()
    revision: int = 1
    dependent_proposition_ids: frozenset[str] = frozenset()
    dependent_rule_ids: frozenset[str] = frozenset()
    assumption_ids: frozenset[str] = frozenset()
    dependent_annotation_ids: frozenset[str] = frozenset()
    dependent_source_ids: frozenset[str] = frozenset()
    dependent_information_need_ids: frozenset[str] = frozenset()
    dependent_clarification_ids: frozenset[str] = frozenset()
    status: CandidateStatus = CandidateStatus.ACTIVE
    last_operation: CandidateOperation = CandidateOperation.CREATE
    content_fingerprint: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty")
        if self.revision < 1:
            raise ValueError("revision must be at least 1")
        if self.candidate_id in self.parent_candidate_ids:
            raise ValueError("candidate cannot be its own parent")

    @property
    def dependency_ids(self) -> frozenset[str]:
        return (
            self.dependent_proposition_ids
            | self.dependent_rule_ids
            | self.assumption_ids
            | self.dependent_annotation_ids
            | self.dependent_source_ids
            | self.dependent_information_need_ids
            | self.dependent_clarification_ids
        )


@dataclass(frozen=True, slots=True)
class FrontierHistory:
    frontier_id: str
    target_proposition_id: str
    candidate_ids: tuple[str, ...] = ()
    expanded_before: bool = False
    last_attempt_id: Optional[str] = None
    last_attempt_outcome: Optional[str] = None
    dependency_ids: frozenset[str] = frozenset()
    linked_need_ids: tuple[str, ...] = ()
    last_direction_fingerprint: Optional[str] = None
    attempted_direction_fingerprints: tuple[str, ...] = ()
    workflow_status: str = "open"


@dataclass(frozen=True, slots=True)
class InformationNeedHistory:
    need_id: str
    linked_candidate_ids: tuple[str, ...] = ()
    linked_frontier_ids: tuple[str, ...] = ()
    target_unknown_id: Optional[str] = None
    material_or_request_ids: tuple[str, ...] = ()
    workflow_status: str = "proposed"
    last_changed_version: Optional[str] = None
    meaning_fingerprint: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SpecialistHistory:
    schema_version: str
    specialist_scope_id: str
    history_version: str
    case_snapshot_id: str
    board_version: str
    candidates: tuple[CandidateLineage, ...] = ()
    frontiers: tuple[FrontierHistory, ...] = ()
    information_needs: tuple[InformationNeedHistory, ...] = ()
    prior_expansion_budget_usage: int = 0

    def __post_init__(self) -> None:
        if not self.specialist_scope_id.strip():
            raise ValueError("specialist_scope_id must be non-empty")
        if self.prior_expansion_budget_usage < 0:
            raise ValueError("prior_expansion_budget_usage cannot be negative")
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate IDs in history must be unique")
        known = set(candidate_ids)
        for candidate in self.candidates:
            missing = set(candidate.parent_candidate_ids) - known
            if missing:
                raise ValueError(
                    f"candidate {candidate.candidate_id!r} has unknown parents: "
                    f"{sorted(missing)}"
                )
        frontier_ids = [frontier.frontier_id for frontier in self.frontiers]
        if len(frontier_ids) != len(set(frontier_ids)):
            raise ValueError("frontier IDs in history must be unique")
        need_ids = [need.need_id for need in self.information_needs]
        if len(need_ids) != len(set(need_ids)):
            raise ValueError("information-need IDs in history must be unique")

    def candidate_map(self) -> dict[str, CandidateLineage]:
        return {candidate.candidate_id: candidate for candidate in self.candidates}

"""Constrained optional Lead-planner port.

The planner can rank only Python-generated action IDs. It cannot create work,
change a priority tier, approve requests, assess evidence, or mutate the board.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import CandidateAction, VersionManifest


@dataclass(frozen=True, slots=True)
class PlannerRequest:
    manifest: VersionManifest
    actions: tuple[CandidateAction, ...]
    instruction: str = (
        "Order only the supplied action IDs. Python preserves priority tiers and age; "
        "your order breaks ties only among equally aged actions in the same tier."
    )


@dataclass(frozen=True, slots=True)
class PlannerResponse:
    ordered_action_ids: tuple[str, ...]
    case_snapshot_id: str
    board_version: int
    material_index_version: str


class LeadPlanner(Protocol):
    def rank_actions(self, request: PlannerRequest) -> PlannerResponse: ...


@dataclass(frozen=True, slots=True)
class PlannerDecision:
    rank_by_action_id: tuple[tuple[str, int], ...] = ()
    called: bool = False
    accepted: bool = False
    diagnostics: tuple[str, ...] = ()


def get_planner_decision(*, actions: tuple[CandidateAction, ...], manifest: VersionManifest,
                         planner: LeadPlanner | None, ambiguous: bool) -> PlannerDecision:
    """Call only on ambiguous choices and accept an exact ID permutation only."""
    if not ambiguous or planner is None or len(actions) < 2:
        return PlannerDecision()
    try:
        response = planner.rank_actions(PlannerRequest(manifest, actions))
    except Exception as exc:  # provider failures fall back to deterministic scheduling
        return PlannerDecision(called=True, diagnostics=(f"planner_failed:{type(exc).__name__}",))
    if (not isinstance(getattr(response, "ordered_action_ids", None), (tuple, list))
            or not all(isinstance(item, str) for item in response.ordered_action_ids)
            or not isinstance(getattr(response, "case_snapshot_id", None), str)
            or not isinstance(getattr(response, "board_version", None), int)
            or not isinstance(getattr(response, "material_index_version", None), str)):
        return PlannerDecision(called=True, diagnostics=("planner_malformed_response",))
    allowed = [action.action_id for action in actions]
    returned = list(response.ordered_action_ids)
    if (response.case_snapshot_id != manifest.case_snapshot_id
            or response.board_version != manifest.board_version
            or response.material_index_version != manifest.material_index_version):
        return PlannerDecision(called=True, diagnostics=("planner_response_stale",))
    if len(returned) != len(set(returned)):
        return PlannerDecision(called=True, diagnostics=("planner_returned_duplicate_action_ids",))
    if set(returned) != set(allowed):
        return PlannerDecision(called=True, diagnostics=("planner_must_return_exact_candidate_id_permutation",))
    return PlannerDecision(tuple((action_id, rank) for rank, action_id in enumerate(returned)),
                           called=True, accepted=True)

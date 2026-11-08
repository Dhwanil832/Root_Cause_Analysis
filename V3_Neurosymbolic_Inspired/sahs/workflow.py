"""Frontier and information-need state transitions for repeated SAHS runs."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .contracts import (
    FrontierAction,
    FrontierHistory,
    InformationNeedHistory,
    InformationNeedStatus,
    SpecialistHistory,
)


def decide_frontier_action(
    frontier: FrontierHistory,
    *,
    direction_fingerprint: str,
    changed_ids: Iterable[str] = (),
    pending_information_need_ids: Iterable[str] = (),
    expansion_budget_remaining: int,
    lead_authorized: bool,
) -> FrontierAction:
    """Choose whether a recorded frontier waits, reopens, expands, or defers."""
    if expansion_budget_remaining < 0:
        raise ValueError("expansion_budget_remaining cannot be negative")
    changed = set(changed_ids)
    frontier_changed = (
        frontier.target_proposition_id in changed
        or bool(frontier.dependency_ids & changed)
    )
    if frontier_changed:
        if lead_authorized and expansion_budget_remaining > 0:
            return FrontierAction.REOPEN_AND_EXPAND
        return FrontierAction.REOPEN

    pending = set(pending_information_need_ids)
    if pending & set(frontier.linked_need_ids):
        return FrontierAction.WAIT

    attempted = set(frontier.attempted_direction_fingerprints)
    if frontier.last_direction_fingerprint:
        attempted.add(frontier.last_direction_fingerprint)
    if frontier.expanded_before and direction_fingerprint in attempted:
        return FrontierAction.WAIT
    if not lead_authorized:
        return FrontierAction.DEFER
    if expansion_budget_remaining == 0:
        return FrontierAction.DEFER
    return FrontierAction.EXPAND


def record_frontier_attempt(
    history: SpecialistHistory,
    *,
    frontier_id: str,
    target_proposition_id: str,
    candidate_ids: Iterable[str],
    direction_fingerprint: str,
    assignment_id: str,
    outcome: str,
    dependency_ids: Iterable[str] = (),
    linked_need_ids: Iterable[str] = (),
    expansion_calls_used: int,
    new_history_version: str,
) -> SpecialistHistory:
    """Record a completed frontier action and cumulative expansion use."""
    if expansion_calls_used < 0:
        raise ValueError("expansion_calls_used cannot be negative")
    frontiers = {item.frontier_id: item for item in history.frontiers}
    previous = frontiers.get(frontier_id)
    if previous and previous.target_proposition_id != target_proposition_id:
        raise ValueError("frontier_id cannot be reused for a different target")
    completed_search = outcome in {
        "expanded",
        "completed_with_expansion",
        "reopen_and_expand",
        "no_candidate_under_supplied_rules",
        "completed_without_expansion",
    }
    attempted_directions = set(previous.attempted_direction_fingerprints if previous else ())
    if previous and previous.last_direction_fingerprint:
        attempted_directions.add(previous.last_direction_fingerprint)
    if completed_search or expansion_calls_used > 0:
        attempted_directions.add(direction_fingerprint)
    prior_linked_needs = set(previous.linked_need_ids if previous else ())
    frontiers[frontier_id] = FrontierHistory(
        frontier_id=frontier_id,
        target_proposition_id=target_proposition_id,
        candidate_ids=tuple(sorted(set(candidate_ids))),
        expanded_before=(previous.expanded_before if previous else False)
        or completed_search
        or expansion_calls_used > 0,
        last_attempt_id=assignment_id,
        last_attempt_outcome=outcome,
        dependency_ids=frozenset(dependency_ids),
        linked_need_ids=tuple(sorted(prior_linked_needs | set(linked_need_ids))),
        last_direction_fingerprint=direction_fingerprint,
        attempted_direction_fingerprints=tuple(sorted(attempted_directions)),
        workflow_status=outcome,
    )
    return replace(
        history,
        history_version=new_history_version,
        frontiers=tuple(sorted(frontiers.values(), key=lambda item: item.frontier_id)),
        prior_expansion_budget_usage=(
            history.prior_expansion_budget_usage + expansion_calls_used
        ),
    )


def merge_information_needs(
    history: SpecialistHistory,
    proposed_needs: Iterable[InformationNeedHistory],
    *,
    new_history_version: str,
) -> SpecialistHistory:
    """Deduplicate open information needs by Python-generated meaning hash."""
    records = {item.need_id: item for item in history.information_needs}
    open_statuses = {
        InformationNeedStatus.PROPOSED.value,
        InformationNeedStatus.PENDING.value,
    }
    by_meaning = {
        item.meaning_fingerprint: item
        for item in records.values()
        if item.meaning_fingerprint and item.workflow_status in open_statuses
    }
    for proposed in proposed_needs:
        if not proposed.need_id.strip():
            raise ValueError("information need must have a non-empty ID")
        if not proposed.meaning_fingerprint:
            raise ValueError("information need must have a Python-generated meaning fingerprint")
        existing_id = records.get(proposed.need_id)
        if existing_id and existing_id.meaning_fingerprint != proposed.meaning_fingerprint:
            raise ValueError("information-need ID reused for different meaning")
        existing = by_meaning.get(proposed.meaning_fingerprint)
        if existing:
            merged = replace(
                existing,
                linked_candidate_ids=tuple(sorted(set(existing.linked_candidate_ids)
                                                  | set(proposed.linked_candidate_ids))),
                linked_frontier_ids=tuple(sorted(set(existing.linked_frontier_ids)
                                                 | set(proposed.linked_frontier_ids))),
                material_or_request_ids=tuple(sorted(set(existing.material_or_request_ids)
                                                     | set(proposed.material_or_request_ids))),
            )
            records[existing.need_id] = merged
            by_meaning[proposed.meaning_fingerprint] = merged
            continue
        # An answered/closed need with the same meaning is retained as history;
        # it is not silently reissued unless a new, explicit need ID/meaning is
        # proposed after the investigation state changes.
        if any(item.meaning_fingerprint == proposed.meaning_fingerprint
               for item in records.values()):
            continue
        records[proposed.need_id] = proposed
        if proposed.workflow_status in open_statuses:
            by_meaning[proposed.meaning_fingerprint] = proposed
    return replace(
        history,
        history_version=new_history_version,
        information_needs=tuple(sorted(records.values(), key=lambda item: item.need_id)),
    )


def transition_information_need(
    history: SpecialistHistory,
    *,
    need_id: str,
    new_status: InformationNeedStatus,
    new_history_version: str,
    explicit_reopen: bool = False,
    material_or_request_ids: Iterable[str] = (),
) -> SpecialistHistory:
    """Apply an explicit workflow transition to an existing information need."""
    records = {item.need_id: item for item in history.information_needs}
    current = records.get(need_id)
    if current is None:
        raise ValueError(f"unknown information need {need_id!r}")
    allowed = {
        InformationNeedStatus.PROPOSED: {
            InformationNeedStatus.PENDING,
            InformationNeedStatus.ANSWERED,
            InformationNeedStatus.CLOSED,
            InformationNeedStatus.SUPERSEDED,
        },
        InformationNeedStatus.PENDING: {
            InformationNeedStatus.ANSWERED,
            InformationNeedStatus.CLOSED,
            InformationNeedStatus.SUPERSEDED,
        },
        InformationNeedStatus.ANSWERED: {
            InformationNeedStatus.CLOSED,
            InformationNeedStatus.SUPERSEDED,
        },
        InformationNeedStatus.CLOSED: {InformationNeedStatus.PROPOSED},
        InformationNeedStatus.SUPERSEDED: {InformationNeedStatus.PROPOSED},
    }
    current_status = InformationNeedStatus(current.workflow_status)
    if new_status not in allowed[current_status]:
        raise ValueError(f"invalid information-need transition: {current_status} -> {new_status}")
    if current_status in {InformationNeedStatus.CLOSED, InformationNeedStatus.SUPERSEDED} and not explicit_reopen:
        raise ValueError("reopening a closed/superseded need requires explicit_reopen=True")
    records[need_id] = replace(
        current,
        workflow_status=new_status.value,
        material_or_request_ids=tuple(sorted(set(current.material_or_request_ids)
                                             | set(material_or_request_ids))),
        last_changed_version=new_history_version,
    )
    return replace(
        history,
        history_version=new_history_version,
        information_needs=tuple(sorted(records.values(), key=lambda item: item.need_id)),
    )

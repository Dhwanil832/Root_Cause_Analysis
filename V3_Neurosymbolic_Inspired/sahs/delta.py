"""Affected-branch calculation and immutable candidate-delta construction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Iterable, Optional

from .contracts import (
    CandidateLineage,
    CandidateOperation,
    CandidateStatus,
    SpecialistHistory,
)
from .history import compute_input_fingerprint


@dataclass(frozen=True, slots=True)
class CandidateProposal:
    """Validated candidate proposal after LLM schema/provenance checks."""

    content_fingerprint: str
    dependent_proposition_ids: frozenset[str] = frozenset()
    dependent_rule_ids: frozenset[str] = frozenset()
    assumption_ids: frozenset[str] = frozenset()
    dependent_annotation_ids: frozenset[str] = frozenset()
    dependent_source_ids: frozenset[str] = frozenset()
    dependent_information_need_ids: frozenset[str] = frozenset()
    dependent_clarification_ids: frozenset[str] = frozenset()
    parent_candidate_ids: tuple[str, ...] = ()
    revises_candidate_id: Optional[str] = None
    reopens_candidate_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CandidateDelta:
    operation: CandidateOperation
    candidate: CandidateLineage
    revised_from_candidate_id: Optional[str] = None
    invalidated_by_ids: tuple[str, ...] = ()
    reason_code: str = ""


def fingerprint_candidate_graph(
    *,
    propositions: object,
    rules: object,
    assumptions: object,
    source_refs: object,
) -> str:
    """Hash a validated candidate graph in Python, never from an LLM hash field."""
    return compute_input_fingerprint(
        {
            "propositions": propositions,
            "rules": rules,
            "assumptions": assumptions,
            "source_refs": source_refs,
        }
    )


def transition_candidate(
    history: SpecialistHistory,
    candidate_id: str,
    operation: CandidateOperation,
    *,
    reason_code: str,
    invalidated_by_ids: Iterable[str] = (),
) -> CandidateDelta:
    """Build a Python-authored park/supersede transition for an existing node."""
    if operation not in (CandidateOperation.PARK, CandidateOperation.SUPERSEDE):
        raise ValueError("status transition must be park or supersede")
    candidate = history.candidate_map().get(candidate_id)
    if candidate is None:
        raise ValueError(f"unknown candidate {candidate_id!r}")
    if candidate.status != CandidateStatus.ACTIVE:
        raise ValueError("only an active candidate can be parked or superseded")
    return CandidateDelta(
        operation=operation,
        candidate=candidate,
        invalidated_by_ids=tuple(sorted(set(invalidated_by_ids))),
        reason_code=reason_code,
    )


def compute_affected_candidates(
    history: SpecialistHistory,
    changed_ids: Iterable[str],
    explicitly_targeted_candidate_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return changed-dependent candidates plus descendants, deterministically.

    Dependencies include proposition, rule, and unresolved-assumption IDs.
    Descendants of an affected candidate are included because their lineage
    depends on that branch even if the changed leaf is not repeated locally.
    """
    changed = set(changed_ids)
    candidates = history.candidate_map()
    affected = set(explicitly_targeted_candidate_ids) & candidates.keys()
    affected.update(
        candidate_id
        for candidate_id, candidate in candidates.items()
        if candidate.dependency_ids & changed
    )

    changed_any = True
    while changed_any:
        before = len(affected)
        for candidate_id, candidate in candidates.items():
            if candidate_id not in affected and set(candidate.parent_candidate_ids) & affected:
                affected.add(candidate_id)
        changed_any = len(affected) != before

    return tuple(sorted(
        candidate_id
        for candidate_id in affected
        if (
            candidates[candidate_id].status != CandidateStatus.SUPERSEDED
            or candidate_id in set(explicitly_targeted_candidate_ids)
        )
    ))


def select_focal_candidates(
    history: SpecialistHistory,
    focal_proposition_id: str,
    explicitly_targeted_candidate_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    """Select candidate branches connected to an advance-mode focal node.

    This is task routing/selection, not a claim that those branches changed.
    The result is therefore kept separate from `affected_candidate_ids`.
    """
    if not focal_proposition_id:
        raise ValueError("advance mode requires a focal proposition ID")
    candidates = history.candidate_map()
    selected = {
        candidate_id
        for candidate_id, candidate in candidates.items()
        if focal_proposition_id in candidate.dependent_proposition_ids
    }
    changed = True
    while changed:
        previous_count = len(selected)
        for candidate_id, candidate in candidates.items():
            if candidate_id not in selected and set(candidate.parent_candidate_ids) & selected:
                selected.add(candidate_id)
        changed = len(selected) != previous_count
    explicitly_targeted = set(explicitly_targeted_candidate_ids)
    return tuple(sorted(
        candidate_id
        for candidate_id in selected
        if candidates[candidate_id].status == CandidateStatus.ACTIVE
        or candidate_id in explicitly_targeted
    ))


def missing_affected_dispositions(
    affected_candidate_ids: Iterable[str],
    deltas: Iterable[CandidateDelta],
) -> tuple[str, ...]:
    """List affected branches lacking an explicit output disposition.

    Call this before committing Specialist history. An affected branch must
    be revised/reopened, explicitly unchanged, or explicitly parked/superseded.
    Creating a child candidate alone does not silently disposition its parent.
    """
    covered: set[str] = set()
    for delta in deltas:
        if delta.operation in (CandidateOperation.REVISE, CandidateOperation.REOPEN):
            if delta.revised_from_candidate_id:
                covered.add(delta.revised_from_candidate_id)
        elif delta.operation in (
            CandidateOperation.UNCHANGED,
            CandidateOperation.MERGE,
            CandidateOperation.PARK,
            CandidateOperation.SUPERSEDE,
        ):
            covered.add(delta.candidate.candidate_id)
            if delta.operation == CandidateOperation.MERGE and delta.revised_from_candidate_id:
                covered.add(delta.revised_from_candidate_id)
    return tuple(sorted(set(affected_candidate_ids) - covered))


def _deterministic_candidate_id(
    assignment_id: str,
    proposal: CandidateProposal,
) -> str:
    parents = ",".join(sorted(proposal.parent_candidate_ids))
    target = proposal.revises_candidate_id or proposal.reopens_candidate_id or ""
    source = "|".join([assignment_id, proposal.content_fingerprint, parents, target])
    return "sahs-" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def build_candidate_delta(
    *,
    assignment_id: str,
    history: SpecialistHistory,
    proposals: Iterable[CandidateProposal],
    invalidated_by_ids: Iterable[str] = (),
) -> tuple[CandidateDelta, ...]:
    """Infer lifecycle operations in Python; proposals cannot set statuses.

    An identical active candidate becomes UNCHANGED. A changed proposal linked
    to an existing candidate becomes a new REVISE record and supersedes the
    prior revision. A proposal linked to an inactive candidate becomes REOPEN.
    Otherwise it creates a new candidate. IDs are deterministic within a run.
    """
    known = history.candidate_map()
    invalidators = tuple(sorted(set(invalidated_by_ids)))
    deltas: list[CandidateDelta] = []
    seen_content: set[tuple[str, tuple[str, ...], Optional[str]]] = set()
    for proposal in proposals:
        if not proposal.content_fingerprint.strip():
            raise ValueError("candidate proposal needs a content fingerprint")
        for parent_id in proposal.parent_candidate_ids:
            if parent_id not in known:
                raise ValueError(f"proposal references unknown parent {parent_id!r}")
        if proposal.revises_candidate_id and proposal.reopens_candidate_id:
            raise ValueError("proposal cannot both revise and reopen a candidate")

        target_id = proposal.revises_candidate_id or proposal.reopens_candidate_id
        if target_id and target_id not in known:
            raise ValueError(f"proposal targets unknown candidate {target_id!r}")

        proposal_key = (
            proposal.content_fingerprint,
            tuple(sorted(proposal.parent_candidate_ids)),
            target_id,
        )
        if proposal_key in seen_content:
            continue
        seen_content.add(proposal_key)

        if proposal.reopens_candidate_id:
            prior = known[proposal.reopens_candidate_id]
            if prior.status == CandidateStatus.ACTIVE:
                raise ValueError("only an inactive candidate can be reopened")
            if prior.content_fingerprint == proposal.content_fingerprint:
                reopened = replace(
                    prior,
                    parent_candidate_ids=tuple(dict.fromkeys((
                        *prior.parent_candidate_ids,
                        *proposal.parent_candidate_ids,
                    ))),
                    dependent_proposition_ids=proposal.dependent_proposition_ids,
                    dependent_rule_ids=proposal.dependent_rule_ids,
                    assumption_ids=proposal.assumption_ids,
                    dependent_annotation_ids=proposal.dependent_annotation_ids,
                    dependent_source_ids=proposal.dependent_source_ids,
                    dependent_information_need_ids=proposal.dependent_information_need_ids,
                    dependent_clarification_ids=proposal.dependent_clarification_ids,
                    status=CandidateStatus.ACTIVE,
                    last_operation=CandidateOperation.REOPEN,
                )
                deltas.append(
                    CandidateDelta(
                        CandidateOperation.REOPEN,
                        reopened,
                        revised_from_candidate_id=prior.candidate_id,
                        invalidated_by_ids=invalidators,
                        reason_code="reopen_unchanged_candidate",
                    )
                )
                continue

        matching_active = next(
            (
                candidate
                for candidate in known.values()
                if candidate.status == CandidateStatus.ACTIVE
                and candidate.content_fingerprint == proposal.content_fingerprint
            ),
            None,
        )
        if matching_active and target_id == matching_active.candidate_id:
            current = matching_active
            refreshed = replace(
                current,
                parent_candidate_ids=tuple(dict.fromkeys((
                    *current.parent_candidate_ids,
                    *proposal.parent_candidate_ids,
                ))),
                dependent_proposition_ids=proposal.dependent_proposition_ids,
                dependent_rule_ids=proposal.dependent_rule_ids,
                assumption_ids=proposal.assumption_ids,
                dependent_annotation_ids=proposal.dependent_annotation_ids,
                dependent_source_ids=proposal.dependent_source_ids,
                dependent_information_need_ids=proposal.dependent_information_need_ids,
                dependent_clarification_ids=proposal.dependent_clarification_ids,
                last_operation=CandidateOperation.UNCHANGED,
            )
            deltas.append(CandidateDelta(
                CandidateOperation.UNCHANGED,
                refreshed,
                revised_from_candidate_id=target_id,
                reason_code="target_candidate_content_unchanged",
            ))
            continue

        if matching_active and target_id is None:
            deltas.append(
                CandidateDelta(
                    CandidateOperation.UNCHANGED,
                    matching_active,
                    invalidated_by_ids=(),
                    reason_code="identical_active_candidate",
                )
            )
            continue

        if (
            matching_active
            and target_id
            and target_id != matching_active.candidate_id
            and known[target_id].status == CandidateStatus.ACTIVE
        ):
            merged = replace(
                matching_active,
                parent_candidate_ids=tuple(dict.fromkeys((
                    *matching_active.parent_candidate_ids,
                    target_id,
                    *proposal.parent_candidate_ids,
                ))),
                dependent_proposition_ids=(
                    matching_active.dependent_proposition_ids
                    | proposal.dependent_proposition_ids
                ),
                dependent_rule_ids=matching_active.dependent_rule_ids | proposal.dependent_rule_ids,
                assumption_ids=matching_active.assumption_ids | proposal.assumption_ids,
                dependent_annotation_ids=(
                    matching_active.dependent_annotation_ids
                    | proposal.dependent_annotation_ids
                ),
                dependent_source_ids=matching_active.dependent_source_ids | proposal.dependent_source_ids,
                dependent_information_need_ids=(
                    matching_active.dependent_information_need_ids
                    | proposal.dependent_information_need_ids
                ),
                dependent_clarification_ids=(
                    matching_active.dependent_clarification_ids
                    | proposal.dependent_clarification_ids
                ),
                last_operation=CandidateOperation.MERGE,
            )
            deltas.append(CandidateDelta(
                CandidateOperation.MERGE,
                merged,
                revised_from_candidate_id=target_id,
                invalidated_by_ids=invalidators,
                reason_code="converged_on_existing_active_candidate",
            ))
            continue

        if target_id:
            prior = known[target_id]
            if prior.content_fingerprint == proposal.content_fingerprint:
                op = CandidateOperation.UNCHANGED
                deltas.append(
                    CandidateDelta(
                        op,
                        prior,
                        revised_from_candidate_id=target_id,
                        reason_code="target_candidate_content_unchanged",
                    )
                )
                continue
            if proposal.revises_candidate_id and prior.status != CandidateStatus.ACTIVE:
                raise ValueError("an inactive candidate must be reopened, not revised")
            operation = CandidateOperation.REOPEN if proposal.reopens_candidate_id else CandidateOperation.REVISE
            parents = tuple(dict.fromkeys((*proposal.parent_candidate_ids, target_id)))
            new_id = _deterministic_candidate_id(assignment_id, proposal)
            lineage = CandidateLineage(
                candidate_id=new_id,
                parent_candidate_ids=parents,
                revision=prior.revision + 1,
                dependent_proposition_ids=proposal.dependent_proposition_ids,
                dependent_rule_ids=proposal.dependent_rule_ids,
                assumption_ids=proposal.assumption_ids,
                dependent_annotation_ids=proposal.dependent_annotation_ids,
                dependent_source_ids=proposal.dependent_source_ids,
                dependent_information_need_ids=proposal.dependent_information_need_ids,
                dependent_clarification_ids=proposal.dependent_clarification_ids,
                status=CandidateStatus.ACTIVE,
                last_operation=operation,
                content_fingerprint=proposal.content_fingerprint,
            )
            deltas.append(
                CandidateDelta(
                    operation,
                    lineage,
                    revised_from_candidate_id=target_id,
                    invalidated_by_ids=invalidators,
                    reason_code="linked_candidate_changed",
                )
            )
            continue

        new_id = _deterministic_candidate_id(assignment_id, proposal)
        lineage = CandidateLineage(
            candidate_id=new_id,
            parent_candidate_ids=proposal.parent_candidate_ids,
            revision=1,
            dependent_proposition_ids=proposal.dependent_proposition_ids,
            dependent_rule_ids=proposal.dependent_rule_ids,
            assumption_ids=proposal.assumption_ids,
            dependent_annotation_ids=proposal.dependent_annotation_ids,
            dependent_source_ids=proposal.dependent_source_ids,
            dependent_information_need_ids=proposal.dependent_information_need_ids,
            dependent_clarification_ids=proposal.dependent_clarification_ids,
            status=CandidateStatus.ACTIVE,
            last_operation=CandidateOperation.CREATE,
            content_fingerprint=proposal.content_fingerprint,
        )
        deltas.append(
            CandidateDelta(
                CandidateOperation.CREATE,
                lineage,
                invalidated_by_ids=invalidators,
                reason_code="new_candidate",
            )
        )
    return tuple(deltas)


def apply_candidate_delta(
    history: SpecialistHistory,
    deltas: Iterable[CandidateDelta],
    *,
    new_history_version: str,
) -> SpecialistHistory:
    """Apply a candidate delta to the Specialist history, returning a copy.

    This updates only Specialist-local history. It does not write the shared
    board or alter evidence statuses.
    """
    candidates = history.candidate_map()
    for delta in deltas:
        incoming = delta.candidate
        if delta.operation == CandidateOperation.REOPEN:
            prior = candidates.get(incoming.candidate_id)
            if prior:
                if prior.status == CandidateStatus.ACTIVE:
                    raise ValueError("cannot reopen an active candidate")
                candidates[incoming.candidate_id] = replace(
                    incoming,
                    status=CandidateStatus.ACTIVE,
                    last_operation=CandidateOperation.REOPEN,
                )
            else:
                if delta.revised_from_candidate_id:
                    old = candidates.get(delta.revised_from_candidate_id)
                    if old is None:
                        raise ValueError("delta references unknown candidate to reopen")
                    candidates[old.candidate_id] = replace(
                        old,
                        status=CandidateStatus.SUPERSEDED,
                        last_operation=CandidateOperation.SUPERSEDE,
                    )
                candidates[incoming.candidate_id] = incoming
        elif delta.operation in (CandidateOperation.CREATE, CandidateOperation.REVISE):
            if incoming.candidate_id in candidates:
                raise ValueError(f"candidate ID collision: {incoming.candidate_id}")
            if delta.revised_from_candidate_id:
                prior = candidates.get(delta.revised_from_candidate_id)
                if not prior:
                    raise ValueError("delta references unknown candidate to revise")
                if delta.operation == CandidateOperation.REVISE:
                    candidates[prior.candidate_id] = replace(
                        prior,
                        status=CandidateStatus.SUPERSEDED,
                        last_operation=CandidateOperation.SUPERSEDE,
                    )
            candidates[incoming.candidate_id] = incoming
        elif delta.operation == CandidateOperation.PARK:
            prior = candidates.get(incoming.candidate_id)
            if not prior:
                raise ValueError("cannot park unknown candidate")
            candidates[incoming.candidate_id] = replace(
                prior,
                status=CandidateStatus.PARKED,
                last_operation=CandidateOperation.PARK,
            )
        elif delta.operation == CandidateOperation.MERGE:
            existing = candidates.get(incoming.candidate_id)
            if existing is None or existing.status != CandidateStatus.ACTIVE:
                raise ValueError("merge target must be an existing active candidate")
            if not delta.revised_from_candidate_id:
                raise ValueError("merge delta must identify the converging candidate")
            converging = candidates.get(delta.revised_from_candidate_id)
            if converging is None or converging.status != CandidateStatus.ACTIVE:
                raise ValueError("merge source must be an existing active candidate")
            if converging.candidate_id == existing.candidate_id:
                raise ValueError("candidate cannot merge into itself")
            candidates[converging.candidate_id] = replace(
                converging,
                status=CandidateStatus.SUPERSEDED,
                last_operation=CandidateOperation.SUPERSEDE,
            )
            candidates[existing.candidate_id] = replace(
                incoming,
                status=CandidateStatus.ACTIVE,
                last_operation=CandidateOperation.MERGE,
            )
        elif delta.operation in (CandidateOperation.UNCHANGED, CandidateOperation.SUPERSEDE):
            if incoming.candidate_id not in candidates:
                raise ValueError("unchanged/supersede delta references unknown candidate")
            if delta.operation == CandidateOperation.UNCHANGED:
                existing = candidates[incoming.candidate_id]
                candidates[incoming.candidate_id] = replace(
                    incoming,
                    status=existing.status,
                    last_operation=CandidateOperation.UNCHANGED,
                )
            else:
                candidates[incoming.candidate_id] = replace(
                    candidates[incoming.candidate_id],
                    status=CandidateStatus.SUPERSEDED,
                    last_operation=CandidateOperation.SUPERSEDE,
                )

    return replace(
        history,
        history_version=new_history_version,
        candidates=tuple(sorted(candidates.values(), key=lambda item: item.candidate_id)),
    )

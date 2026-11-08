"""Entry gate for a Specialist run: snapshot checks, no-op, affected branches."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Iterable, Mapping, Optional

from .contracts import FrontierAction, FrontierHistory, SpecialistHistory
from .delta import compute_affected_candidates, select_focal_candidates
from .delta import CandidateDelta, missing_affected_dispositions
from .history import (
    AssignmentFingerprintInput,
    NoOpDecision,
    RunHistoryStore,
    RunRecord,
    compute_input_fingerprint,
    detect_no_op,
    validate_history_compatibility,
)
from .workflow import decide_frontier_action


class PreparationStatus(StrEnum):
    READY = "ready"
    NO_OP = "no_op"
    STALE_INPUT = "stale_input"
    ASSIGNMENT_ID_CONFLICT = "assignment_id_conflict"
    WAITING = "waiting"
    BUDGET_DEFERRED = "budget_deferred"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True, slots=True)
class RunPreparation:
    status: PreparationStatus
    input_fingerprint: str
    affected_candidate_ids: tuple[str, ...] = ()
    focal_candidate_ids: tuple[str, ...] = ()
    focal_frontier_id: Optional[str] = None
    frontier_action: Optional[FrontierAction] = None
    prior_result_reference: Optional[str] = None
    prior_assignment_id: Optional[str] = None
    diagnostics: tuple[str, ...] = ()


def prepare_run(
    *,
    assignment_id: str,
    fingerprint_input: AssignmentFingerprintInput,
    history: SpecialistHistory,
    store: RunHistoryStore,
    changed_ids: Optional[Iterable[str]] = None,
    explicitly_targeted_candidate_ids: Optional[Iterable[str]] = None,
) -> RunPreparation:
    """Validate the history snapshot and return a deterministic run decision.

    Call this before proposal generation or solver work. Only `READY` should
    continue into model/solver calls. A mismatch or replay is returned as data,
    leaving policy and transport handling with the integration adapter.
    """
    changed = tuple(
        fingerprint_input.changed_ids or () if changed_ids is None else changed_ids
    )
    targeted = tuple(
        fingerprint_input.explicitly_targeted_candidate_ids or ()
        if explicitly_targeted_candidate_ids is None
        else explicitly_targeted_candidate_ids
    )
    fingerprint_input = replace(
        fingerprint_input,
        changed_ids=changed,
        explicitly_targeted_candidate_ids=targeted,
    )

    mismatches = validate_history_compatibility(
        history,
        specialist_scope_id=fingerprint_input.specialist_scope_id,
        case_snapshot_id=fingerprint_input.case_snapshot_id,
        board_version=fingerprint_input.board_version,
        history_version=fingerprint_input.history_version,
    )
    fingerprint = compute_input_fingerprint(fingerprint_input)
    if mismatches:
        return RunPreparation(
            PreparationStatus.STALE_INPUT,
            fingerprint,
            diagnostics=mismatches,
        )

    validation_errors = _validate_assignment_targets(fingerprint_input, history)
    if validation_errors:
        return RunPreparation(
            PreparationStatus.INVALID_INPUT,
            fingerprint,
            diagnostics=validation_errors,
        )

    no_op = detect_no_op(
        assignment_id=assignment_id,
        input_fingerprint=fingerprint,
        store=store,
    )
    if no_op.decision == NoOpDecision.NO_OP:
        return RunPreparation(
            PreparationStatus.NO_OP,
            fingerprint,
            prior_result_reference=no_op.prior_result_reference,
            prior_assignment_id=no_op.prior_assignment_id,
            diagnostics=(no_op.reason,),
        )
    if no_op.decision == NoOpDecision.ASSIGNMENT_ID_CONFLICT:
        return RunPreparation(
            PreparationStatus.ASSIGNMENT_ID_CONFLICT,
            fingerprint,
            diagnostics=(no_op.reason,),
        )

    affected = compute_affected_candidates(
        history,
        changed,
        targeted,
    )
    focal_candidates: tuple[str, ...] = ()
    focal_frontier_id: Optional[str] = None
    frontier_action: Optional[FrontierAction] = None
    if fingerprint_input.mode == "advance" and fingerprint_input.focal_proposition_id:
        focal_candidates = select_focal_candidates(
            history,
            fingerprint_input.focal_proposition_id,
            explicitly_targeted_candidate_ids=targeted,
        )
        focal_frontier = next(
            (
                frontier for frontier in history.frontiers
                if frontier.target_proposition_id == fingerprint_input.focal_proposition_id
            ),
            FrontierHistory(
                frontier_id=f"frontier:{fingerprint_input.focal_proposition_id}",
                target_proposition_id=fingerprint_input.focal_proposition_id,
            ),
        )
        focal_frontier_id = focal_frontier.frontier_id
        budget_values = fingerprint_input.budgets
        if not isinstance(budget_values, Mapping):
            return RunPreparation(
                PreparationStatus.INVALID_INPUT,
                fingerprint,
                diagnostics=("budgets must be a mapping for advance mode",),
            )
        try:
            raw_remaining = budget_values.get(
                "targeted_expansion_calls_remaining",
                budget_values.get("max_targeted_expansion_calls", 1),
            )
            if isinstance(raw_remaining, bool) or not isinstance(raw_remaining, int):
                raise ValueError("targeted expansion budget must be an integer")
            per_run_remaining = raw_remaining
            if per_run_remaining < 0:
                raise ValueError("targeted expansion budget cannot be negative")
        except (TypeError, ValueError) as exc:
            return RunPreparation(
                PreparationStatus.INVALID_INPUT,
                fingerprint,
                diagnostics=(str(exc),),
            )
        cumulative_limit = budget_values.get("max_cumulative_expansion_calls")
        if cumulative_limit is not None:
            if isinstance(cumulative_limit, bool) or not isinstance(cumulative_limit, int):
                return RunPreparation(
                    PreparationStatus.INVALID_INPUT,
                    fingerprint,
                    diagnostics=("cumulative expansion budget must be an integer",),
                )
            if cumulative_limit < 0:
                return RunPreparation(
                    PreparationStatus.INVALID_INPUT,
                    fingerprint,
                    diagnostics=("cumulative expansion budget cannot be negative",),
                )
            per_run_remaining = min(
                per_run_remaining,
                max(0, cumulative_limit - history.prior_expansion_budget_usage),
            )
        pending_need_ids = {
            need.need_id
            for need in history.information_needs
            if need.workflow_status == "pending"
        }
        direction_fingerprint = compute_input_fingerprint(
            {
                "mode": fingerprint_input.mode,
                "focal_proposition_id": fingerprint_input.focal_proposition_id,
                "operation_goal": fingerprint_input.operation_goal,
                "lead_direction": fingerprint_input.lead_direction,
            }
        )
        frontier_action = decide_frontier_action(
            focal_frontier,
            direction_fingerprint=direction_fingerprint,
            changed_ids=changed,
            pending_information_need_ids=pending_need_ids,
            expansion_budget_remaining=per_run_remaining,
            lead_authorized=True,
        )
        if frontier_action == FrontierAction.WAIT:
            return RunPreparation(
                PreparationStatus.WAITING,
                fingerprint,
                focal_candidate_ids=focal_candidates,
                focal_frontier_id=focal_frontier_id,
                frontier_action=frontier_action,
                diagnostics=("frontier is already expanded or awaits linked information",),
            )
        if frontier_action in (FrontierAction.DEFER, FrontierAction.PARK, FrontierAction.REOPEN):
            return RunPreparation(
                PreparationStatus.BUDGET_DEFERRED,
                fingerprint,
                focal_candidate_ids=focal_candidates,
                focal_frontier_id=focal_frontier_id,
                frontier_action=frontier_action,
                diagnostics=("frontier work is deferred by its state or expansion budget",),
            )
    return RunPreparation(
        PreparationStatus.READY,
        fingerprint,
        affected_candidate_ids=affected,
        focal_candidate_ids=focal_candidates,
        focal_frontier_id=focal_frontier_id,
        frontier_action=frontier_action,
    )


def _validate_assignment_targets(
    assignment: AssignmentFingerprintInput,
    history: SpecialistHistory,
) -> tuple[str, ...]:
    errors: list[str] = []
    valid_modes = {"initial", "revision", "advance"}
    if assignment.mode not in valid_modes:
        errors.append(f"unsupported mode {assignment.mode!r}")
    candidates = history.candidate_map()
    targeted = set(assignment.explicitly_targeted_candidate_ids or ())
    unknown_targets = targeted - candidates.keys()
    if unknown_targets:
        errors.append("unknown targeted candidate IDs: " + ", ".join(sorted(unknown_targets)))
    if assignment.mode == "initial" and assignment.initial_case_packet is None:
        errors.append("initial mode requires initial_case_packet")
    if assignment.mode == "revision":
        if not assignment.focal_proposition_id and not targeted:
            errors.append("revision mode requires a focal proposition or targeted candidate")
        known_propositions = set(assignment.available_proposition_ids or ())
        known_propositions.update(
            proposition_id
            for candidate in candidates.values()
            for proposition_id in candidate.dependent_proposition_ids
        )
        focal = assignment.focal_proposition_id
        if focal and focal not in known_propositions:
            errors.append(f"unknown revision focal proposition {focal!r}")
    if assignment.mode == "advance":
        focal = assignment.focal_proposition_id
        if not focal:
            errors.append("advance mode requires a focal proposition")
        else:
            known_propositions = set(assignment.available_proposition_ids or ())
            known_propositions.update(
                proposition_id
                for candidate in candidates.values()
                for proposition_id in candidate.dependent_proposition_ids
            )
            if focal not in known_propositions:
                errors.append(f"unknown advance focal proposition {focal!r}")
    return tuple(errors)


def record_run_result(
    *,
    assignment_id: str,
    preparation: RunPreparation,
    result_reference: str,
    run_status: str,
    store: RunHistoryStore,
    reusable: bool,
    candidate_deltas: Iterable[CandidateDelta] = (),
) -> None:
    """Record a completed result after generation/search has actually finished."""
    if preparation.status != PreparationStatus.READY:
        raise ValueError("only a READY run can be recorded as completed")
    missing = missing_affected_dispositions(
        preparation.affected_candidate_ids,
        candidate_deltas,
    )
    if missing:
        raise ValueError(
            "cannot record run with undispositioned affected candidates: "
            + ", ".join(missing)
        )
    store.record_completed(
        RunRecord(
            assignment_id=assignment_id,
            input_fingerprint=preparation.input_fingerprint,
            result_reference=result_reference,
            run_status=run_status,
            reusable=reusable,
        )
    )

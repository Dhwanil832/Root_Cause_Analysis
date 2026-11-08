"""SAHS run orchestration: state gate, one proposal, validation, ASP, delta."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from .config import SpecialistConfig
from .contracts import (
    CandidateLineage,
    CandidateOperation,
    CandidateStatus,
    InformationNeedHistory,
    SpecialistHistory,
)
from .delta import (
    CandidateDelta,
    CandidateProposal,
    apply_candidate_delta,
    build_candidate_delta,
    fingerprint_candidate_graph,
    missing_affected_dispositions,
)
from .engine_contracts import (
    CandidateExplanation,
    CausalGraph,
    InformationGap,
    OpenFrontier,
    SpecialistAssignment,
    SpecialistResult,
    SourceReference,
)
from .history import AssignmentFingerprintInput, RunHistoryStore, compute_input_fingerprint
from .prompt_builder import SYSTEM_INSTRUCTIONS, build_proposal_request
from .proposal import ProposalGenerator, ProposalRequest
from .solver.interface import CandidateSolver, SearchLimits, SolverCandidate, SearchResult
from .state_controller import PreparationStatus, prepare_run, record_run_result
from .validation import ProposalValidationError, merge_graph, validate_proposal_batch
from .workflow import merge_information_needs, record_frontier_attempt


class SpecialistEngine:
    def __init__(
        self,
        proposer: ProposalGenerator,
        solver: CandidateSolver,
        history_store: RunHistoryStore,
        config: SpecialistConfig | None = None,
    ) -> None:
        self.proposer = proposer
        self.solver = solver
        self.history_store = history_store
        self.config = config or SpecialistConfig()

    def run(self, assignment: SpecialistAssignment) -> SpecialistResult:
        fingerprint_input = self._fingerprint_input(assignment)
        prepared = prepare_run(
            assignment_id=assignment.assignment_id,
            fingerprint_input=fingerprint_input,
            history=assignment.history,
            store=self.history_store,
            changed_ids=assignment.changed_ids,
            explicitly_targeted_candidate_ids=assignment.explicitly_targeted_candidate_ids,
        )
        if prepared.status != PreparationStatus.READY:
            return self._early_result(assignment, prepared)

        budget_error = self._validate_budgets(assignment)
        if budget_error:
            return self._result(assignment, prepared.input_fingerprint, "invalid_input",
                                diagnostics=(budget_error,))

        self._run_usage = {
            "proposal_calls_start": getattr(self.proposer, "calls_made", 0),
            "solver_calls": 0,
            "solver_models": 0,
            "solver_seconds": 0.0,
            "prompt_omissions": [],
        }

        primary_request = build_proposal_request(
            assignment, max_source_chars=self._source_budget(assignment),
            max_prompt_tokens=self.config.max_prompt_tokens,
        )
        self._run_usage["prompt_omissions"].extend(primary_request.omitted)
        try:
            raw = self.proposer.propose(primary_request)
        except Exception as exc:
            return self._result(
                assignment, prepared.input_fingerprint, "generation_failed",
                diagnostics=(f"proposal generator failed: {type(exc).__name__}: {exc}",),
                resource_usage=self._usage(),
            )
        try:
            proposal = validate_proposal_batch(raw, assignment)
        except ProposalValidationError as exc:
            return self._result(
                assignment, prepared.input_fingerprint, "invalid_proposal",
                diagnostics=(str(exc),), resource_usage=self._usage(),
            )
        graph = merge_graph(assignment.relevant_graph, proposal)
        target_ids = self._target_ids(assignment, prepared.focal_candidate_ids, graph)
        if not target_ids:
            return self._result(
                assignment, prepared.input_fingerprint, "invalid_input",
                rejected_fragments=proposal.rejected_fragments,
                diagnostics=("No target proposition was supplied, reported, or proposed",),
                resource_usage=self._usage(),
                graph_delta=CausalGraph(proposal.proposed_propositions, proposal.proposed_rules),
            )
        unknown_targets = set(target_ids) - graph.proposition_map().keys()
        if unknown_targets:
            return self._result(assignment, prepared.input_fingerprint, "invalid_input",
                                diagnostics=("unknown target propositions: " + ", ".join(sorted(unknown_targets)),),
                                resource_usage=self._usage())
        if len(graph.propositions) > self._limit(assignment, "max_propositions", self.config.max_propositions):
            return self._result(assignment, prepared.input_fingerprint, "invalid_proposal",
                                diagnostics=("proposal exceeds proposition budget",),
                                rejected_fragments=proposal.rejected_fragments,
                                resource_usage=self._usage())
        if len(graph.rules) > self._limit(assignment, "max_rules", self.config.max_rules):
            return self._result(assignment, prepared.input_fingerprint, "invalid_proposal",
                                diagnostics=("proposal exceeds rule budget",),
                                rejected_fragments=proposal.rejected_fragments,
                                resource_usage=self._usage())

        limits = self._search_limits(assignment)
        search_results: dict[str, SearchResult] = {}
        try:
            for target_id in target_ids:
                search_results[target_id] = self._search_tracked(graph, target_id, limits)
        except Exception as exc:
            return self._result(
                assignment, prepared.input_fingerprint, "solver_failed",
                rejected_fragments=proposal.rejected_fragments,
                clarification_items=proposal.clarification_items,
                information_gaps=proposal.information_gaps,
                diagnostics=(f"candidate solver failed: {type(exc).__name__}: {exc}",),
                resource_usage=self._usage(),
                graph_delta=CausalGraph(proposal.proposed_propositions, proposal.proposed_rules),
            )

        # At most one targeted follow-up, selected deterministically from the
        # first unresolved frontier. Never run an unbounded critique loop.
        expansion_calls = 0
        frontier_id = self._first_frontier(search_results)
        remaining_targeted = min(
            self._limit(assignment, "max_targeted_expansion_calls", self.config.max_targeted_expansion_calls),
            max(0, self._limit(assignment, "targeted_expansion_calls_remaining", 1)),
        )
        if frontier_id and remaining_targeted:
            updated_assignment = replace(assignment, relevant_graph=graph)
            expansion_request = build_proposal_request(
                updated_assignment,
                target_proposition_id=frontier_id,
                task_mode="targeted_expansion",
                max_source_chars=self._source_budget(assignment),
                max_prompt_tokens=self.config.max_prompt_tokens,
            )
            self._run_usage["prompt_omissions"].extend(expansion_request.omitted)
            try:
                expansion_raw = self.proposer.propose(expansion_request)
                expansion_batch = validate_proposal_batch(expansion_raw, updated_assignment)
                self._validate_expansion_target(expansion_batch, frontier_id)
                proposal = self._combine_batches(proposal, expansion_batch)
                graph = merge_graph(graph, expansion_batch)
                expansion_calls = 1
                for target_id in target_ids:
                    search_results[target_id] = self._search_tracked(graph, target_id, limits)
            except (ProposalValidationError, Exception) as exc:
                # Keep valid primary results. The diagnostic makes the failed
                # targeted expansion explicit and leaves the frontier open.
                diagnostics = (f"targeted expansion failed: {type(exc).__name__}: {exc}",)
                expansion_failed = True
            else:
                diagnostics = ()
                expansion_failed = False
        else:
            diagnostics = ()
            expansion_failed = False

        solver_candidates = [
            candidate
            for target_id in target_ids
            for candidate in search_results[target_id].candidates
        ]
        solver_candidates = self._dedupe_solver_candidates(solver_candidates)
        max_returned = min(
            self._limit(assignment, "max_returned_explanations", self.config.max_returned_explanations),
            self._limit(assignment, "max_candidates", self.config.max_candidates),
        )
        solver_candidates = solver_candidates[:max_returned]
        candidate_proposals, candidate_by_fingerprint = self._candidate_proposals(
            assignment, prepared, graph, solver_candidates, proposal.information_gaps,
            proposal.clarification_items,
        )
        try:
            deltas = build_candidate_delta(
                assignment_id=assignment.assignment_id,
                history=assignment.history,
                proposals=candidate_proposals,
                invalidated_by_ids=assignment.changed_ids,
            )
            deltas += self._merge_converged_branches(
                deltas, candidate_proposals, assignment.history, assignment.changed_ids
            )
            missing = missing_affected_dispositions(prepared.affected_candidate_ids, deltas)
            if missing:
                # Explicitly preserve affected candidates that yielded no
                # distinct replacement; do not silently drop their lineage.
                preserve = [
                    CandidateProposal(
                        content_fingerprint=assignment.history.candidate_map()[candidate_id].content_fingerprint or "preserve-" + candidate_id,
                        revises_candidate_id=candidate_id,
                    )
                    for candidate_id in missing
                ]
                deltas += build_candidate_delta(
                    assignment_id=assignment.assignment_id,
                    history=assignment.history,
                    proposals=preserve,
                )
            updated_history = self._apply_history(
                assignment, deltas, proposal.information_gaps,
                candidate_by_fingerprint, expansion_calls, frontier_id,
                any_candidate=bool(solver_candidates),
            )
        except (ValueError, KeyError) as exc:
            return self._result(
                assignment, prepared.input_fingerprint, "invalid_delta",
                rejected_fragments=proposal.rejected_fragments,
                clarification_items=proposal.clarification_items,
                information_gaps=proposal.information_gaps,
                diagnostics=(str(exc),), resource_usage=self._usage(search_results),
            )

        explanations = self._explanations(
            solver_candidates, graph, assignment, deltas, candidate_by_fingerprint
        )
        frontiers = self._package_frontiers(search_results, explanations)
        statuses = {result.status for result in search_results.values()}
        if "partial_budget" in statuses:
            status = "partial_budget"
        elif not explanations:
            status = "no_candidate_under_supplied_rules"
        elif frontiers:
            status = "open_frontier"
        else:
            status = "completed"
        result = self._result(
            assignment,
            prepared.input_fingerprint,
            status,
            graph_delta=CausalGraph(proposal.proposed_propositions, proposal.proposed_rules),
            candidate_operations=deltas,
            candidates=explanations,
            unchanged_candidate_refs=tuple(
                delta.candidate.candidate_id for delta in deltas
                if delta.operation == CandidateOperation.UNCHANGED
            ),
            rejected_fragments=proposal.rejected_fragments,
            clarification_items=proposal.clarification_items,
            information_gaps=proposal.information_gaps,
            open_frontier=frontiers,
            solver_trace=tuple((target, search_results[target]) for target in target_ids),
            validation_warnings=tuple(
                f"discarded {item.fragment_type} {item.fragment_id or '<unknown>'}: {item.reason}"
                for item in proposal.rejected_fragments
            ),
            resource_usage=self._usage(search_results, expansion_calls),
            diagnostics=diagnostics,
            updated_history=updated_history,
        )
        result_ref = f"sahs-result:{assignment.assignment_id}:{prepared.input_fingerprint[:16]}"
        record_run_result(
            assignment_id=assignment.assignment_id,
            preparation=prepared,
            result_reference=result_ref,
            run_status=result.status,
            store=self.history_store,
            reusable=result.status not in {"generation_failed", "solver_failed", "invalid_delta"},
            candidate_deltas=deltas,
        )
        return result

    @staticmethod
    def _fingerprint_input(assignment: SpecialistAssignment) -> AssignmentFingerprintInput:
        return AssignmentFingerprintInput(
            case_id=assignment.case_id,
            specialist_scope_id=assignment.specialist_scope_id,
            case_snapshot_id=assignment.case_snapshot_id,
            board_version=assignment.board_version,
            history_version=assignment.history_version,
            mode=assignment.mode,
            focal_proposition_id=assignment.focal_proposition_id,
            operation_goal=assignment.operation_goal,
            lead_direction=assignment.lead_direction,
            initial_case_packet=assignment.initial_case_packet,
            relevant_graph=assignment.relevant_graph,
            source_bundle=assignment.source_bundle,
            relevant_history=assignment.history,
            lead_feedback=assignment.lead_feedback,
            assessor_annotations=assignment.assessor_annotations,
            changed_ids=assignment.changed_ids,
            budgets=assignment.budgets,
            config_version="sahs-0.3",
            explicitly_targeted_candidate_ids=assignment.explicitly_targeted_candidate_ids,
            available_proposition_ids=assignment.available_proposition_ids,
        )

    @staticmethod
    def _target_ids(assignment: SpecialistAssignment, focal_candidate_ids: tuple[str, ...], graph: CausalGraph) -> tuple[str, ...]:
        if assignment.mode == "advance":
            return (assignment.focal_proposition_id,) if assignment.focal_proposition_id else ()
        if assignment.mode == "revision":
            targets = set(assignment.target_proposition_ids)
            if assignment.focal_proposition_id:
                targets.add(assignment.focal_proposition_id)
            if not targets:
                history_candidates = assignment.history.candidate_map()
                for candidate_id in focal_candidate_ids or assignment.explicitly_targeted_candidate_ids:
                    candidate = history_candidates.get(candidate_id)
                    if candidate:
                        targets.update(candidate.dependent_proposition_ids)
            return tuple(sorted(targets))
        if assignment.target_proposition_ids:
            return tuple(sorted(set(assignment.target_proposition_ids)))
        return tuple(sorted(
            prop.proposition_id for prop in graph.propositions
            if prop.case_status in {"reported", "hypothetical"}
            and prop.kind in {"incident_event", "case_claim"}
        ))

    def _candidate_proposals(
        self,
        assignment: SpecialistAssignment,
        prepared,
        graph: CausalGraph,
        solver_candidates: list[SolverCandidate],
        gaps: tuple[InformationGap, ...],
        clarifications,
    ) -> tuple[list[CandidateProposal], dict[str, CandidateProposal]]:
        props = graph.proposition_map()
        rules = graph.rule_map()
        affected = [assignment.history.candidate_map()[item]
                    for item in prepared.affected_candidate_ids
                    if item in assignment.history.candidate_map()]
        parent_defaults = tuple(prepared.focal_candidate_ids) if assignment.mode == "advance" else ()
        entries: list[tuple[str, CandidateProposal, str | None]] = []
        for solved in solver_candidates:
            selected_rules = [rules[rule_id] for rule_id in solved.rule_ids]
            references = [ref for rule in selected_rules for ref in rule.source_refs]
            references.extend(ref for proposition_id in solved.proposition_ids
                              for ref in props[proposition_id].source_refs)
            refs = _unique_source_refs(references)
            fingerprint = fingerprint_candidate_graph(
                propositions=[asdict(props[item]) for item in solved.proposition_ids],
                rules=[asdict(rules[item]) for item in solved.rule_ids],
                assumptions=solved.assumptions,
                source_refs=[asdict(item) for item in refs],
            )
            dependencies = set(solved.proposition_ids) | set(solved.rule_ids) | set(solved.assumptions)
            source_ids = {ref.source_id for ref in refs}
            annotation_ids = {
                annotation.get("annotation_id")
                for annotation in assignment.assessor_annotations
                if isinstance(annotation, dict)
                and annotation.get("target_id") in dependencies
                and annotation.get("annotation_id")
            }
            linked_candidate_ids = (
                set(prepared.focal_candidate_ids)
                | set(prepared.affected_candidate_ids)
                | set(assignment.explicitly_targeted_candidate_ids)
            )
            need_ids = {
                item.need_id for item in assignment.history.information_needs
                if set(item.linked_candidate_ids) & linked_candidate_ids
            }
            need_ids.update(
                item.need_id for item in gaps
                if (set(item.linked_proposition_ids) & dependencies)
                or (set(item.linked_candidate_ids) & linked_candidate_ids)
                or (set(item.linked_frontier_ids) & {
                    f"frontier:{proposition_id}" for proposition_id in dependencies
                })
            )
            clarification_ids = {
                item.clarification_id for item in clarifications
                if set(item.linked_proposition_ids) & dependencies
            }
            matching_priors = _overlapping_prior_candidates(affected, dependencies)
            target = matching_priors[0] if matching_priors else (
                affected[0] if assignment.mode == "revision" and len(affected) == 1 else None
            )
            parents = (
                tuple(item.candidate_id for item in matching_priors)
                if matching_priors else ((target.candidate_id,) if target else parent_defaults)
            )
            proposal = CandidateProposal(
                content_fingerprint=fingerprint,
                dependent_proposition_ids=frozenset(solved.proposition_ids),
                dependent_rule_ids=frozenset(solved.rule_ids),
                assumption_ids=frozenset(solved.assumptions),
                dependent_annotation_ids=frozenset(annotation_ids),
                dependent_source_ids=frozenset(source_ids),
                dependent_information_need_ids=frozenset(need_ids),
                dependent_clarification_ids=frozenset(clarification_ids),
                parent_candidate_ids=parents,
                revises_candidate_id=(target.candidate_id if target and target.status == CandidateStatus.ACTIVE else None),
                reopens_candidate_id=(target.candidate_id if target and target.status == CandidateStatus.PARKED else None),
            )
            entries.append((fingerprint, proposal, target.candidate_id if target else None))

        # At most one revised child can supersede a prior branch. Additional
        # explanations become sibling alternatives retaining the same parent.
        grouped: dict[str, list[tuple[str, CandidateProposal, str | None]]] = {}
        for item in entries:
            if item[2]:
                grouped.setdefault(item[2], []).append(item)
        for target_id in grouped:
            indexes = sorted(
                (index for index, item in enumerate(entries) if item[2] == target_id),
                key=lambda index: entries[index][0],
            )
            for index in indexes[1:]:
                fingerprint, proposal, matched_id = entries[index]
                entries[index] = (
                    fingerprint,
                    replace(
                        proposal,
                        revises_candidate_id=None,
                        reopens_candidate_id=None,
                        parent_candidate_ids=(target_id,),
                    ),
                    matched_id,
                )

        # Make the first group entry revise/reopen; additional alternatives fork.
        proposals = [item[1] for item in entries]
        by_fingerprint = {item[0]: item[1] for item in entries}
        return proposals, by_fingerprint

    @staticmethod
    def _apply_history(assignment, deltas, gaps, by_fingerprint, expansion_calls, frontier_id, any_candidate):
        version = _next_history_version(assignment.history_version)
        history = apply_candidate_delta(assignment.history, deltas, new_history_version=version)
        linked_frontier = (
            f"frontier:{frontier_id}" if frontier_id
            else (f"frontier:{assignment.focal_proposition_id}" if assignment.focal_proposition_id else None)
        )
        needs = []
        for gap in gaps:
            meaning = compute_input_fingerprint({
                "unknown": gap.unknown.casefold(),
                "why": gap.why_it_matters.casefold(),
                "resolves": gap.information_that_could_resolve_it.casefold(),
            })
            needs.append(InformationNeedHistory(
                need_id=gap.need_id,
                linked_candidate_ids=gap.linked_candidate_ids,
                linked_frontier_ids=gap.linked_frontier_ids or ((linked_frontier,) if linked_frontier else ()),
                target_unknown_id=gap.linked_proposition_ids[0] if gap.linked_proposition_ids else None,
                workflow_status="proposed",
                last_changed_version=version,
                meaning_fingerprint=meaning,
            ))
        if needs:
            history = merge_information_needs(history, needs, new_history_version=version)
        if assignment.mode == "advance" and assignment.focal_proposition_id:
            target = assignment.focal_proposition_id
            target_frontier_id = f"frontier:{target}"
            candidate_ids = [item.candidate.candidate_id for item in deltas]
            dependencies = {item for delta in deltas for item in delta.candidate.dependency_ids}
            links = {need.need_id for need in history.information_needs
                     if target_frontier_id in need.linked_frontier_ids
                     or (linked_frontier is not None and linked_frontier in need.linked_frontier_ids)}
            history = record_frontier_attempt(
                history,
                frontier_id=target_frontier_id,
                target_proposition_id=target,
                candidate_ids=candidate_ids,
                direction_fingerprint=compute_input_fingerprint({
                    "mode": assignment.mode,
                    "focal_proposition_id": target,
                    "operation_goal": assignment.operation_goal,
                    "lead_direction": assignment.lead_direction,
                }),
                assignment_id=assignment.assignment_id,
                outcome="expanded" if any_candidate else "no_candidate_under_supplied_rules",
                dependency_ids=dependencies,
                linked_need_ids=links,
                expansion_calls_used=expansion_calls,
                new_history_version=version,
            )
        return history

    @staticmethod
    def _merge_converged_branches(deltas, proposals, history, invalidated_by_ids):
        """Merge equally relevant affected branches that converge on one graph.

        One branch is revised/reopened by the normal delta builder. If the
        same proposal explicitly names additional affected branches as parents,
        append MERGE operations so those active branches are superseded into
        the converged candidate rather than left as duplicate active entries.
        """
        by_fingerprint = {item.content_fingerprint: item for item in proposals}
        prior_candidates = history.candidate_map()
        result = list(deltas)
        for index, delta in enumerate(tuple(result)):
            proposal = by_fingerprint.get(delta.candidate.content_fingerprint or "")
            if proposal is None or delta.operation not in {
                CandidateOperation.REVISE, CandidateOperation.REOPEN,
                CandidateOperation.UNCHANGED, CandidateOperation.MERGE,
            }:
                continue
            original_target = proposal.revises_candidate_id or proposal.reopens_candidate_id
            if not original_target:
                continue
            branch_ids = set(proposal.parent_candidate_ids) - {original_target}
            converging = [prior_candidates[item] for item in sorted(branch_ids)
                          if item in prior_candidates
                          and prior_candidates[item].status == CandidateStatus.ACTIVE]
            current = result[index].candidate
            for source in converging:
                merged = replace(
                    current,
                    parent_candidate_ids=tuple(sorted(set(current.parent_candidate_ids) | {source.candidate_id})),
                    dependent_proposition_ids=current.dependent_proposition_ids | source.dependent_proposition_ids,
                    dependent_rule_ids=current.dependent_rule_ids | source.dependent_rule_ids,
                    assumption_ids=current.assumption_ids | source.assumption_ids,
                    dependent_annotation_ids=current.dependent_annotation_ids | source.dependent_annotation_ids,
                    dependent_source_ids=current.dependent_source_ids | source.dependent_source_ids,
                    dependent_information_need_ids=(
                        current.dependent_information_need_ids | source.dependent_information_need_ids
                    ),
                    dependent_clarification_ids=(
                        current.dependent_clarification_ids | source.dependent_clarification_ids
                    ),
                    last_operation=CandidateOperation.MERGE,
                )
                result.append(CandidateDelta(
                    CandidateOperation.MERGE,
                    merged,
                    revised_from_candidate_id=source.candidate_id,
                    invalidated_by_ids=tuple(sorted(set(invalidated_by_ids))),
                    reason_code="converged_on_same_candidate_graph",
                ))
                current = merged
        return tuple(result[len(deltas):])

    @staticmethod
    def _explanations(solver_candidates, graph, assignment, deltas, by_fingerprint):
        props = graph.proposition_map()
        rules = graph.rule_map()
        output = []
        active = assignment.history.candidate_map()
        delta_by_fp = {delta.candidate.content_fingerprint: delta.candidate.candidate_id for delta in deltas
                       if delta.candidate.content_fingerprint}
        for solved in solver_candidates:
            references = _unique_source_refs(
                [ref for rule_id in solved.rule_ids for ref in rules[rule_id].source_refs]
                + [ref for prop_id in solved.proposition_ids for ref in props[prop_id].source_refs]
            )
            fp = fingerprint_candidate_graph(
                propositions=[asdict(props[item]) for item in solved.proposition_ids],
                rules=[asdict(rules[item]) for item in solved.rule_ids],
                assumptions=solved.assumptions,
                source_refs=[asdict(item) for item in references],
            )
            candidate_id = delta_by_fp.get(fp)
            if not candidate_id:
                candidate_id = next((item.candidate_id for item in active.values()
                                     if item.content_fingerprint == fp), "sahs-" + fp[:16])
            output.append(CandidateExplanation(
                candidate_id=candidate_id,
                target_proposition_id=solved.target_id,
                proposition_ids=solved.proposition_ids,
                rule_ids=solved.rule_ids,
                reported_premise_ids=solved.reported_premise_ids,
                assumptions=solved.assumptions,
                source_refs=references,
                solver_trace=solved.trace,
                candidate_fingerprint=fp,
            ))
        return tuple(output)

    @staticmethod
    def _package_frontiers(search_results, explanations):
        associated = {item.proposition_id: set() for result in search_results.values()
                      for item in [OpenFrontier(pid, "") for pid in result.open_frontier_ids]}
        for candidate in explanations:
            for proposition_id in candidate.assumptions:
                associated.setdefault(proposition_id, set()).add(candidate.candidate_id)
        result: dict[str, OpenFrontier] = {}
        for search in search_results.values():
            for proposition_id in search.open_frontier_ids:
                result[proposition_id] = OpenFrontier(
                    proposition_id,
                    "required condition is not established in the supplied graph",
                    tuple(sorted(associated.get(proposition_id, ()))),
                )
        return tuple(result[key] for key in sorted(result))

    @staticmethod
    def _combine_batches(first, second):
        from .proposal import ProposalBatch
        return ProposalBatch(
            "1",
            first.proposed_propositions + second.proposed_propositions,
            first.proposed_rules + second.proposed_rules,
            first.clarification_items + second.clarification_items,
            first.information_gaps + second.information_gaps,
            first.rejected_fragments + second.rejected_fragments,
        )

    @staticmethod
    def _validate_expansion_target(batch, target_id):
        """Keep a targeted backward expansion attached to its assigned frontier."""
        if not any(rule.consequent_id == target_id for rule in batch.proposed_rules):
            raise ProposalValidationError(
                f"targeted expansion did not propose a rule for assigned frontier {target_id!r}"
            )

    @staticmethod
    def _dedupe_solver_candidates(candidates):
        unique = {}
        for candidate in candidates:
            key = (candidate.target_id, candidate.rule_ids, candidate.assumptions)
            unique.setdefault(key, candidate)
        return [unique[key] for key in sorted(unique)]

    @staticmethod
    def _first_frontier(search_results):
        return next((frontier for target in sorted(search_results)
                     for frontier in sorted(search_results[target].open_frontier_ids)), None)

    def _search_limits(self, assignment):
        return SearchLimits(
            max_depth=self._limit(assignment, "max_depth", self.config.max_depth),
            max_models=self._limit(assignment, "max_answer_sets", self.config.max_answer_sets),
            timeout_seconds=float(assignment.budgets.get("solver_timeout_seconds", self.config.solver_timeout_seconds)),
        )

    def _validate_budgets(self, assignment):
        hard_limits = {
            "max_source_chars": self.config.max_source_chars,
            "max_propositions": self.config.max_propositions,
            "max_rules": self.config.max_rules,
            "max_candidates": self.config.max_candidates,
            "max_depth": self.config.max_depth,
            "max_answer_sets": self.config.max_answer_sets,
            "max_targeted_expansion_calls": self.config.max_targeted_expansion_calls,
            "max_returned_explanations": self.config.max_returned_explanations,
            "targeted_expansion_calls_remaining": self.config.max_targeted_expansion_calls,
        }
        for key, hard_max in hard_limits.items():
            if key not in assignment.budgets:
                continue
            value = assignment.budgets[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return f"budget {key} must be a nonnegative integer"
            if value > hard_max:
                return f"budget {key} exceeds configured hard limit {hard_max}"
        import math
        try:
            timeout = float(assignment.budgets.get("solver_timeout_seconds", self.config.solver_timeout_seconds))
        except (TypeError, ValueError):
            return "solver_timeout_seconds must be a positive finite number"
        if not math.isfinite(timeout) or timeout <= 0 or timeout > self.config.solver_timeout_seconds:
            return "solver_timeout_seconds must be positive and within the configured hard limit"
        return None

    def _limit(self, assignment, key, default):
        value = assignment.budgets.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"budget {key} must be a nonnegative integer")
        return value

    def _source_budget(self, assignment):
        return self._limit(assignment, "max_source_chars", self.config.max_source_chars)

    def _usage(self, searches=None, targeted_calls=0):
        usage = getattr(self, "_run_usage", None) or {
            "proposal_calls_start": 0, "solver_calls": 0,
            "solver_models": 0, "solver_seconds": 0.0,
        }
        current_calls = getattr(self.proposer, "calls_made", None)
        return {
            "proposal_calls": (
                max(0, current_calls - usage["proposal_calls_start"])
                if isinstance(current_calls, int) else None
            ),
            "targeted_expansion_calls": targeted_calls,
            "solver_calls": usage["solver_calls"],
            "solver_models": usage["solver_models"],
            "solver_seconds": round(usage["solver_seconds"], 6),
            "prompt_omissions": list(usage.get("prompt_omissions", ())),
        }

    def _search_tracked(self, graph, target_id, limits):
        result = self.solver.search(graph, target_id, limits)
        usage = self._run_usage
        usage["solver_calls"] += 1
        usage["solver_models"] += result.models_seen
        usage["solver_seconds"] += result.solver_time_seconds
        return result

    def _early_result(self, assignment, prepared):
        status = prepared.status.value
        return self._result(
            assignment,
            prepared.input_fingerprint,
            status,
            diagnostics=prepared.diagnostics,
            prior_result_reference=prepared.prior_result_reference,
            prior_assignment_id=prepared.prior_assignment_id,
        )

    @staticmethod
    def _result(assignment, fingerprint, status, **kwargs):
        return SpecialistResult(
            schema_version="1",
            assignment_id=assignment.assignment_id,
            case_snapshot_id=assignment.case_snapshot_id,
            board_version=assignment.board_version,
            history_version=assignment.history_version,
            input_fingerprint=fingerprint,
            status=status,
            **kwargs,
        )


def _unique_source_refs(references: list[SourceReference]) -> tuple[SourceReference, ...]:
    by_key = {(item.source_id, item.source_version, item.chunk_id, item.start_offset, item.end_offset): item
              for item in references}
    return tuple(by_key[key] for key in sorted(by_key))


def _best_prior_candidate(candidates: list[CandidateLineage], dependencies: set[str]) -> CandidateLineage | None:
    matches = _overlapping_prior_candidates(candidates, dependencies)
    return matches[0] if matches else None


def _overlapping_prior_candidates(
    candidates: list[CandidateLineage], dependencies: set[str]
) -> list[CandidateLineage]:
    scored = [
        (len(candidate.dependency_ids & dependencies), candidate.candidate_id, candidate)
        for candidate in candidates
        if dependencies and candidate.dependency_ids & dependencies
    ]
    if not scored:
        return []
    best = max(item[0] for item in scored)
    return [item[2] for item in sorted(scored, key=lambda item: item[1]) if item[0] == best]


def _next_history_version(version: str) -> str:
    import re
    match = re.fullmatch(r"(.*?)(\d+)", version)
    return f"{match.group(1)}{int(match.group(2)) + 1}" if match else version + ".next"

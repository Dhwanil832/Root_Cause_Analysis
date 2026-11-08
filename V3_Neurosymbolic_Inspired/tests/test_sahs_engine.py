from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest

from sahs.config import SpecialistConfig
from sahs.contracts import CandidateLineage, SpecialistHistory
from sahs.delta import CandidateProposal, apply_candidate_delta, build_candidate_delta
from sahs.engine import SpecialistEngine
from sahs.engine_contracts import (
    CausalGraph,
    CausalRuleCandidate,
    Proposition,
    SourceChunk,
    InformationGap,
    SpecialistAssignment,
)
from sahs.history import InMemoryRunHistoryStore
from sahs.proposal import ProposalRequest
from sahs.solver.clingo_solver import ClingoCandidateSolver, ClingoUnavailableError
from sahs.solver.interface import SearchLimits, SolverCandidate
from sahs.validation import ProposalValidationError, validate_proposal_batch


def base_history():
    return SpecialistHistory(
        schema_version="1", specialist_scope_id="mechanical", history_version="h0",
        case_snapshot_id="case-1:s0", board_version="b0",
    )


def source_ref(excerpt="A leaking valve can cause hydraulic pressure loss."):
    return {
        "source_id": "manual-1", "source_version": "1", "chunk_id": "manual-1:0",
        "exact_text": excerpt, "source_relation": "quotation",
    }


def batch(**updates):
    value = {
        "schema_version": "1",
        "proposed_propositions": [
            {"proposition_id": "pressure-loss", "text": "Hydraulic pressure loss",
             "kind": "system_mechanism", "source_refs": [], "time_scope": None},
            {"proposition_id": "valve-leaked", "text": "The valve leaked during the incident",
             "kind": "incident_event", "source_refs": [], "time_scope": "incident"},
        ],
        "proposed_rules": [
            {"rule_id": "rule-leak-pressure", "antecedent_ids": ["valve-leaked"],
             "consequent_id": "pressure-loss", "relation": "may_cause", "modality": "can",
             "conditions": [], "time_constraint": None, "basis": "source_described",
             "source_refs": [source_ref()], "source_relation": "paraphrase", "vetted_rule_id": None},
            {"rule_id": "rule-pressure-beam", "antecedent_ids": ["pressure-loss"],
             "consequent_id": "beam-fell", "relation": "contributes_to", "modality": "may",
             "conditions": [], "time_constraint": None, "basis": "model_proposed",
             "source_refs": [], "source_relation": None, "vetted_rule_id": None},
        ],
        "clarification_items": [], "information_gaps": [],
    }
    value.update(updates)
    return value


def assignment(*, mode="initial", graph=None, budgets=None, history=None):
    graph = graph or CausalGraph((
        Proposition("beam-fell", "Carrier beam fell", "incident_event", "reported"),
    ))
    history = history or base_history()
    return SpecialistAssignment(
        schema_version="1", assignment_id="run-1", case_id="case-1",
        specialist_scope_id="mechanical", case_snapshot_id="case-1:s0",
        board_version="b0", history_version="h0", mode=mode,
        operation_goal="generate_alternatives", lead_direction={"focus": "upstream"},
        relevant_graph=graph,
        source_bundle=(SourceChunk(
            "manual-1", "1", "manual-1:0",
            "A leaking valve can cause hydraulic pressure loss.", "manual",
        ),),
        history=history,
        target_proposition_ids=("beam-fell",) if mode == "initial" else (),
        available_proposition_ids=tuple(graph.proposition_map()),
        initial_case_packet={"reported_outcome": "Carrier beam fell"} if mode == "initial" else None,
        focal_proposition_id="beam-fell" if mode == "advance" else None,
        budgets=budgets or {"max_targeted_expansion_calls": 1},
    )


class ScriptedProposer:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls_made = 0
        self.requests = []

    def propose(self, request: ProposalRequest):
        self.requests.append(request)
        self.calls_made += 1
        return self.responses.pop(0)


class TestProposalValidation(unittest.TestCase):
    def test_batch_can_dedupe_clarifications_and_information_gaps_together(self):
        response = batch(
            clarification_items=[
                {"id": "c1", "question": "What is a yolk?", "why_it_matters": "It identifies a component.",
                 "information_that_could_resolve_it": "Witness definition.",
                 "linked_proposition_ids": ["valve-leaked"], "linked_rule_ids": [],
                 "linked_candidate_ids": [], "linked_frontier_ids": []},
                {"id": "c2", "question": "What is a yolk?", "why_it_matters": "It identifies a component.",
                 "information_that_could_resolve_it": "Equipment drawing.",
                 "linked_proposition_ids": ["pressure-loss"], "linked_rule_ids": [],
                 "linked_candidate_ids": [], "linked_frontier_ids": []},
            ],
            information_gaps=[
                {"id": "g1", "question": "Did the valve leak during the event?",
                 "why_it_matters": "This tests incident occurrence.",
                 "information_that_could_resolve_it": "Incident inspection record.",
                 "linked_proposition_ids": ["valve-leaked"], "linked_rule_ids": [],
                 "linked_candidate_ids": [], "linked_frontier_ids": []},
                {"id": "g2", "question": "Did the valve leak during the event?",
                 "why_it_matters": "This tests incident occurrence.",
                 "information_that_could_resolve_it": "Maintenance log.",
                 "linked_proposition_ids": ["pressure-loss"], "linked_rule_ids": [],
                 "linked_candidate_ids": [], "linked_frontier_ids": []},
            ],
        )
        validated = validate_proposal_batch(response, assignment())
        self.assertEqual(len(validated.clarification_items), 1)
        self.assertEqual(set(validated.clarification_items[0].linked_proposition_ids),
                         {"valve-leaked", "pressure-loss"})
        self.assertEqual(len(validated.information_gaps), 1)
        self.assertEqual(set(validated.information_gaps[0].linked_proposition_ids),
                         {"valve-leaked", "pressure-loss"})
        self.assertIn("Incident inspection record", validated.information_gaps[0].information_that_could_resolve_it)
        self.assertIn("Maintenance log", validated.information_gaps[0].information_that_could_resolve_it)

    def test_general_manual_mechanism_does_not_promote_incident_event(self):
        result = validate_proposal_batch(
            batch(),
            assignment(),
        )
        events = {item.proposition_id: item for item in result.proposed_propositions}
        self.assertEqual(events["valve-leaked"].case_status, "hypothetical")
        self.assertEqual(events["pressure-loss"].case_status, "not_applicable")
        rule = result.proposed_rules[0]
        self.assertEqual(rule.basis, "source_described")
        self.assertEqual(rule.source_refs[0].start_offset, 0)
        self.assertEqual(rule.source_refs[0].end_offset, 50)

    def test_model_cannot_assign_event_status_or_other_unknown_fields(self):
        bad = batch(proposed_propositions=[{
            "proposition_id": "promoted", "text": "Valve leaked", "kind": "incident_event",
            "source_refs": [], "time_scope": None, "case_status": "reported",
        }])
        validated = validate_proposal_batch(bad, assignment())
        self.assertEqual(validated.proposed_propositions, ())
        self.assertIn("forbidden fields", validated.rejected_fragments[0].reason)

    def test_unknown_top_level_field_fails_strict_contract(self):
        with self.assertRaisesRegex(ProposalValidationError, "forbidden fields"):
            validate_proposal_batch(batch(root_cause="beam fell"), assignment())

    def test_duplicate_exact_excerpt_is_rejected_as_ambiguous(self):
        source = "A leaking valve can cause hydraulic pressure loss. A leaking valve can cause hydraulic pressure loss."
        case = replace(assignment(), source_bundle=(SourceChunk("manual-1", "1", "manual-1:0", source, "manual"),))
        validated = validate_proposal_batch(batch(), case)
        self.assertEqual(len(validated.proposed_rules), 1)  # the model-proposed rule survives
        self.assertEqual(len(validated.rejected_fragments), 1)
        self.assertIn("ambiguous", validated.rejected_fragments[0].reason)


class TestClingoSearch(unittest.TestCase):
    def setUp(self):
        self.solver = ClingoCandidateSolver()
        self.limits = SearchLimits(max_depth=4, max_models=64, timeout_seconds=2)

    def test_single_rule_returns_conditional_path_and_unestablished_assumption(self):
        graph = CausalGraph(
            (Proposition("outcome", "Outcome", "incident_event", "reported"),
             Proposition("leak", "Valve leaked", "incident_event", "hypothetical")),
            (CausalRuleCandidate("r1", ("leak",), "outcome", "may_cause", "can"),),
        )
        result = self.solver.search(graph, "outcome", self.limits)
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].rule_ids, ("r1",))
        self.assertEqual(result.candidates[0].assumptions, ("leak",))

    def test_multi_antecedent_rule_requires_all_conditions(self):
        graph = CausalGraph(
            tuple(Proposition(pid, pid, "component_state", status)
                  for pid, status in (("outcome", "reported"), ("load", "reported"),
                                      ("restraint-missing", "hypothetical"))),
            (CausalRuleCandidate("r1", ("load", "restraint-missing"), "outcome", "may_cause", "when"),),
        )
        result = self.solver.search(graph, "outcome", self.limits)
        self.assertEqual(result.candidates[0].reported_premise_ids, ("load",))
        self.assertEqual(result.candidates[0].assumptions, ("restraint-missing",))

    def test_distinct_causal_rules_are_alternative_answer_sets(self):
        graph = CausalGraph(
            tuple(Proposition(pid, pid, "incident_event", status)
                  for pid, status in (("outcome", "reported"), ("a", "hypothetical"), ("b", "hypothetical"))),
            (CausalRuleCandidate("ra", ("a",), "outcome", "may_cause", "can"),
             CausalRuleCandidate("rb", ("b",), "outcome", "may_cause", "can")),
        )
        result = self.solver.search(graph, "outcome", self.limits)
        self.assertEqual({item.rule_ids for item in result.candidates}, {("ra",), ("rb",)})

    def test_reported_premise_is_not_recast_as_assumption(self):
        graph = CausalGraph(
            (Proposition("outcome", "Outcome", "incident_event", "reported"),
             Proposition("pressure", "Pressure loss reported", "case_claim", "reported")),
            (CausalRuleCandidate("r1", ("pressure",), "outcome", "contributes_to", "may"),),
        )
        candidate = self.solver.search(graph, "outcome", self.limits).candidates[0]
        self.assertEqual(candidate.reported_premise_ids, ("pressure",))
        self.assertEqual(candidate.assumptions, ())

    def test_generic_mechanism_is_not_reported_as_incident_assumption(self):
        graph = CausalGraph(
            (Proposition("outcome", "Outcome", "incident_event", "reported"),
             Proposition("pressure", "Hydraulic pressure loss", "system_mechanism", "not_applicable")),
            (CausalRuleCandidate("r1", ("pressure",), "outcome", "may_cause", "can"),),
        )
        result = self.solver.search(graph, "outcome", self.limits)
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.open_frontier_ids, ("pressure",))

    def test_unsupported_cycle_is_not_returned_as_explanation(self):
        graph = CausalGraph(
            (Proposition("outcome", "Outcome", "incident_event", "reported"),
             Proposition("a", "A", "component_state", "hypothetical"),
             Proposition("b", "B", "component_state", "hypothetical")),
            (CausalRuleCandidate("r0", ("a",), "outcome", "may_cause", "can"),
             CausalRuleCandidate("ra", ("b",), "a", "may_cause", "can"),
             CausalRuleCandidate("rb", ("a",), "b", "may_cause", "can")),
        )
        result = self.solver.search(graph, "outcome", self.limits)
        self.assertFalse(any(set(item.rule_ids) == {"r0", "ra", "rb"} for item in result.candidates))

    def test_solver_model_cap_is_reported_as_partial(self):
        graph = CausalGraph(
            (Proposition("outcome", "Outcome", "incident_event", "reported"),
             Proposition("a", "A", "component_state", "hypothetical"),
             Proposition("b", "B", "component_state", "hypothetical")),
            (CausalRuleCandidate("ra", ("a",), "outcome", "may_cause", "can"),
             CausalRuleCandidate("rb", ("b",), "outcome", "may_cause", "can")),
        )
        result = self.solver.search(graph, "outcome", SearchLimits(2, 1, 2))
        self.assertEqual(result.status, "partial_budget")
        self.assertEqual(len(result.candidates), 1)


class TestSpecialistEngine(unittest.TestCase):
    def test_end_to_end_initial_proposal_search_delta_and_no_op(self):
        first = batch()
        second = {
            "schema_version": "1", "proposed_propositions": [
                {"proposition_id": "seal-damaged", "text": "Seal damage", "kind": "component_state",
                 "source_refs": [], "time_scope": None},
            ], "proposed_rules": [
                {"rule_id": "rule-seal-leak", "antecedent_ids": ["seal-damaged"],
                 "consequent_id": "valve-leaked", "relation": "enables", "modality": "may",
                 "conditions": [], "time_constraint": None, "basis": "model_proposed",
                 "source_refs": [], "source_relation": None, "vetted_rule_id": None},
            ], "clarification_items": [], "information_gaps": [],
        }
        proposer = ScriptedProposer([first, second])
        store = InMemoryRunHistoryStore()
        engine = SpecialistEngine(proposer, ClingoCandidateSolver(), store)
        result = engine.run(assignment())
        self.assertIn(result.status, {"open_frontier", "completed"})
        self.assertTrue(result.candidates)
        candidate = result.candidates[0]
        self.assertIn("beam-fell", candidate.proposition_ids)
        self.assertTrue(any("seal-damaged" in item.assumptions for item in result.candidates))
        self.assertEqual(
            {item.proposition_id: item.case_status for item in result.graph_delta.propositions}["pressure-loss"],
            "not_applicable",
        )
        self.assertTrue(any(item.basis == "source_described" for item in result.graph_delta.rules))
        self.assertEqual(result.resource_usage["targeted_expansion_calls"], 1)
        self.assertEqual(result.resource_usage["proposal_calls"], 2)
        self.assertEqual(result.resource_usage["solver_calls"], 2)
        self.assertEqual(proposer.requests[1].target_proposition_id, "valve-leaked")
        self.assertEqual(result.updated_history.history_version, "h1")
        self.assertEqual(len(result.candidate_operations), 2)
        prior_calls = proposer.calls_made
        replay = engine.run(assignment())
        self.assertEqual(replay.status, "no_op")
        self.assertEqual(proposer.calls_made, prior_calls)

    def test_targeted_expansion_rejects_a_different_frontier(self):
        unrelated = {
            "schema_version": "1", "proposed_propositions": [
                {"proposition_id": "seal-damaged", "text": "Seal damage", "kind": "component_state",
                 "source_refs": [], "time_scope": None},
            ], "proposed_rules": [
                {"rule_id": "rule-seal-leak", "antecedent_ids": ["seal-damaged"],
                 "consequent_id": "beam-fell", "relation": "enables", "modality": "may",
                 "conditions": [], "time_constraint": None, "basis": "model_proposed",
                 "source_refs": [], "source_relation": None, "vetted_rule_id": None},
            ], "clarification_items": [], "information_gaps": [],
        }
        proposer = ScriptedProposer([batch(), unrelated])
        result = SpecialistEngine(proposer, ClingoCandidateSolver(), InMemoryRunHistoryStore()).run(assignment())
        self.assertEqual(result.status, "open_frontier")
        self.assertEqual(result.resource_usage["targeted_expansion_calls"], 0)
        self.assertTrue(any("assigned frontier" in item for item in result.diagnostics))

    def test_revision_gap_linked_only_to_candidate_is_saved_as_dependency(self):
        prior = CandidateLineage("prior", dependent_proposition_ids=frozenset({"beam-fell"}),
                                 content_fingerprint="prior-fingerprint")
        hist = replace(base_history(), candidates=(prior,))
        case = assignment(mode="revision", history=hist)
        prepared = SimpleNamespace(affected_candidate_ids=("prior",), focal_candidate_ids=())
        graph = CausalGraph(
            (Proposition("beam-fell", "Carrier beam fell", "incident_event", "reported"),
             Proposition("valve-leaked", "Valve leaked", "incident_event", "hypothetical")),
            (CausalRuleCandidate("r1", ("valve-leaked",), "beam-fell", "may_cause", "may"),),
        )
        gap = InformationGap("need-valve-status", "Whether the valve leaked", "It changes the route",
                             "A maintenance record", linked_candidate_ids=("prior",))
        engine = SpecialistEngine(ScriptedProposer([]), ClingoCandidateSolver(), InMemoryRunHistoryStore())
        proposals, _ = engine._candidate_proposals(
            case, prepared, graph,
            [SolverCandidate("beam-fell", ("beam-fell", "valve-leaked"), ("r1",), (),
                             ("valve-leaked",), ("use:r1",))],
            (gap,), (),
        )
        self.assertEqual(proposals[0].dependent_information_need_ids, frozenset({"need-valve-status"}))

    def test_revision_convergence_merges_both_affected_candidate_branches(self):
        old_a = CandidateLineage("old-a", dependent_proposition_ids=frozenset({"beam-fell"}),
                                 content_fingerprint="old-a-fp")
        old_b = CandidateLineage("old-b", dependent_proposition_ids=frozenset({"beam-fell"}),
                                 content_fingerprint="old-b-fp")
        hist = replace(base_history(), candidates=(old_a, old_b))
        case = assignment(mode="revision", history=hist)
        prepared = SimpleNamespace(affected_candidate_ids=("old-a", "old-b"), focal_candidate_ids=())
        graph = CausalGraph(
            (Proposition("beam-fell", "Carrier beam fell", "incident_event", "reported"),
             Proposition("actuator-failed", "Actuator failed", "incident_event", "hypothetical")),
            (CausalRuleCandidate("r1", ("actuator-failed",), "beam-fell", "may_cause", "may"),),
        )
        engine = SpecialistEngine(ScriptedProposer([]), ClingoCandidateSolver(), InMemoryRunHistoryStore())
        proposals, _ = engine._candidate_proposals(
            case, prepared, graph,
            [SolverCandidate("beam-fell", ("beam-fell", "actuator-failed"), ("r1",), (),
                             ("actuator-failed",), ("use:r1",))],
            (), (),
        )
        deltas = build_candidate_delta(assignment_id="merge-run", history=hist, proposals=proposals)
        deltas += engine._merge_converged_branches(deltas, proposals, hist, ())
        self.assertEqual({item.operation.value for item in deltas}, {"revise", "merge"})
        updated = apply_candidate_delta(hist, deltas, new_history_version="h1")
        by_id = updated.candidate_map()
        self.assertEqual(by_id["old-a"].status.value, "superseded")
        self.assertEqual(by_id["old-b"].status.value, "superseded")
        merged = next(item for item in by_id.values() if item.candidate_id not in {"old-a", "old-b"})
        self.assertEqual(set(merged.parent_candidate_ids), {"old-a", "old-b"})

    def test_revision_convergence_merges_into_existing_active_candidate(self):
        old_a = CandidateLineage("old-a", dependent_proposition_ids=frozenset({"beam-fell"}),
                                 content_fingerprint="old-a-fp")
        old_b = CandidateLineage("old-b", dependent_proposition_ids=frozenset({"beam-fell"}),
                                 content_fingerprint="old-b-fp")
        same = CandidateLineage("same", dependent_proposition_ids=frozenset({"beam-fell"}),
                                content_fingerprint="converged-fp")
        hist = replace(base_history(), candidates=(old_a, old_b, same))
        proposal = CandidateProposal(
            content_fingerprint="converged-fp",
            dependent_proposition_ids=frozenset({"beam-fell", "actuator-failed"}),
            dependent_rule_ids=frozenset({"r1"}),
            parent_candidate_ids=("old-a", "old-b"),
            revises_candidate_id="old-a",
        )
        deltas = build_candidate_delta(
            assignment_id="merge-existing", history=hist, proposals=(proposal,)
        )
        self.assertEqual([item.operation.value for item in deltas], ["merge"])
        engine = SpecialistEngine(ScriptedProposer([]), ClingoCandidateSolver(), InMemoryRunHistoryStore())
        deltas += engine._merge_converged_branches(deltas, (proposal,), hist, ())
        self.assertEqual([item.operation.value for item in deltas], ["merge", "merge"])
        updated = apply_candidate_delta(hist, deltas, new_history_version="h1")
        by_id = updated.candidate_map()
        self.assertEqual(by_id["old-a"].status.value, "superseded")
        self.assertEqual(by_id["old-b"].status.value, "superseded")
        self.assertEqual(by_id["same"].status.value, "active")
        self.assertEqual(set(by_id["same"].parent_candidate_ids), {"old-a", "old-b"})

    def test_bad_budgets_fail_before_proposal_call(self):
        proposer = ScriptedProposer([batch()])
        engine = SpecialistEngine(proposer, ClingoCandidateSolver(), InMemoryRunHistoryStore())
        result = engine.run(assignment(budgets={"max_depth": -1}))
        self.assertEqual(result.status, "invalid_input")
        self.assertEqual(proposer.calls_made, 0)

    def test_stale_snapshot_stops_before_proposal_call(self):
        proposer = ScriptedProposer([batch()])
        stale = replace(assignment(), board_version="b-stale")
        engine = SpecialistEngine(proposer, ClingoCandidateSolver(), InMemoryRunHistoryStore())
        result = engine.run(stale)
        self.assertEqual(result.status, "stale_input")
        self.assertEqual(proposer.calls_made, 0)

    def test_model_schema_failure_returns_invalid_proposal_without_solver(self):
        proposer = ScriptedProposer([{"schema_version": "1", "root_cause": "claimed"}])
        engine = SpecialistEngine(proposer, ClingoCandidateSolver(), InMemoryRunHistoryStore())
        result = engine.run(assignment())
        self.assertEqual(result.status, "invalid_proposal")
        self.assertEqual(result.candidates, ())


if __name__ == "__main__":
    unittest.main()

"""The Specialist's prompt is trimmed to leave room in the window for its answer."""
from __future__ import annotations

from dataclasses import replace
import json
import sys
import unittest

from sahs.config import SpecialistConfig
from sahs.engine import SpecialistEngine
from sahs.engine_contracts import CausalGraph, CausalRuleCandidate, Proposition, SourceChunk, SourceReference
from sahs.history import InMemoryRunHistoryStore
from sahs.prompt_builder import build_proposal_request, estimate_prompt_tokens
from sahs.solver.clingo_solver import ClingoCandidateSolver
from tests.test_sahs_engine import ScriptedProposer, assignment, batch

HASH = "sha256:" + "a" * 64


def ref(source_id):
    return SourceReference(source_id, HASH, f"{source_id}:{HASH}:0", "quoted passage " * 4, 0, 60, "case_document", "quotation")


def big_assignment():
    """A target with one cited document, many uncited documents, and far-off rules."""
    props = [Proposition("beam-fell", "Carrier beam fell", "incident_event", "reported", (ref("cited"),))]
    rules = []
    for i in range(30):
        props.append(Proposition(f"p{i}", f"Distant condition number {i}", "system_mechanism", "hypothetical",
                                 (ref(f"doc{i}"),)))
        rules.append(CausalRuleCandidate(f"r{i}", (f"p{i}",), f"p{(i + 1) % 30}", "may_cause", "possible",
                                         (), None, "source_described", (ref(f"doc{i}"),), "paraphrase"))
    rules.append(CausalRuleCandidate("near", ("p0",), "beam-fell", "may_cause", "possible",
                                     (), None, "model_proposed", (), None))
    sources = tuple(SourceChunk(sid, HASH, f"{sid}:{HASH}:0", f"Text of {sid}. " * 20, "case_document")
                    for sid in ["cited", *(f"doc{i}" for i in range(30))])
    graph = CausalGraph(tuple(props), tuple(rules))
    return replace(assignment(), relevant_graph=graph, source_bundle=sources,
                   available_proposition_ids=tuple(graph.proposition_map()),
                   assessor_annotations=(
                       {"annotation_id": "A1", "target_id": "beam-fell", "material_id": "doc5",
                        "exact_text": "x", "effect": "neutral", "rationale": "r" * 400},
                       {"annotation_id": "A2", "target_id": "beam-fell", "material_id": "doc6",
                        "exact_text": "y", "effect": "supports", "rationale": "r" * 400}))


class Trimming(unittest.TestCase):
    def setUp(self):
        self.whole = build_proposal_request(big_assignment()).context

    def test_without_a_budget_the_prompt_is_sent_whole(self):
        self.assertNotIn("omitted_for_length", self.whole)
        self.assertEqual(len(self.whole["source_bundle"]), 31)

    def test_a_prompt_within_budget_is_unchanged(self):
        fitted = build_proposal_request(big_assignment(), max_prompt_tokens=10 ** 6).context
        self.assertEqual(fitted, self.whole)

    def test_an_oversized_prompt_is_trimmed_to_fit_keeping_what_the_target_rests_on(self):
        budget = estimate_prompt_tokens(self.whole) // 3
        request = build_proposal_request(big_assignment(), max_prompt_tokens=budget)
        context = request.context
        self.assertLessEqual(estimate_prompt_tokens(context), budget)
        same = lambda c: json.dumps((c["schema"], c["task"]))
        self.assertEqual(same(context), same(self.whole))
        kept = [s["source_id"] for s in context["source_bundle"]]
        self.assertIn("cited", kept)
        self.assertIn("beam-fell", [p["proposition_id"] for p in context["relevant_graph"]["propositions"]])
        self.assertIn("relevant_graph source_refs reduced to source_id", request.omitted)
        self.assertTrue(any(o.startswith("source_bundle document doc") for o in request.omitted))
        dropped = sum(o.startswith("source_bundle document") for o in request.omitted)
        self.assertIn(f"{dropped} source_bundle documents left out", context["omitted_for_length"])

    def test_trims_run_from_least_to_most_useful(self):
        omitted = build_proposal_request(big_assignment(), max_prompt_tokens=1).omitted
        kinds = [("refs" if o.startswith("relevant_graph source_refs") else
                  "graph" if o.startswith("relevant_graph items") else
                  # "cited" backs the target; doc6 backs a non-neutral annotation
                  "cited doc" if o in ("source_bundle document cited", "source_bundle document doc6") else
                  "doc" if o.startswith("source_bundle") else o.rsplit(" ", 1)[1]) for o in omitted]
        runs = [k for i, k in enumerate(kinds) if i == 0 or kinds[i - 1] != k]
        self.assertEqual(runs, ["refs", "doc", "A1", "graph", "cited doc", "A2"])
        self.assertEqual(omitted[1], "source_bundle document doc29")  # latest uncited document first

    def test_the_assignment_itself_is_not_changed(self):
        original = big_assignment()
        build_proposal_request(original, max_prompt_tokens=100)
        self.assertEqual(original, big_assignment())


class EngineUsesTheBudget(unittest.TestCase):
    def test_the_configured_budget_reaches_the_proposer_and_the_omissions_are_reported(self):
        whole = estimate_prompt_tokens(build_proposal_request(big_assignment()).context)
        proposer = ScriptedProposer([batch(), batch(proposed_propositions=[], proposed_rules=[])])
        engine = SpecialistEngine(proposer, ClingoCandidateSolver(), InMemoryRunHistoryStore(),
                                  SpecialistConfig(max_prompt_tokens=whole // 3, max_propositions=80,
                                                   max_rules=80))
        output = engine.run(big_assignment())
        self.assertLessEqual(estimate_prompt_tokens(proposer.requests[0].context), whole // 3)
        self.assertTrue(output.resource_usage["prompt_omissions"])


class RuntimeReservesTheAnswer(unittest.TestCase):
    def test_the_reserve_is_taken_from_the_context_window(self):
        from orchestration.v3_runtime import V3CaseRuntime
        from tests.test_prompt_guard_and_folding import LEGACY_ROOT
        sys.path.insert(0, str(LEGACY_ROOT))
        try:
            reserved = V3CaseRuntime.from_ollama("case", model="m", num_ctx=16384, answer_reserve_tokens=6000)
            whole = V3CaseRuntime.from_ollama("case", model="m", num_ctx=16384)
        finally:
            sys.path.remove(str(LEGACY_ROOT))
        self.assertEqual(reserved.bridge.specialist_engine.config.max_prompt_tokens, 10384)
        self.assertIsNone(whole.bridge.specialist_engine.config.max_prompt_tokens)
        self.assertEqual((reserved.model_client.think, whole.model_client.think), (None, None))

    def test_the_reasoning_effort_reaches_the_shared_model_client(self):
        from orchestration.v3_runtime import V3CaseRuntime
        from tests.test_prompt_guard_and_folding import LEGACY_ROOT
        sys.path.insert(0, str(LEGACY_ROOT))
        try:
            runtime = V3CaseRuntime.from_ollama("case", model="m", num_ctx=16384, think="high")
        finally:
            sys.path.remove(str(LEGACY_ROOT))
        self.assertEqual(runtime.model_client.think, "high")


if __name__ == "__main__":
    unittest.main()

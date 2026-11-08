"""Oversized prompts are refused, not cut; the Specialist sees compact annotations;
restated claims and repeated questions fold into the board; searches per claim are capped."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

from cferp import RoleResult
from cferp.contracts import JobState, Role
from cferp.integration import MAX_SPECIALIST_ANNOTATIONS, specialist_annotations
from cferp.workflow import statement_meaning
from tests.test_cferp_workflow import setup_workflow

LEGACY_ROOT = (Path(__file__).resolve().parents[2] / "V1_V2_Prompt_and_Rules" / "source"
               / "RCA_Version_Labeled_Codebase")


def ollama_client():
    sys.path.insert(0, str(LEGACY_ROOT))
    try:
        from shared.llm import ollama_client as module
    finally:
        sys.path.remove(str(LEGACY_ROOT))
    return module


OVERFLOW = json.dumps({"error": json.dumps({"error": {
    "code": 400, "message": "request (31163 tokens) exceeds the available context size (16384 tokens), "
    "try increasing it", "type": "exceed_context_size_error", "n_prompt_tokens": 31163, "n_ctx": 16384}})})


def http_error(code, body):
    return urllib.error.HTTPError("http://x/api/chat", code, "err", {}, io.BytesIO(body.encode()))


class Reply:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self, *_):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class PromptGuard(unittest.TestCase):
    def test_an_oversized_prompt_is_refused_with_its_token_count_and_not_retried(self):
        module = ollama_client()
        model = module.OllamaChatModel("m", num_ctx=16384, retries=3)
        with patch.object(module.urllib.request, "urlopen", side_effect=http_error(400, OVERFLOW)) as sent:
            with self.assertRaises(module.PromptTooLarge) as caught:
                model.ask("sahs_proposal", "system", {"x": 1})
        self.assertEqual((caught.exception.prompt_tokens, caught.exception.context_tokens), (31163, 16384))
        self.assertEqual(sent.call_count, 1)
        self.assertEqual(model.raw_responses[-1]["outcome"], "prompt_exceeds_context")

    def test_requests_ask_ollama_to_refuse_rather_than_truncate(self):
        module = ollama_client()
        bodies = []

        def capture(request, timeout):
            bodies.append(json.loads(request.data))
            return Reply({"message": {"content": "{\"ok\": true}"}, "done_reason": "stop"})

        for flag in (False, True):
            with patch.object(module.urllib.request, "urlopen", side_effect=capture):
                module.OllamaChatModel("m", truncate_prompt=flag).ask("t", "s", {})
        self.assertIs(bodies[0]["truncate"], False)
        self.assertNotIn("truncate", bodies[1])

    def test_reasoning_effort_is_sent_only_when_set(self):
        module = ollama_client()
        bodies = []

        def capture(request, timeout):
            bodies.append(json.loads(request.data))
            return Reply({"message": {"content": "{\"ok\": true}"}, "done_reason": "stop"})

        for think in ("low", None):
            with patch.object(module.urllib.request, "urlopen", side_effect=capture):
                module.OllamaChatModel("m", think=think).ask("t", "s", {})
        self.assertEqual(bodies[0]["think"], "low")
        self.assertNotIn("think", bodies[1])

    def test_another_bad_request_is_an_ordinary_failure(self):
        module = ollama_client()
        with patch.object(module.urllib.request, "urlopen", side_effect=http_error(400, '{"error":"bad format"}')):
            with self.assertRaises(module.ModelFailure) as caught:
                module.OllamaChatModel("m").ask("t", "s", {})
        self.assertNotIsInstance(caught.exception, module.PromptTooLarge)
        self.assertIn("after 1 HTTP attempts", str(caught.exception))


def annotation(i, effect="neutral", status="current"):
    return {"assessment_id": f"A{i}", "claim_id": "H1", "material_id": "DOC-1",
            "material_version": "sha256:" + "f" * 64, "passage_id": f"p{i}", "exact_text": f"text {i}",
            "effect": effect, "rationale": "r" * 900, "assignment_id": f"job-{i}",
            "manifest": {"source_versions": ["x" * 80] * 10}, "prior_assessment_ids": [], "status": status}


class SpecialistAnnotations(unittest.TestCase):
    def test_bookkeeping_is_dropped_and_the_reading_kept(self):
        row, = specialist_annotations([annotation(1, "supports")])
        self.assertEqual(row, {"annotation_id": "A1", "target_id": "H1", "material_id": "DOC-1",
                               "exact_text": "text 1", "effect": "supports", "rationale": "r" * 400})

    def test_the_specialist_assignment_carries_the_compact_form(self):
        from cferp.integration import sahs_assignment_from_cferp
        wf, _ = setup_workflow()
        revisit = wf.assignments[wf._assignment(
            role=Role.SPECIALIST, owner_id="lead-routed", purpose="revisit", target_ids=("H0",),
            dependencies=("H0",), context={"mode": "revision", "assessor_annotations": (annotation(1),)}).assignment_id]
        row, = sahs_assignment_from_cferp(revisit, wf).assessor_annotations
        self.assertNotIn("manifest", row)
        self.assertEqual(row["annotation_id"], "A1")

    def test_superseded_annotations_are_left_out(self):
        self.assertEqual(specialist_annotations([annotation(1, status="superseded")]), ())

    def test_evidence_bearing_effects_are_kept_before_neutral_ones(self):
        rows = [annotation(i) for i in range(20)] + [annotation(99, "contradicts")]
        kept = specialist_annotations(rows)
        self.assertEqual(len(kept), MAX_SPECIALIST_ANNOTATIONS)
        self.assertIn("A99", [r["annotation_id"] for r in kept])
        self.assertIn("A19", [r["annotation_id"] for r in kept])  # newest neutral kept
        self.assertNotIn("A0", [r["annotation_id"] for r in kept])  # oldest neutral dropped


class Meaning(unittest.TestCase):
    def test_restatements_match_and_opposites_do_not(self):
        same = statement_meaning("Keeper plate was engaged on the link arm during carrier raise.")
        self.assertEqual(same, statement_meaning("Keeper plate engaged on the link arm during the carrier raise"))
        self.assertNotEqual(same, statement_meaning("Keeper plate was not engaged on the link arm during carrier raise."))
        self.assertNotEqual(statement_meaning("Hydraulic pressure was nominal at the raise"),
                            statement_meaning("Hydraulic pressure was low at the raise"))


def specialist_turn(wf, assignment, result_id, payload):
    if wf.lead.work[assignment.assignment_id].state == JobState.QUEUED:
        wf.start_assignment(assignment.assignment_id)
    return wf.submit_specialist_result(RoleResult(result_id, assignment.assignment_id, Role.SPECIALIST,
                                                  assignment.manifest, payload))


def claim(cid, text, parents=("H0",)):
    return {"claim_id": cid, "text": text, "branch_id": "B1", "kind": "incident_event",
            "parent_claim_ids": list(parents)}


def need(nid, targets, question, **extra):
    return {"need_id": nid, "target_ids": list(targets), "slots": [{"slot_id": f"{nid}-s", "description": question}],
            **extra}


VALVE = "The isolation valve was closed during the raise."


class FoldClaims(unittest.TestCase):
    def setUp(self):
        self.wf, specialist = setup_workflow()
        specialist_turn(self.wf, specialist, "SR-1", {"claims": [claim("H1", VALVE)]})
        self.next = self.wf.assignments[self.wf._assignment(
            role=Role.SPECIALIST, owner_id="lead-routed", purpose="revisit", target_ids=("H1",),
            dependencies=("H1",), context={"mode": "revision"}).assignment_id]

    def test_a_restated_claim_folds_into_the_board_claim_and_its_links_follow(self):
        specialist_turn(self.wf, self.next, "SR-2", {
            "claims": [claim("H1-again", "Isolation valve closed during raise"), claim("H2", "The carrier dropped")],
            "causal_links": [{"link_id": "L1", "source_claim_ids": ["H1-again"], "target_claim_id": "H2"}]})
        self.assertNotIn("H1-again", self.wf.claims)
        self.assertEqual(self.wf.causal_links["L1"].source_claim_ids, ("H1",))
        self.assertEqual(self.wf.claim_aliases, {"H1-again": "H1"})
        self.assertTrue(any(e.kind == "duplicates_folded" for e in self.wf.lead.events))

    def test_an_opposite_claim_is_kept(self):
        specialist_turn(self.wf, self.next, "SR-2", {"claims": [claim("H1-not", "The isolation valve was not closed during the raise.")]})
        self.assertIn("H1-not", self.wf.claims)

    def test_a_later_result_may_cite_the_folded_id(self):
        specialist_turn(self.wf, self.next, "SR-2", {"claims": [claim("H1-again", "Isolation valve closed during raise")]})
        third = self.wf.assignments[self.wf._assignment(
            role=Role.SPECIALIST, owner_id="lead-routed", purpose="revisit", target_ids=("H1",),
            dependencies=("H1",), context={"mode": "revision"}).assignment_id]
        specialist_turn(self.wf, third, "SR-3", {"claims": [claim("H3", "Stored energy was released", ("H1-again",))]})
        self.assertEqual(self.wf.claims["H3"].parent_claim_ids, ("H1",))

    def test_a_link_that_folding_turns_into_a_self_loop_is_dropped(self):
        specialist_turn(self.wf, self.next, "SR-2", {
            "claims": [claim("H1-again", "Isolation valve closed during raise")],
            "causal_links": [{"link_id": "L1", "source_claim_ids": ["H1-again"], "target_claim_id": "H1"}]})
        self.assertNotIn("L1", self.wf.causal_links)


class FoldNeeds(unittest.TestCase):
    def setUp(self):
        self.wf, specialist = setup_workflow()
        specialist_turn(self.wf, specialist, "SR-1", {
            "claims": [claim("H1", VALVE), claim("H2", "The carrier dropped")],
            "needs": [need("N1", ["H1"], "Was the isolation valve closed during the raise?")]})

    def turn(self, *needs):
        nxt = self.wf.assignments[self.wf._assignment(
            role=Role.SPECIALIST, owner_id="lead-routed", purpose="revisit", target_ids=("H1",),
            dependencies=("H1",), context={"mode": "revision"}).assignment_id]
        return specialist_turn(self.wf, nxt, f"SR-{len(self.wf.lead.events)}", {"needs": list(needs)})

    def test_the_same_question_on_the_same_claim_folds(self):
        self.turn(need("N2", ["H1"], "Was the isolation valve closed during raise?"))
        self.assertNotIn("N2", self.wf.lead.needs)
        self.assertEqual(self.wf.need_aliases, {"N2": "N1"})

    def test_a_question_reaching_another_claim_is_kept(self):
        self.turn(need("N2", ["H1", "H2"], "Was the isolation valve closed during the raise?"))
        self.assertIn("N2", self.wf.lead.needs)

    def test_a_question_with_another_scope_is_kept(self):
        self.turn(need("N2", ["H1"], "Was the isolation valve closed during the raise?", source_scope=["DOC-1"]))
        self.assertIn("N2", self.wf.lead.needs)


def searches_on(wf, claim_id, *states):
    return [w for w in wf.lead.work.values() if w.role == Role.EVIDENCE_WORKER
            and claim_id in w.target_ids and w.state in states]


class SearchCap(unittest.TestCase):
    def test_at_most_two_searches_per_claim_are_queued_and_the_rest_wait(self):
        wf, specialist = setup_workflow()
        specialist_turn(wf, specialist, "SR-1", {"claims": [claim("H1", VALVE)], "needs": [
            need("N1", ["H1"], "Was the isolation valve closed?"),
            need("N2", ["H1"], "Who signed the isolation checklist?"),
            need("N3", ["H1"], "What pressure did the gauge record?")]})
        active = searches_on(wf, "H1", JobState.QUEUED, JobState.RUNNING)
        self.assertEqual(len(active), 2)
        first = wf.assignments[active[0].work_id]
        wf.start_assignment(first.assignment_id)
        wf.submit_worker_result(RoleResult("EW-1", first.assignment_id, Role.EVIDENCE_WORKER, first.manifest,
                                           {"packets": [], "requests": []}))
        searched = {n for w in searches_on(wf, "H1", JobState.QUEUED, JobState.RUNNING, JobState.RETURNED)
                    for n in w.need_ids}
        self.assertEqual(searched, {"N1", "N2", "N3"})

    def test_a_search_gone_stale_mid_run_keeps_its_slot_and_its_reissue_waits(self):
        wf, specialist = setup_workflow()
        specialist_turn(wf, specialist, "SR-1", {"claims": [claim("H1", VALVE)], "needs": [
            need("N1", ["H1"], "Was the isolation valve closed?"),
            need("N2", ["H1"], "Who signed the isolation checklist?"),
            need("N3", ["H1"], "What pressure did the gauge record?")]})
        running, waiting = (wf.assignments[w.work_id] for w in searches_on(wf, "H1", JobState.QUEUED))
        wf.start_assignment(running.assignment_id)
        wf.lead.stale_dependents(("H1",), reason="board changed")
        wf._queue_available()
        queued = lambda: {n for w in searches_on(wf, "H1", JobState.QUEUED, JobState.RUNNING) for n in w.need_ids}
        self.assertEqual(queued(), {waiting.need_ids[0]})  # the stale call still holds its slot; N3 waits
        wf.submit_worker_result(RoleResult("EW-1", running.assignment_id, Role.EVIDENCE_WORKER,
                                           running.manifest, {"packets": [], "requests": []}))
        self.assertEqual(queued(), {waiting.need_ids[0], running.need_ids[0]})  # reissued into the freed slot


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from types import SimpleNamespace

from cferp.contracts import Role, VersionManifest
from cferp.integration import (IntegrationError, MAX_REVIEW_LINK_CHARS, MAX_REVIEW_LINKS,
                               hera_task_from_cferp, hera_result_to_cferp,
                               ew_result_to_cferp, sahs_result_to_cferp,
                               sahs_sources_from_materials)
from cferp.workflow import Assignment
from hera1 import AssessmentTask, EvidenceMaterial, Hera1Engine
from hera1.config import AssessorConfig
from hera1.validation import validate_task
from hera1.contracts import AssessmentResult, VersionSnapshot
from sahs.engine_contracts import CausalGraph, CausalRuleCandidate, InformationGap, Proposition, SourceReference
from ewv3.contracts import (CandidateLink, Coverage, EvidenceWorkerResult, RequestDraft,
                             SearchPassStatus, SlotResult, WorkPhase)


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)

    def ask(self, task, system, payload):
        return self.responses.pop(0)


class Versions:
    def read(self, case_id, material_ids):
        return VersionSnapshot("case:s1", "1", {"D1": "v1", "D2": "v2"})


def cferp_assignment(task_kind="evidence_review"):
    return Assignment(
        "assessor-a", Role.ASSESSOR, "assessor-pair:ew-a", "review", ("H1",), ("N1",),
        ("H1",), VersionManifest("C1", "case:s1", 1, "materials:1:v1", (("D1", "v1", "h1"),)),
        context={"source_work_item_id": "ew-work"},
    )


class JointAdapterTests(unittest.TestCase):
    def test_sahs_source_ids_match_lead_material_ids_and_keep_version(self):
        chunks = sahs_sources_from_materials(({
            "material_id": "DOC-1", "version": "v3", "source_kind": "inspection_log",
            "content": "Valve was inspected at 10:14.",
        },))
        self.assertEqual((chunks[0].source_id, chunks[0].source_version), ("DOC-1", "v3"))
        self.assertEqual(chunks[0].text, "Valve was inspected at 10:14.")

    def test_sahs_delta_maps_to_lead_with_material_ids_and_open_gaps(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1", (("DOC-1", "v1", "h1"),))
        lead_assignment = Assignment("sa-a", Role.SPECIALIST, "mechanical", "expand",
            ("H0",), (), ("H0",), manifest)
        passage = SourceReference("DOC-1", "v1", "DOC-1:v1:0",
            "A leaking valve can cause hydraulic pressure loss.", 0, 50, "manual", "paraphrase")
        proposed = SimpleNamespace(
            assignment_id="sa-a", case_snapshot_id="case:s1", board_version="1", status="open_frontier",
            graph_delta=CausalGraph(
                (Proposition("leak", "Valve leaked", "incident_event", "hypothetical"),
                 Proposition("pressure", "Pressure loss", "system_mechanism", "not_applicable")),
                (CausalRuleCandidate("r1", ("leak",), "pressure", "may_cause", "can",
                    basis="source_described", source_refs=(passage,), source_relation="paraphrase"),)),
            information_gaps=(InformationGap("N1", "Did the valve leak during the event?", "Tests occurrence",
                "Inspection record", linked_proposition_ids=("leak",)),),
            clarification_items=(),
        )
        normalized = sahs_result_to_cferp(proposed, lead_assignment)
        self.assertEqual(normalized.payload["causal_links"][0]["source_refs"], ("DOC-1",))
        self.assertEqual(normalized.payload["causal_links"][0]["source_text"], passage.exact_text)
        self.assertEqual(normalized.payload["needs"][0]["target_ids"], ("leak",))

    def test_sahs_alternatives_keep_separate_branch_membership(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1")
        lead_assignment = Assignment("sa-multi", Role.SPECIALIST, "mechanical", "alternatives",
            ("H0",), (), ("H0",), manifest)
        graph = CausalGraph((Proposition("A", "Cause A", "incident_event", "hypothetical"),
            Proposition("B", "Cause B", "incident_event", "hypothetical"),
            Proposition("shared", "Shared condition", "component_state", "hypothetical")), ())
        proposed = SimpleNamespace(assignment_id="sa-multi", case_snapshot_id="case:s1", board_version="1",
            status="completed", graph_delta=graph, information_gaps=(), clarification_items=(), candidates=(
                SimpleNamespace(candidate_id="cand-A", proposition_ids=("A", "shared"), rule_ids=()),
                SimpleNamespace(candidate_id="cand-B", proposition_ids=("B", "shared"), rule_ids=()),
            ))
        normalized = sahs_result_to_cferp(proposed, lead_assignment)
        branches = {row["claim_id"]: row["branch_id"] for row in normalized.payload["claims"]}
        self.assertEqual(branches["A"], "sahs:candidate:cand-A")
        self.assertEqual(branches["B"], "sahs:candidate:cand-B")
        self.assertTrue(branches["shared"].startswith("sahs:shared:"))
        self.assertEqual(len(normalized.payload["candidate_memberships"]), 2)

    def test_multi_source_sahs_rule_is_split_into_quote_bound_links(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1",
            (("D1", "v1", "h1"), ("D2", "v2", "h2")))
        lead_assignment = Assignment("sa-sources", Role.SPECIALIST, "mechanical", "expand",
            ("H0",), (), ("H0",), manifest)
        d1 = SourceReference("D1", "v1", "D1:v1:0", "Source one says valve leak.", 0, 27, "log", "quotation")
        d2 = SourceReference("D2", "v2", "D2:v2:0", "Source two says pressure fell.", 0, 30, "log", "quotation")
        proposed = SimpleNamespace(assignment_id="sa-sources", case_snapshot_id="case:s1", board_version="1",
            status="completed", graph_delta=CausalGraph((), (CausalRuleCandidate("r1", ("H0",), "H0",
                "may_cause", "may", basis="source_described", source_refs=(d1, d2),
                source_relation="paraphrase"),)), information_gaps=(), clarification_items=())
        links = sahs_result_to_cferp(proposed, lead_assignment).payload["causal_links"]
        self.assertEqual([link["source_refs"] for link in links], [("D1",), ("D2",)])
        self.assertEqual([link["source_text"] for link in links], [d1.exact_text, d2.exact_text])

    def test_candidate_membership_follows_a_split_rule_to_every_link(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1",
            (("D1", "v1", "h1"), ("D2", "v2", "h2")))
        lead_assignment = Assignment("sa-members", Role.SPECIALIST, "mechanical", "expand",
            ("H0",), (), ("H0",), manifest)
        refs = (SourceReference("D1", "v1", "D1:v1:0", "Source one says valve leak.", 0, 27, "log", "quotation"),
                SourceReference("D2", "v2", "D2:v2:0", "Source two says pressure fell.", 0, 30, "log", "quotation"))
        rule = lambda rule_id, basis, source_refs: CausalRuleCandidate(
            rule_id, ("H0",), "H1", "may_cause", "may", basis=basis, source_refs=source_refs,
            source_relation="paraphrase")
        proposed = SimpleNamespace(assignment_id="sa-members", case_snapshot_id="case:s1", board_version="1",
            status="completed", information_gaps=(), clarification_items=(),
            graph_delta=CausalGraph((), (rule("split", "source_described", refs),
                                         rule("whole", "model_proposed", ()))),
            candidates=(SimpleNamespace(candidate_id="C1", proposition_ids=("H0", "H1"),
                                        rule_ids=("split", "whole")),))
        payload = sahs_result_to_cferp(proposed, lead_assignment).payload
        link_ids = {link["link_id"] for link in payload["causal_links"]}
        self.assertEqual(link_ids, {"split:source:0", "split:source:1", "whole"})
        # Every member rule ID must be a link the Lead's commit gate will know.
        self.assertEqual(payload["candidate_memberships"][0]["rule_ids"],
                         ("split:source:0", "split:source:1", "whole"))

    def test_sahs_source_not_in_lead_catalog_is_rejected_before_commit(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1")
        lead_assignment = Assignment("sa-a", Role.SPECIALIST, "mechanical", "expand",
            ("H0",), (), ("H0",), manifest)
        passage = SourceReference("unknown-doc", "v1", "c1", "quoted text", 0, 11, "manual", "quotation")
        proposed = SimpleNamespace(assignment_id="sa-a", case_snapshot_id="case:s1", board_version="1",
            status="completed", graph_delta=CausalGraph((), (
                CausalRuleCandidate("r1", ("H0",), "H0", "may_cause", "can",
                    basis="source_described", source_refs=(passage,), source_relation="quotation"),)),
            information_gaps=(), clarification_items=())
        with self.assertRaisesRegex(IntegrationError, "not in|source"):
            sahs_result_to_cferp(proposed, lead_assignment)

    def test_ew_passages_and_requests_keep_lead_scope_and_source_versions(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1", (("D1", "v1", "hash-1"),))
        lead_assignment = Assignment("ew-a", Role.EVIDENCE_WORKER, "ew1", "retrieve", ("H1",), ("N1",),
            ("H1", "N1"), manifest)
        link = CandidateLink("link-1", "N1", "s1", "D1", "v1", "R1", 0, 17,
            "Valve leaked at 10.", "Inspection", "log", "bm25", 0.9)
        result = EvidenceWorkerResult("1", "ew-a", "ew-a", "e1", "case:s1", "1", "corp1",
            "catalog1", "repr1", "ready_for_assessor", WorkPhase.AWAITING_ASSESSOR,
            SearchPassStatus.COMPLETE,
            slot_results=(SlotResult("N1", "s1", Coverage.CANDIDATE_FOUND, (link,)),),
            request_drafts=(RequestDraft("REQ-1", "document_request", ("s2",),
                "Provide the V-13 inspection record.", entity_scope=("V-13",), requested_fields=("time",)),))
        normalized = ew_result_to_cferp(result, lead_assignment)
        packet = normalized.payload["packets"][0]
        self.assertEqual(packet["candidate_links"][0]["material_id"], "D1")
        self.assertEqual(packet["source_versions"], (("D1", "v1", "hash-1"),))
        self.assertEqual(normalized.payload["requests"][0]["request_id"], "REQ-1")
        self.assertEqual(normalized.payload["requests"][0]["target_ids"], ("H1",))

    def test_ew_multi_target_slot_clones_candidate_link_per_lead_linked_claim(self):
        manifest = VersionManifest("C1", "case:s1", 1, "materials:1:v1", (("D1", "v1", "hash-1"),))
        lead_assignment = Assignment("ew-multi", Role.EVIDENCE_WORKER, "ew1", "retrieve", ("H1", "H2"),
            ("N1",), ("H1", "H2", "N1"), manifest,
            context={"need": {"need_id": "N1", "target_ids": ("H1", "H2"), "slots": (
                {"slot_id": "s1", "description": "one shared information gap"},)}})
        link = CandidateLink("link-1", "N1", "s1", "D1", "v1", "R1", 0, 17,
            "The source passage is a candidate for the linked need.", "Record", "log", "bm25", 0.9)
        result = EvidenceWorkerResult("1", "ew-multi", "ew-multi", "e1", "case:s1", "1", "corp1",
            "catalog1", "repr1", "ready_for_assessor", WorkPhase.AWAITING_ASSESSOR,
            SearchPassStatus.COMPLETE,
            slot_results=(SlotResult("N1", "s1", Coverage.CANDIDATE_FOUND, (link,)),))

        normalized = ew_result_to_cferp(result, lead_assignment)

        packet = normalized.payload["packets"][0]
        self.assertEqual(packet["target_ids"], ("H1", "H2"))
        self.assertEqual([row["claim_id"] for row in packet["candidate_links"]], ["H1", "H2"])
        self.assertEqual([row["passage_id"] for row in packet["candidate_links"]], ["link-1", "link-1"])

    def test_hera_mixed_findings_become_separate_cferp_annotations(self):
        task = AssessmentTask(
            "1", "t1", "ew-work", "e1", "C1", "case:s1", "1", "evidence_review",
            "evidence_worker", "ew1",
            materials=(
                EvidenceMaterial("L1", "D1", "v1", "R1", "The inspection records a leak."),
                EvidenceMaterial("L2", "D2", "v2", "R2", "No leak was observed."),
            ),
            hypothesis={"hypothesis_id": "cand1", "parts": [
                {"part_id": "p1", "claim_type": "incident_fact", "text": "Valve leaked.", "board_ids": ["H1"]},
            ]},
        )
        statements = {"statements": [
            {"statement_id": "s1", "material_id": "L1", "source_id": "D1", "source_version": "v1",
             "representation_id": "R1", "quote": "The inspection records a leak.", "start_offset": 0,
             "kind": "incident_observation", "modality": "reported", "scope": "event", "timing": "incident"},
            {"statement_id": "s2", "material_id": "L2", "source_id": "D2", "source_version": "v2",
             "representation_id": "R2", "quote": "No leak was observed.", "start_offset": 0,
             "kind": "incident_observation", "modality": "reported", "scope": "event", "timing": "incident"},
        ]}
        comparison = {"parts": [{"part_id": "p1", "findings": [
            {"relation": "supports", "statement_ids": ["s1"], "rationale": "The inspection reports a leak.",
             "inference_bridge": "Incident observation supports occurrence.", "relevance_status": "direct",
             "scope_alignment": "match", "time_alignment": "match"},
            {"relation": "contradicts", "statement_ids": ["s2"], "rationale": "The later record reports no leak.",
             "inference_bridge": "The record directly denies the event.", "relevance_status": "direct",
             "scope_alignment": "match", "time_alignment": "match"},
        ]}]}
        result = Hera1Engine(ScriptedModel([statements, comparison]), Versions()).run(task)
        self.assertEqual(result.payload["evidence_effect"], "mixed")
        assignment = cferp_assignment()
        normalized = hera_result_to_cferp(result, task, assignment)
        rows = normalized.payload["assessments"]
        self.assertEqual([(r["material_id"], r["effect"]) for r in rows],
                         [("D1", "supports"), ("D2", "contradicts")])
        self.assertTrue(all(r["claim_id"] == "H1" for r in rows))

    def test_hera_general_or_unclear_result_maps_to_neutral_without_promotion(self):
        task = AssessmentTask(
            "1", "t2", "ew-work", "e2", "C1", "case:s1", "1", "evidence_review",
            "evidence_worker", "ew1", materials=(EvidenceMaterial("L1", "D1", "v1", "R1", "General mechanism."),),
            hypothesis={"hypothesis_id": "cand1", "parts": [
                {"part_id": "p1", "claim_type": "incident_fact", "text": "Valve leaked.", "board_ids": ["H1"]},
            ]},
        )
        extraction = {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
            "source_version": "v1", "representation_id": "R1", "quote": "General mechanism.",
            "start_offset": 0, "kind": "general_mechanism", "modality": "conditional",
            "scope": "general", "timing": "unspecified"}]}
        comparison = {"parts": [{"part_id": "p1", "findings": [{"relation": "does_not_address",
            "statement_ids": ["s1"], "rationale": "It does not report this incident.",
            "inference_bridge": "", "relevance_status": "direct", "scope_alignment": "match",
            "time_alignment": "match"}]}]}
        result = Hera1Engine(ScriptedModel([extraction, comparison]), Versions()).run(task)
        normalized = hera_result_to_cferp(result, task, cferp_assignment())
        self.assertEqual(normalized.payload["assessments"][0]["effect"], "neutral")

    def test_hera_no_extraction_closes_only_as_neutral_for_assigned_passage(self):
        task = AssessmentTask("1", "no-extract", "ew-work", "e3", "C1", "case:s1", "1",
            "evidence_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", "unreadable passage", offset_base=12),),
            hypothesis={"hypothesis_id": "cand1", "parts": [
                {"part_id": "p1", "claim_type": "incident_fact", "text": "Valve leaked.", "board_ids": ["H1"]},
            ]})
        result = AssessmentResult("1", "no-extract", "ew-work", "e3", "C1", "case:s1", "1",
            "evidence_review", "completed", "lead", payload={"parts": [], "source_statements": [],
            "evidence_effect": "insufficient"})
        assignment = cferp_assignment()
        assignment = Assignment(assignment.assignment_id, assignment.role, assignment.owner_id,
            assignment.purpose, assignment.target_ids, assignment.need_ids, assignment.dependencies,
            assignment.manifest, context={"source_work_item_id": "ew-work", "candidate_link": {
                "claim_id": "H1", "material_id": "D1", "material_version": "v1",
                "passage_id": "L1", "start_offset": 12, "end_offset": 29,
                "exact_text": "unreadable passage"}})
        normalized = hera_result_to_cferp(result, task, assignment)
        row = normalized.payload["assessments"][0]
        self.assertEqual((row["material_id"], row["passage_id"], row["effect"]), ("D1", "L1", "neutral"))

    def request_review_assignment(self, link_count):
        request = SimpleNamespace(request_id="REQ-A", request_kind="document_request",
            target_ids=("H1",), wording="Please provide the pressure log.", slot_ids=("s1",),
            record_types=(), origin_ids=("N1",), request_version=1)
        links = [{"candidate_link_id": f"cl:{i:02d}", "source_id": f"mat_{i}",
                  "source_version": "sha256:" + "a" * 64, "slot_id": "s1",
                  "exact_text": f"passage {i} " + "x" * 400, "start_offset": 0, "end_offset": 410}
                 for i in range(link_count)]
        base = cferp_assignment()
        return Assignment(base.assignment_id, base.role, base.owner_id, base.purpose, base.target_ids,
            base.need_ids, base.dependencies, base.manifest, context={
                "task_kind": "request_review", "request": request, "existing_candidate_links": links,
                "source_work_item_id": "ew-work"})

    def test_request_review_links_are_capped_so_the_task_fits_hera_limits(self):
        task = hera_task_from_cferp(self.request_review_assignment(24))

        shown = task.context["existing_candidate_links"]
        self.assertEqual([row["candidate_link_id"] for row in shown],
                         [f"cl:{i:02d}" for i in range(MAX_REVIEW_LINKS)])
        self.assertTrue(all(len(row["exact_text"]) <= MAX_REVIEW_LINK_CHARS for row in shown))
        self.assertEqual(task.context["omitted_candidate_link_count"], 24 - MAX_REVIEW_LINKS)
        validate_task(task, AssessorConfig())  # raised "context exceeds max_context_chars" uncapped

    def test_request_review_with_few_links_is_passed_through_without_an_omission_note(self):
        task = hera_task_from_cferp(self.request_review_assignment(3))

        self.assertEqual(len(task.context["existing_candidate_links"]), 3)
        self.assertNotIn("omitted_candidate_link_count", task.context)

    def test_request_and_clarification_outcomes_keep_lead_meaning(self):
        assignment = cferp_assignment()
        request_task = SimpleNamespace(task_id="req-t", work_item_id="ew-work", case_id="C1", case_snapshot_id="case:s1",
            board_version="1", task_kind="request_review", request={"request_id": "REQ-A"})
        request_result = AssessmentResult("1", "req-t", "ew-work", "e", "C1", "case:s1", "1",
            "request_review", "completed", "lead", payload={"request_id": "REQ-A", "disposition": "eligible",
            "rationale": "The missing inspection record is relevant."})
        self.assertEqual(hera_result_to_cferp(request_result, request_task, assignment).payload["disposition"], "pass")
        clar_task = SimpleNamespace(task_id="clar-t", work_item_id="ew-work", case_id="C1", case_snapshot_id="case:s1",
            board_version="1", task_kind="clarification_review", clarification={"question_id": "C-1"})
        clar_result = AssessmentResult("1", "clar-t", "ew-work", "e", "C1", "case:s1", "1",
            "clarification_review", "completed", "lead", payload={"clarification_id": "C-1",
            "status": "conflicting", "verified_truth": False})
        self.assertEqual(hera_result_to_cferp(clar_result, clar_task, assignment).payload["decision"], "ambiguous")

    def test_stale_or_noncompleted_hera_result_is_not_committed(self):
        task = SimpleNamespace(task_id="t3", work_item_id="ew-work", case_id="C1", case_snapshot_id="case:s1",
            board_version="1", task_kind="request_review", request={"request_id": "REQ-A"})
        stale = AssessmentResult("1", "t3", "ew-work", "e", "C1", "case:s0", "1",
            "request_review", "completed", "lead", payload={"request_id": "REQ-A", "disposition": "eligible"})
        with self.assertRaisesRegex(IntegrationError, "snapshot"):
            hera_result_to_cferp(stale, task, cferp_assignment())


if __name__ == "__main__":
    unittest.main()

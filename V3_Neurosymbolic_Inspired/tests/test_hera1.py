import unittest

from ewv3.contracts import (CandidateLink, EvidenceWorkerResult, SearchPassStatus,
                            SlotResult, WorkPhase)
from sahs.engine_contracts import CandidateExplanation, CausalGraph, SpecialistResult

from hera1 import (
    AssessmentRoute, AssessmentTask, EvidenceMaterial, Hera1Engine, HeraPipelineAdapter,
    InMemoryAssessmentLedger, VersionSnapshot,
)


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def ask(self, task, system, payload):
        self.calls.append((task, system, payload))
        return self.responses.pop(0)


class FixedVersions:
    def __init__(self, snapshot_id="case:s1", board="b1", versions=None):
        self.snapshot_id = snapshot_id
        self.board = board
        self.material_versions = versions or {"D1": "v1"}

    def read(self, case_id, material_ids):
        return VersionSnapshot(self.snapshot_id, self.board,
                               {k: v for k, v in self.material_versions.items() if k in material_ids})


def material(text="A leaking valve can cause pressure loss.", start=0):
    return EvidenceMaterial("L1", "D1", "v1", "R1", text, "manual", start,
                            {"page": 2, "candidate_link_id": "L1"})


def evidence_task(**overrides):
    data = dict(
        schema_version="1", task_id="t1", work_item_id="w1", event_id="e1",
        case_id="c1", case_snapshot_id="case:s1", board_version="b1",
        task_kind="evidence_review", sender_role="evidence_worker", sender_id="ew7",
        materials=(material(),),
        hypothesis={"hypothesis_id": "h1", "parts": [
            {"part_id": "p1", "claim_type": "incident_fact", "text": "The valve leaked during the event."},
            {"part_id": "p2", "claim_type": "incident_causal_link", "text": "The leak caused pressure loss."},
        ]},
    )
    data.update(overrides)
    return AssessmentTask(**data)


def extraction(quote="A leaking valve can cause pressure loss.", kind="general_mechanism", modality="conditional"):
    return {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                            "source_version": "v1", "representation_id": "R1", "quote": quote,
                            "start_offset": 0, "kind": kind, "modality": modality,
                            "scope": "general", "timing": "unspecified"}]}


def comparison(second="supports"):
    return {"parts": [
        {"part_id": "p1", "findings": [finding("does_not_address", ["s1"], "No incident occurrence is stated.")]},
        {"part_id": "p2", "findings": [finding(second, ["s1"], "The source describes a possible mechanism.")]},
    ]}


def finding(relation, statement_ids, rationale, scope="match", timing="match", relevance="direct"):
    bridge = rationale if relation in {"supports", "weakens", "contradicts"} else ""
    return {"relation": relation, "statement_ids": statement_ids, "rationale": rationale,
            "inference_bridge": bridge, "relevance_status": relevance,
            "scope_alignment": scope, "time_alignment": timing}


class TestHera1(unittest.TestCase):
    def test_pipeline_accepts_lead_committed_sahs_snapshot_with_current_ew_snapshot(self):
        sahs = {"assignment_id": "sa-old", "case_snapshot_id": "case:s0", "board_version": "b1",
                "candidates": [{"candidate_id": "cand-1", "proposition_ids": ["p1"], "rule_ids": []}]}
        link = {"candidate_link_id": "link-1", "need_id": "n1", "slot_id": "s1",
                "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                "start_offset": 0, "end_offset": 20, "exact_text": "Valve leaked in incident."}
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b2", "work_item_id": "ew-work",
                "event_id": "ew-event", "status": "ready_for_assessor", "work_phase": "awaiting_assessor",
                "slot_results": [{"need_id": "n1", "slot_id": "s1", "candidate_links": [link]}]}
        route = {"task_id": "hera-task", "work_item_id": "ew-work", "event_id": "ew-event",
                 "case_id": "c1", "case_snapshot_id": "case:s1", "board_version": "b2",
                 "specialist_assignment_id": "sa-old", "specialist_case_snapshot_id": "case:s0",
                 "specialist_board_version": "b1",
                 "candidate_id": "cand-1", "need_id": "n1", "slot_ids": ["s1"], "worker_id": "ew1",
                 "hypothesis_parts": [{"part_id": "p1", "board_ids": ["p1"],
                     "claim_type": "incident_fact", "text": "The valve leaked during the incident."}]}
        task = HeraPipelineAdapter.evidence_review(sahs, ewv3, route)
        self.assertEqual(task.board_version, "b2")
        self.assertEqual(task.hypothesis["hypothesis_id"], "cand-1")

    def test_general_mechanism_does_not_establish_incident_leak_or_causal_link(self):
        model = ScriptedModel([extraction(), comparison()])
        result = Hera1Engine(model, FixedVersions()).run(evidence_task())
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.destination_role, "lead")
        self.assertEqual(result.payload["parts"][0]["relation"], "does_not_address")
        self.assertEqual(result.payload["parts"][1]["findings"][0]["model_relation"], "supports")
        self.assertEqual(result.payload["parts"][1]["relation"], "does_not_address")
        self.assertEqual(result.payload["evidence_effect"], "insufficient")
        self.assertEqual(result.payload["source_statements"][0]["start_offset"], 0)
        self.assertEqual(result.model_calls, 2)

    def test_incident_observation_can_support_an_incident_part(self):
        text = "The inspection log records that the valve leaked during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        model = ScriptedModel([
            extraction(text, kind="incident_observation", modality="reported"),
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s1"], "Incident-time report.")]},
                {"part_id": "p2", "findings": [finding("insufficient_or_unclear", ["s1"], "Causal link not established.")]},
            ]},
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["parts"][0]["relation"], "supports")
        self.assertEqual(result.payload["evidence_effect"], "supportive")

    def test_aggregation_reports_mixed_part_effects_without_erasing_them(self):
        text = "The inspection log records that the valve leaked during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            hypothesis={"hypothesis_id": "h1", "parts": [
                {"part_id": "p1", "claim_type": "incident_fact", "text": "The valve leaked."},
                {"part_id": "p2", "claim_type": "incident_fact", "text": "The valve leaked at 10:00."},
            ]})
        model = ScriptedModel([
            extraction(text, kind="incident_observation", modality="reported"),
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s1"], "Leak is reported.")]},
                {"part_id": "p2", "findings": [finding("weakens", ["s1"], "No pressure loss is reported.")]},
            ]},
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["evidence_effect"], "mixed")
        self.assertEqual([p["relation"] for p in result.payload["parts"]], ["supports", "weakens"])

    def test_packet_can_combine_statements_from_multiple_linked_materials(self):
        first = EvidenceMaterial("L1", "D1", "v1", "R1", "The valve was inspected after the event.", "log")
        second = EvidenceMaterial("L2", "D2", "v3", "R7", "The valve was leaking at 09:14.", "operator log")
        task = evidence_task(materials=(first, second))
        first_statement = {"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                           "source_version": "v1", "representation_id": "R1",
                           "quote": first.text, "start_offset": 0, "kind": "incident_observation",
                           "modality": "reported", "scope": "event", "timing": "post-event"}
        second_statement = {"statement_id": "s2", "material_id": "L2", "source_id": "D2",
                            "source_version": "v3", "representation_id": "R7",
                            "quote": second.text, "start_offset": 0, "kind": "incident_observation",
                            "modality": "reported", "scope": "event", "timing": "09:14"}
        model = ScriptedModel([
            {"statements": [first_statement, second_statement]},
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s2"], "Incident-time leak report.")]},
                {"part_id": "p2", "findings": [finding("insufficient_or_unclear", ["s2"], "No pressure outcome is stated.")]},
            ]},
        ])
        versions = FixedVersions(versions={"D1": "v1", "D2": "v3"})
        result = Hera1Engine(model, versions).run(task)
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.payload["source_statements"]), 2)
        self.assertEqual(result.payload["parts"][0]["relation"], "supports")

    def test_invalid_source_quote_fails_assessment_and_routes_to_lead(self):
        model = ScriptedModel([extraction("not in source")])
        result = Hera1Engine(model, FixedVersions()).run(evidence_task())
        self.assertEqual(result.status, "assessment_failed")
        self.assertEqual(result.destination_role, "lead")
        self.assertEqual(result.model_calls, 1)

    def test_negated_incident_statement_cannot_support_positive_event(self):
        text = "The valve did not leak during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        output = {"parts": [
            {"part_id": "p1", "findings": [finding("supports", ["s1"], "The passage mentions the leak.")]},
            {"part_id": "p2", "findings": [finding("does_not_address", ["s1"], "No causal link is stated.")]},
        ]}
        model = ScriptedModel([
            {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                "source_version": "v1", "representation_id": "R1", "quote": text, "start_offset": 0,
                "kind": "incident_observation", "modality": "negated", "scope": "incident", "timing": "incident"}]},
            output,
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        finding_out = result.payload["parts"][0]["findings"][0]
        self.assertEqual(finding_out["model_relation"], "supports")
        self.assertEqual(finding_out["relation"], "insufficient_or_unclear")

    def test_wrong_time_or_scope_cannot_support_incident_claim(self):
        text = "The valve leaked during the previous shift."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        model = ScriptedModel([
            {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                "source_version": "v1", "representation_id": "R1", "quote": text, "start_offset": 0,
                "kind": "incident_observation", "modality": "reported", "scope": "previous shift", "timing": "previous shift"}]},
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s1"], "Leak is reported.", scope="mismatch", timing="mismatch")]},
                {"part_id": "p2", "findings": [finding("does_not_address", ["s1"], "No causal link.")]},
            ]},
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["parts"][0]["relation"], "does_not_address")
        self.assertIn(result.payload["scope_guard_flags"][0]["rule"],
                      {"incident_scope_or_time_mismatch", "lexical_incident_time_mismatch"})

    def test_procedure_statement_cannot_support_that_an_event_occurred(self):
        text = "Valve V-7 must be isolated before maintenance."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        model = ScriptedModel([
            {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                "source_version": "v1", "representation_id": "R1", "quote": text, "start_offset": 0,
                "kind": "procedure", "modality": "asserted", "scope": "maintenance", "timing": "general"}]},
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s1"], "Procedure requires isolation.")]},
                {"part_id": "p2", "findings": [finding("does_not_address", ["s1"], "No causal event is reported.")]},
            ]},
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["parts"][0]["relation"], "does_not_address")

    def test_board_change_during_model_call_discards_result_as_stale(self):
        class ChangesAfterFirstRead:
            def __init__(self): self.reads = 0
            def read(self, case_id, material_ids):
                self.reads += 1
                board = "b1" if self.reads == 1 else "b2"
                return VersionSnapshot("case:s1", board, {"D1": "v1"})
        model = ScriptedModel([{"statements": []}])
        result = Hera1Engine(model, ChangesAfterFirstRead()).run(evidence_task())
        self.assertEqual(result.status, "stale")
        self.assertEqual(result.model_calls, 1)
        self.assertEqual(result.destination_role, "lead")

    def test_conflicting_passages_for_same_part_are_preserved_as_mixed(self):
        text = "The valve leaked during the incident. The valve did not leak during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        quote_a = "The valve leaked during the incident."
        quote_b = "The valve did not leak during the incident."
        model = ScriptedModel([
            {"statements": [
                {"statement_id": "s1", "material_id": "L1", "source_id": "D1", "source_version": "v1",
                 "representation_id": "R1", "quote": quote_a, "start_offset": 0, "kind": "incident_observation",
                 "modality": "reported", "scope": "incident", "timing": "incident"},
                {"statement_id": "s2", "material_id": "L1", "source_id": "D1", "source_version": "v1",
                 "representation_id": "R1", "quote": quote_b, "start_offset": text.index(quote_b), "kind": "incident_observation",
                 "modality": "negated", "scope": "incident", "timing": "incident"},
            ]},
            {"parts": [
                {"part_id": "p1", "findings": [
                    finding("supports", ["s1"], "The event log reports a leak."),
                    finding("contradicts", ["s2"], "Inspection says no leak was found.")
                ]},
                {"part_id": "p2", "findings": [finding("does_not_address", ["s1", "s2"], "Neither states a causal link.")]},
            ]},
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["parts"][0]["relation"], "mixed")
        self.assertEqual([f["relation"] for f in result.payload["parts"][0]["findings"]], ["supports", "contradicts"])
        self.assertEqual(result.payload["evidence_effect"], "mixed")

    def test_document_answer_cannot_be_marked_answered_without_citation(self):
        task = AssessmentTask("1", "t-doc-no-cite", "w-doc-no-cite", "e-doc-no-cite", "c1",
            "case:s1", "b1", "clarification_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", "The procedure defines YOLK as a key."),),
            clarification={"question_id": "q1", "text": "What does YOLK mean?"}, answer={"kind": "document", "question_id": "q1"})
        model = ScriptedModel([{"status": "answered", "summary": "It is a key.",
            "answered_slots": ["YOLK meaning"], "open_slots": [], "ambiguities": [],
            "conflicts": [], "source_passages": []}])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")
        self.assertEqual(result.destination_role, "lead")

    def test_visual_only_retrieval_returns_unsupported_material_without_model_call(self):
        sahs = {"assignment_id": "sa-img", "case_snapshot_id": "case:s1", "board_version": "b1",
                "candidates": [{"candidate_id": "cand-img", "proposition_ids": ["p1"]}]}
        image_link = {"candidate_link_id": "image-link", "need_id": "n-img", "slot_id": "s-img",
            "source_id": "D1", "source_version": "v1", "representation_id": "FIG-1",
            "start_offset": None, "end_offset": None, "exact_text": "", "modality": "image",
            "structural_context": {"page": 4, "figure": "2"}}
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b1", "work_item_id": "w-img",
            "event_id": "e-img", "status": "ready_for_assessor", "work_phase": "awaiting_assessor",
            "slot_results": [{"need_id": "n-img", "slot_id": "s-img", "candidate_links": [image_link]}]}
        route = {"task_id": "t-img", "work_item_id": "w-img", "event_id": "e-img", "case_id": "c1",
            "case_snapshot_id": "case:s1", "board_version": "b1", "candidate_id": "cand-img",
            "specialist_assignment_id": "sa-img", "need_id": "n-img", "slot_ids": ["s-img"],
            "worker_id": "ew-img", "hypothesis_parts": [{"part_id": "p1", "board_ids": ["p1"],
            "claim_type": "incident_fact", "text": "The indicator was red."}]}
        task = HeraPipelineAdapter.evidence_review(sahs, ewv3, route)
        model = ScriptedModel([])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.status, "unsupported_material")
        self.assertEqual(result.destination_role, "lead")
        self.assertEqual(result.model_calls, 0)

    def test_missing_source_offset_is_reported_as_local_not_global(self):
        text = "Inspection log confirms the valve was leaking."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text,
            "incident_log", 0, {"start_offset_missing": True}),))
        model = ScriptedModel([
            {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                "source_version": "v1", "representation_id": "R1", "quote": text, "start_offset": 0,
                "kind": "incident_observation", "modality": "reported", "scope": "incident", "timing": "incident"}]},
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s1"], "Incident log report.")]},
                {"part_id": "p2", "findings": [finding("does_not_address", ["s1"], "No causal link.")]},
            ]},
        ])
        result = Hera1Engine(model, FixedVersions()).run(task)
        statement = result.payload["source_statements"][0]
        self.assertIsNone(statement["start_offset"])
        self.assertEqual(statement["local_start_offset"], 0)
        self.assertEqual(statement["offset_basis"], "representation_text")

    def test_human_answer_cannot_smuggle_unverified_document_citation(self):
        task = AssessmentTask("1", "t-human-cite", "w-human-cite", "e-human-cite", "c1",
            "case:s1", "b1", "clarification_review", "evidence_worker", "ew1",
            clarification={"question_id": "q1", "text": "Was the valve isolated?"},
            answer={"kind": "human", "question_id": "q1", "text": "Yes, see document D1."})
        citation = {"material_id": "unknown", "source_id": "D1", "source_version": "v1",
                    "representation_id": "R1", "quote": "Yes, it was.", "start_offset": 0}
        model = ScriptedModel([{"status": "answered", "summary": "The responder says yes.",
            "answered_slots": ["isolation"], "open_slots": [], "ambiguities": [],
            "conflicts": [], "source_passages": [citation]}])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")

    def test_no_response_is_registered_without_model_call(self):
        task = AssessmentTask("1", "t-no-response", "w-no-response", "e-no-response", "c1",
            "case:s1", "b1", "clarification_review", "intake", "intake-1",
            clarification={"question_id": "q1", "text": "Was the valve isolated?"},
            answer={"kind": "no_response", "question_id": "q1"})
        model = ScriptedModel([])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.payload["status"], "unanswered")
        self.assertEqual(result.payload["answer_basis"], "no_response")
        self.assertEqual(result.model_calls, 0)

    def test_answer_question_id_cannot_be_crossed_to_another_question(self):
        task = AssessmentTask("1", "t-wrong-q", "w-wrong-q", "e-wrong-q", "c1", "case:s1", "b1",
            "clarification_review", "intake", "intake-1",
            clarification={"question_id": "q-current", "text": "Was the valve isolated?"},
            answer={"kind": "human", "question_id": "q-other", "text": "Yes."})
        result = Hera1Engine(ScriptedModel([]), FixedVersions()).run(task)
        self.assertEqual(result.status, "invalid_input")
        self.assertEqual(result.model_calls, 0)

    def test_request_review_rejects_empty_rationale(self):
        task = AssessmentTask("1", "t-empty-rationale", "w-empty-rationale", "e-empty-rationale", "c1",
            "case:s1", "b1", "request_review", "evidence_worker", "ew1",
            request={"request_id": "r1", "target_id": "g1", "kind": "question", "text": "Was it open?"})
        model = ScriptedModel([{"disposition": "eligible", "rationale": "", "existing_evidence_status": "unresolved", "existing_evidence_rationale": "No retrieved item resolves this gap.",
                                "proportionality": "proportionate", "revision_feedback": "",
                                "revised_request": ""}])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")

    def test_sensitive_personal_data_request_is_held_for_lead_even_if_model_approves(self):
        task = AssessmentTask("1", "t-sensitive", "w-sensitive", "e-sensitive", "c1",
            "case:s1", "b1", "request_review", "evidence_worker", "ew1",
            request={"request_id": "r-sensitive", "target_id": "g1", "kind": "document_request",
                     "text": "Send all operator emails, home addresses and medical records.",
                     "requested_fields": []})
        output = {"disposition": "eligible", "rationale": "May help.",
                  "existing_evidence_status": "unresolved", "existing_evidence_rationale": "No results.",
                  "proportionality": "proportionate", "revision_feedback": "", "revised_request": ""}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.payload["disposition"], "not_eligible")
        self.assertEqual(result.payload["reason"], "sensitive_scope_lead_review")
        self.assertEqual(result.destination_role, "lead")

    def test_sensitive_data_guard_catches_common_personal_data_wording(self):
        requests = ["Provide the operator residential address and full health chart.",
                    "Provide employee date of birth and diagnosis.",
                    "Provide all operator correspondence.",
                    "Provide crew phone and mobile numbers.",
                    "Collect operator private personnel files and family details.",
                    "Obtain the technician's personal telephone number."]
        for index, wording in enumerate(requests):
            task = AssessmentTask("1", f"t-sensitive-{index}", f"w-sensitive-{index}", f"e-sensitive-{index}", "c1",
                "case:s1", "b1", "request_review", "evidence_worker", "ew1",
                request={"request_id": f"r-{index}", "target_id": "g1", "kind": "document_request",
                         "text": wording, "requested_fields": []})
            output = {"disposition": "eligible", "rationale": "Useful.",
                      "existing_evidence_status": "unresolved", "existing_evidence_rationale": "No results.",
                      "proportionality": "proportionate", "revision_feedback": "", "revised_request": ""}
            result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
            self.assertEqual(result.payload["reason"], "sensitive_scope_lead_review", wording)

    def test_request_revision_is_not_routed_back_when_gap_is_marked_resolved(self):
        task = AssessmentTask("1", "t-resolved-revise", "w-resolved-revise", "e-resolved-revise", "c1",
            "case:s1", "b1", "request_review", "evidence_worker", "ew1",
            request={"request_id": "r1", "target_id": "g1", "kind": "question", "text": "Was it open?"})
        output = {"disposition": "revise", "rationale": "Narrow it.",
                  "existing_evidence_status": "resolved", "existing_evidence_rationale": "Found answer.",
                  "proportionality": "proportionate", "revision_feedback": "Narrow it.",
                  "revised_request": "Was it open at 09:10?"}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.payload["disposition"], "not_eligible")
        self.assertEqual(result.payload["reason"], "gap_already_resolved")
        self.assertEqual(result.destination_role, "lead")

    def test_request_must_address_retrieved_link_in_its_evidence_rationale(self):
        task = AssessmentTask("1", "t-link-rationale", "w-link-rationale", "e-link-rationale", "c1",
            "case:s1", "b1", "request_review", "evidence_worker", "ew1",
            request={"request_id": "r1", "target_id": "g1", "kind": "document_request", "text": "Provide logs."},
            context={"existing_candidate_links": [{"candidate_link_id": "link-77", "exact_text": "V-7 serviced at 09:10."}]})
        output = {"disposition": "eligible", "rationale": "Need a log.",
                  "existing_evidence_status": "unresolved", "existing_evidence_rationale": "The gap remains unresolved.",
                  "proportionality": "proportionate", "revision_feedback": "", "revised_request": ""}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")
        self.assertIn("candidate link", result.diagnostics[0])

    def test_request_with_link_id_but_no_content_reasoning_is_held_for_lead(self):
        task = AssessmentTask("1", "t-weak-link-rationale", "w-weak-link-rationale", "e-weak-link-rationale", "c1",
            "case:s1", "b1", "request_review", "evidence_worker", "ew1",
            request={"request_id": "r1", "target_id": "g1", "kind": "document_request", "text": "Provide logs."},
            context={"existing_candidate_links": [{"candidate_link_id": "link-77", "exact_text": "V-7 serviced at 09:10."}]})
        output = {"disposition": "eligible", "rationale": "Need another log.",
                  "existing_evidence_status": "unresolved",
                  "existing_evidence_rationale": "link-77 serviced 09:10; however unrelated to this gap.",
                  "proportionality": "proportionate", "revision_feedback": "", "revised_request": ""}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.payload["disposition"], "not_eligible")
        self.assertEqual(result.payload["reason"], "retrieved_evidence_needs_lead_review")

    def test_stale_snapshot_stops_before_any_model_call(self):
        model = ScriptedModel([])
        result = Hera1Engine(model, FixedVersions(snapshot_id="case:s2")).run(evidence_task())
        self.assertEqual(result.status, "stale")
        self.assertEqual(result.destination_role, "lead")
        self.assertEqual(result.model_calls, 0)

    def test_duplicate_event_reuses_prior_result_without_second_call(self):
        model = ScriptedModel([extraction(), comparison()])
        engine = Hera1Engine(model, FixedVersions(), InMemoryAssessmentLedger())
        task = evidence_task()
        first = engine.run(task)
        second = engine.run(task)
        self.assertIs(first, second)
        self.assertEqual(len(model.calls), 2)

    def test_request_revision_returns_to_the_same_evidence_worker(self):
        model = ScriptedModel([{"disposition": "revise", "rationale": "The request is too broad.",
                                "existing_evidence_status": "unresolved", "existing_evidence_rationale": "No retrieved item resolves this gap.", "proportionality": "proportionate",
                                "revision_feedback": "Name the record and date range.",
                                "revised_request": "Provide V-7 maintenance logs for the incident date."}])
        task = AssessmentTask(
            "1", "t2", "w2", "e2", "c1", "case:s1", "b1", "request_review",
            "evidence_worker", "ew42", request={"request_id": "r1", "target_id": "g1",
                "kind": "document_request", "text": "Send the hydraulic records."})
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["disposition"], "revise")
        self.assertEqual(result.destination_role, "evidence_worker")
        self.assertEqual(result.destination_id, "ew42")

    def test_duplicate_request_is_noop_and_second_revision_closes_loop(self):
        req = {"request_id": "r2", "target_id": "g1", "kind": "question", "text": "Was valve V1 open?"}
        duplicate_task = AssessmentTask(
            "1", "t3", "w3", "e3", "c1", "case:s1", "b1", "request_review",
            "evidence_worker", "ew4", request=req,
            request_history=({"target_id": "g1", "kind": "question", "text": "  was valve v1 open? "},))
        model = ScriptedModel([])
        result = Hera1Engine(model, FixedVersions()).run(duplicate_task)
        self.assertEqual(result.status, "duplicate_request")
        self.assertEqual(len(model.calls), 0)

        retry = AssessmentTask(
            "1", "t4", "w4", "e4", "c1", "case:s1", "b1", "request_review",
            "evidence_worker", "ew4", request={**req, "request_id": "r3"}, revision_attempt=1)
        model = ScriptedModel([{"disposition": "revise", "rationale": "Still too broad.",
                                "existing_evidence_status": "uncertain", "existing_evidence_rationale": "Coverage is incomplete.", "proportionality": "uncertain",
                                "revision_feedback": "Narrow the unit and time range.",
                                "revised_request": "Provide V-7 logs for the incident shift."}])
        result = Hera1Engine(model, FixedVersions()).run(retry)
        self.assertEqual(result.payload["disposition"], "not_eligible")
        self.assertEqual(result.destination_role, "lead")

    def test_human_clarification_is_reported_not_verified_and_goes_to_lead(self):
        model = ScriptedModel([{"status": "partial", "summary": "Responder is unsure.",
                                "answered_slots": ["valve isolation: reported as likely"],
                                "open_slots": ["valve isolation: confirmation missing"],
                                "ambiguities": ["Responder is uncertain."], "conflicts": [],
                                "source_passages": []}])
        task = AssessmentTask(
            "1", "t5", "w5", "e5", "c1", "case:s1", "b1", "clarification_review",
            "evidence_worker", "ew9", clarification={"question_id": "q1", "text": "Was the valve isolated?"},
            answer={"kind": "human", "question_id": "q1", "text": "I think so, but I am not certain."})
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["answer_basis"], "reported_by_responder")
        self.assertFalse(result.payload["verified_truth"])
        self.assertEqual(result.destination_role, "lead")

    def test_document_clarification_answer_keeps_exact_source_location(self):
        text = "In this plant, YOLK refers to the yellow overload-lock key."
        material_row = EvidenceMaterial("L9", "D1", "v1", "R9", text, "procedure", 40)
        task = AssessmentTask(
            "1", "t9", "w9", "e9", "c1", "case:s1", "b1", "clarification_review",
            "evidence_worker", "ew9", materials=(material_row,),
            clarification={"question_id": "q9", "text": "What does YOLK mean?"},
            answer={"kind": "document", "question_id": "q9"})
        passage = {"material_id": "L9", "source_id": "D1", "source_version": "v1",
                   "representation_id": "R9", "quote": "YOLK refers to the yellow overload-lock key.",
                   "start_offset": text.index("YOLK"), "answered_slot": "YOLK meaning"}
        model = ScriptedModel([{"status": "answered", "summary": "The procedure defines YOLK.",
                                "answered_slots": ["YOLK meaning"], "open_slots": [],
                                "ambiguities": [], "conflicts": [], "source_passages": [passage]}])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["status"], "answered")
        self.assertEqual(result.payload["source_passages"][0]["start_offset"], 40 + text.index("YOLK"))
        self.assertFalse(result.payload["verified_truth"])

    def test_document_answer_citation_cannot_smuggle_unrecognized_fields(self):
        text = "In this plant, YOLK refers to the yellow overload-lock key."
        task = AssessmentTask("1", "t-extra-cite", "w-extra-cite", "e-extra-cite", "c1", "case:s1", "b1",
            "clarification_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            clarification={"question_id": "q1", "text": "What does YOLK mean?"},
            answer={"kind": "document", "question_id": "q1"})
        citation = {"material_id": "L1", "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                    "quote": text, "start_offset": 0, "answered_slot": "YOLK meaning", "established": True}
        output = {"status": "answered", "summary": "YOLK is a key.", "answered_slots": ["YOLK meaning"],
                  "open_slots": [], "ambiguities": [], "conflicts": [], "source_passages": [citation]}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")

    def test_each_answered_clarification_slot_needs_its_own_document_citation(self):
        text = "YOLK is the yellow overload-lock key."
        task = AssessmentTask("1", "t-two-slots", "w-two-slots", "e-two-slots", "c1", "case:s1", "b1",
            "clarification_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            clarification={"question_id": "q1", "text": "Define YOLK and identify its storage location."},
            answer={"kind": "document", "question_id": "q1"})
        citation = {"material_id": "L1", "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                    "quote": text, "start_offset": 0, "answered_slot": "YOLK definition"}
        output = {"status": "partial", "summary": "Definition found; location unclear.",
                  "answered_slots": ["YOLK definition", "storage location"], "open_slots": ["Storage location"],
                  "ambiguities": [], "conflicts": [], "source_passages": [citation]}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")

    def test_ambiguous_document_answer_cannot_mark_uncited_slot_answered(self):
        text = "The turbine was inspected."
        task = AssessmentTask("1", "t-ambiguous-uncited", "w-ambiguous-uncited", "e-ambiguous-uncited", "c1",
            "case:s1", "b1", "clarification_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            clarification={"question_id": "q1", "text": "What does YOLK mean?"},
            answer={"kind": "document", "question_id": "q1"})
        output = {"status": "ambiguous", "summary": "Term remains ambiguous.",
                  "answered_slots": ["meaning"], "open_slots": [], "ambiguities": ["Meaning unclear."],
                  "conflicts": [], "source_passages": []}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")

    def test_document_clarification_with_lexically_unrelated_quote_is_downgraded(self):
        text = "The turbine was inspected."
        task = AssessmentTask("1", "t-irrelevant-clarification", "w-irrelevant-clarification", "e-irrelevant-clarification", "c1",
            "case:s1", "b1", "clarification_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            clarification={"question_id": "q1", "text": "What does YOLK mean?"},
            answer={"kind": "document", "question_id": "q1"})
        citation = {"material_id": "L1", "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                    "quote": text, "start_offset": 0, "answered_slot": "meaning"}
        output = {"status": "answered", "summary": "The term is defined.", "answered_slots": ["meaning"],
                  "open_slots": [], "ambiguities": [], "conflicts": [], "source_passages": [citation]}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.payload["status"], "partial")
        self.assertEqual(result.payload["citation_relevance_flags"][0]["reason"], "no_clear_lexical_anchor_to_question")

    def test_adapter_binds_unlabeled_intake_answer_to_routed_question(self):
        sahs = {"assignment_id": "sa-qbind", "case_snapshot_id": "case:s1", "board_version": "b1",
                "clarification_items": [{"clarification_id": "q-bind", "question": "What is YOLK?"}]}
        route = AssessmentRoute("t-qbind", "w-qbind", "e-qbind", "c1", "case:s1", "b1",
                                sender_role="intake", sender_id="intake-1", clarification_id="q-bind",
                                specialist_assignment_id="sa-qbind")
        task = HeraPipelineAdapter.clarification_review(
            sahs, route, {"kind": "human", "text": "A safety key."})
        self.assertEqual(task.answer["question_id"], "q-bind")

    def test_duplicate_extraction_of_same_span_is_rejected(self):
        text = "The valve leaked during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        row = {"statement_id": "s1", "material_id": "L1", "source_id": "D1", "source_version": "v1",
               "representation_id": "R1", "quote": text, "start_offset": 0,
               "kind": "incident_observation", "modality": "reported", "scope": "incident", "timing": "incident"}
        model = ScriptedModel([{"statements": [row, {**row, "statement_id": "s2"}]}])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")
        self.assertIn("same cited source span", result.diagnostics[0])

    def test_lexical_negation_overrides_model_asserted_modality(self):
        text = "The valve did not leak during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        row = {"statement_id": "s1", "material_id": "L1", "source_id": "D1", "source_version": "v1",
               "representation_id": "R1", "quote": text, "start_offset": 0,
               "kind": "incident_observation", "modality": "asserted", "scope": "incident", "timing": "incident"}
        model = ScriptedModel([{"statements": [row]}, comparison()])
        result = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(result.payload["source_statements"][0]["modality"], "negated")
        self.assertNotEqual(result.payload["parts"][0]["relation"], "supports")

    def test_unrelated_exact_quote_cannot_support_claim_if_model_marks_unrelated(self):
        text = "Pump P2 was painted blue."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),))
        row = {"statement_id": "s1", "material_id": "L1", "source_id": "D1", "source_version": "v1",
               "representation_id": "R1", "quote": text, "start_offset": 0,
               "kind": "incident_observation", "modality": "reported", "scope": "incident", "timing": "incident"}
        compared = {"parts": [
            {"part_id": "p1", "findings": [finding("supports", ["s1"], "A pump is mentioned.", relevance="unrelated")]},
            {"part_id": "p2", "findings": [finding("does_not_address", ["s1"], "No causal relationship.")]},
        ]}
        result = Hera1Engine(ScriptedModel([{"statements": [row]}, compared]), FixedVersions()).run(task)
        self.assertEqual(result.payload["parts"][0]["relation"], "does_not_address")
        self.assertEqual(result.payload["scope_guard_flags"][0]["rule"], "source_relevance_not_established")

    def test_lexical_timing_conflict_overrides_false_model_match(self):
        text = "The valve leaked during the previous shift."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            hypothesis={"hypothesis_id": "h1", "parts": [
                {"part_id": "p1", "claim_type": "incident_fact", "text": "The valve leaked during this incident."},
                {"part_id": "p2", "claim_type": "incident_fact", "text": "The valve leaked."},
            ]})
        row = {"statement_id": "s1", "material_id": "L1", "source_id": "D1", "source_version": "v1",
               "representation_id": "R1", "quote": text, "start_offset": 0,
               "kind": "incident_observation", "modality": "reported", "scope": "incident", "timing": "incident"}
        compared = {"parts": [
            {"part_id": "p1", "findings": [finding("supports", ["s1"], "Leak is reported.")]},
            {"part_id": "p2", "findings": [finding("supports", ["s1"], "Leak is reported.")]},
        ]}
        result = Hera1Engine(ScriptedModel([{"statements": [row]}, compared]), FixedVersions()).run(task)
        self.assertEqual(result.payload["parts"][0]["relation"], "does_not_address")

    def test_clarification_answered_with_conflicts_is_rejected(self):
        task = AssessmentTask("1", "t-conflict-status", "w-conflict-status", "e-conflict-status", "c1",
            "case:s1", "b1", "clarification_review", "intake", "intake-1",
            clarification={"question_id": "q1", "text": "Was it isolated?"},
            answer={"kind": "human", "question_id": "q1", "text": "Yes."})
        output = {"status": "answered", "summary": "Yes.", "answered_slots": ["isolation"],
                  "open_slots": [], "ambiguities": [], "conflicts": ["Two answers conflict."],
                  "source_passages": []}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions()).run(task)
        self.assertEqual(result.status, "assessment_failed")

    def test_mixed_text_and_visual_packet_is_explicitly_partial(self):
        text = "The valve leaked during the incident."
        task = evidence_task(materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            context={"unassessable_materials": [{"candidate_link_id": "IMG1", "source_id": "D2",
                "source_version": "v1", "representation_id": "FIG2", "modality": "image"}]})
        model = ScriptedModel([extraction(text, "incident_observation", "reported"),
            {"parts": [
                {"part_id": "p1", "findings": [finding("supports", ["s1"], "Incident log report.")]},
                {"part_id": "p2", "findings": [finding("does_not_address", ["s1"], "No causal link.")]},
            ]}])
        result = Hera1Engine(model, FixedVersions(versions={"D1": "v1", "D2": "v1"})).run(task)
        self.assertEqual(result.payload["assessment_coverage"], "partial")
        self.assertEqual(result.payload["unassessable_materials"][0]["candidate_link_id"], "IMG1")

    def test_partial_document_clarification_retains_unassessed_material_details(self):
        text = "YOLK is the yellow overload-lock key."
        task = AssessmentTask("1", "t-partial-visual", "w-partial-visual", "e-partial-visual", "c1", "case:s1", "b1",
            "clarification_review", "evidence_worker", "ew1",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text),),
            clarification={"question_id": "q1", "text": "What does YOLK mean?"},
            answer={"kind": "document", "question_id": "q1"},
            context={"unassessable_materials": [{"candidate_link_id": "IMG1", "source_id": "D2",
                "source_version": "v1", "representation_id": "FIG1", "modality": "image"}]})
        citation = {"material_id": "L1", "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                    "quote": text, "start_offset": 0, "answered_slot": "YOLK meaning"}
        output = {"status": "partial", "summary": "The text defines the term, image not inspected.",
                  "answered_slots": ["YOLK meaning"], "open_slots": ["What does the diagram show?"],
                  "ambiguities": [], "conflicts": [], "source_passages": [citation]}
        result = Hera1Engine(ScriptedModel([output]), FixedVersions(versions={"D1": "v1", "D2": "v1"})).run(task)
        self.assertEqual(result.payload["status"], "partial")
        self.assertEqual(result.payload["unassessable_materials"][0]["candidate_link_id"], "IMG1")

    def test_stale_unassessable_material_version_is_checked(self):
        task = evidence_task(context={"unassessable_materials": [{"candidate_link_id": "IMG1",
            "source_id": "D2", "source_version": "v1", "representation_id": "FIG2", "modality": "image"}]})
        result = Hera1Engine(ScriptedModel([]), FixedVersions(versions={"D1": "v1", "D2": "v2"})).run(task)
        self.assertEqual(result.status, "stale")
        self.assertEqual(result.model_calls, 0)

    def test_adapter_connects_sahs_candidate_to_ewv3_passages_without_imports(self):
        sahs = {"assignment_id": "sa-6", "case_snapshot_id": "case:s1", "board_version": "b1", "status": "completed",
                "candidates": [{"candidate_id": "cand-1", "proposition_ids": ["p1"]}]}
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b1", "work_item_id": "w6", "event_id": "e6", "status": "ready_for_assessor", "work_phase": "awaiting_assessor",
                "slot_results": [{"need_id": "need-1", "slot_id": "slot-1", "candidate_links": [{
                    "candidate_link_id": "link-1", "need_id": "need-1", "slot_id": "slot-1",
                    "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                    "start_offset": 120, "exact_text": "A leaking valve can cause pressure loss.",
                    "title": "Manual", "source_kind": "manual", "structural_context": {"page": 2},
                    "score_semantics": "retrieval_rank_only"}]}]}
        route = AssessmentRoute(
            task_id="t6", work_item_id="w6", event_id="e6", case_id="c1",
            case_snapshot_id="case:s1", board_version="b1", worker_id="ew6", specialist_assignment_id="sa-6",
            candidate_id="cand-1", need_id="need-1", slot_ids=("slot-1",),
            hypothesis_parts=({"part_id": "p1", "board_ids": ["p1"], "claim_type": "incident_causal_link",
                               "text": "The leak caused pressure loss during the event."},))
        task = HeraPipelineAdapter.evidence_review(sahs, ewv3, route)
        self.assertEqual(task.hypothesis["hypothesis_id"], "cand-1")
        self.assertEqual(task.materials[0].material_id, "link-1")
        self.assertEqual(task.materials[0].offset_base, 120)
        self.assertEqual(task.sender_id, "ew6")
        extracted = extraction()
        extracted["statements"][0]["material_id"] = "link-1"
        model = ScriptedModel([extracted, {"parts": [
            {"part_id": "p1", "findings": [finding("supports", ["s1"],
                "General mechanism statement.")]}
        ]}])
        assessed = Hera1Engine(model, FixedVersions()).run(task)
        self.assertEqual(assessed.status, "completed")
        self.assertEqual(assessed.payload["evidence_effect"], "insufficient")
        self.assertEqual(assessed.payload["source_statements"][0]["start_offset"], 120)

    def test_adapter_maps_ewv3_request_draft_for_assessor_review(self):
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b1", "work_item_id": "w7", "event_id": "e7", "status": "ready_for_assessor", "work_phase": "awaiting_assessor",
                "request_drafts": [{"request_id": "r4", "request_type": "document_request",
                    "slot_ids": ["slot-2"], "question_or_document": "Provide V-7 maintenance logs.",
                    "requested_fields": ["date", "technician"]}]}
        route = {"task_id": "t7", "work_item_id": "w7", "event_id": "e7", "case_id": "c1",
                 "case_snapshot_id": "case:s1", "board_version": "b1", "request_id": "r4",
                 "target_id": "gap-2", "need_id": "need-2", "slot_ids": ["slot-2"],
                 "worker_id": "ew12", "open_gap": "Whether V-7 was serviced."}
        task = HeraPipelineAdapter.request_review(ewv3, route)
        self.assertEqual(task.task_kind, "request_review")
        self.assertEqual(task.request["kind"], "document_request")
        self.assertEqual(task.request["text"], "Provide V-7 maintenance logs.")
        self.assertEqual(task.sender_id, "ew12")

    def test_adapter_rejects_ew_result_from_another_work_event(self):
        sahs = {"assignment_id": "sa", "case_snapshot_id": "case:s1", "board_version": "b1",
                "candidates": [{"candidate_id": "cand-1"}]}
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b1",
                "work_item_id": "other-work", "event_id": "other-event",
                "status": "ready_for_assessor", "work_phase": "awaiting_assessor", "slot_results": []}
        route = {"task_id": "t", "work_item_id": "w", "event_id": "e", "case_id": "c1",
                 "case_snapshot_id": "case:s1", "board_version": "b1", "candidate_id": "cand-1",
                 "need_id": "n", "worker_id": "ew", "specialist_assignment_id": "sa",
                 "hypothesis_parts": [{"part_id": "p1", "board_ids": ["p1"],
                     "claim_type": "incident_fact", "text": "Something happened."}]}
        with self.assertRaisesRegex(ValueError, "work_item_id"):
            HeraPipelineAdapter.evidence_review(sahs, ewv3, route)

    def test_adapter_rejects_nested_candidate_link_from_wrong_slot(self):
        sahs = {"assignment_id": "sa", "case_snapshot_id": "case:s1", "board_version": "b1",
                "candidates": [{"candidate_id": "cand-1"}]}
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b1", "work_item_id": "w",
                "event_id": "e", "status": "ready_for_assessor", "work_phase": "awaiting_assessor", "slot_results": [{
                    "need_id": "n", "slot_id": "s1", "candidate_links": [{
                        "candidate_link_id": "l1", "need_id": "n", "slot_id": "s2",
                        "source_id": "D1", "source_version": "v1", "representation_id": "R1",
                        "start_offset": 0, "end_offset": 5, "exact_text": "hello"}]}]}
        route = {"task_id": "t", "work_item_id": "w", "event_id": "e", "case_id": "c1",
                 "case_snapshot_id": "case:s1", "board_version": "b1", "candidate_id": "cand-1",
                 "need_id": "n", "slot_ids": ["s1"], "worker_id": "ew", "specialist_assignment_id": "sa",
                 "hypothesis_parts": [{"part_id": "p1", "board_ids": ["p1"],
                     "claim_type": "incident_fact", "text": "Something happened."}]}
        with self.assertRaisesRegex(ValueError, "nested EWV3 candidate link"):
            HeraPipelineAdapter.evidence_review(sahs, ewv3, route)

    def test_request_review_receives_search_coverage_and_found_material(self):
        snippet = {"candidate_link_id": "l1", "need_id": "n", "slot_id": "s1", "source_id": "D1",
                   "source_version": "v1", "representation_id": "R1", "start_offset": 0,
                   "end_offset": 20, "exact_text": "Valve was serviced.", "source_kind": "log"}
        ewv3 = {"case_snapshot_id": "case:s1", "board_version": "b1", "work_item_id": "w", "event_id": "e",
                "status": "ready_for_assessor", "work_phase": "awaiting_assessor", "search_pass_status": "bounded_pass_complete",
                "slot_results": [{"need_id": "n", "slot_id": "s1", "coverage": "candidate_found",
                                  "candidate_links": [snippet]}],
                "request_drafts": [{"request_id": "r", "request_type": "incident_question",
                    "slot_ids": ["s1"], "question_or_document": "Was the valve serviced?"}]}
        route = {"task_id": "t", "work_item_id": "w", "event_id": "e", "case_id": "c1",
                 "case_snapshot_id": "case:s1", "board_version": "b1", "request_id": "r", "target_id": "gap",
                 "need_id": "n", "slot_ids": ["s1"], "worker_id": "ew", "open_gap": "Service status."}
        task = HeraPipelineAdapter.request_review(ewv3, route)
        self.assertEqual(task.request["request_type"], "incident_question")
        self.assertEqual(task.context["slot_coverage"][0]["coverage"], "candidate_found")
        self.assertEqual(task.context["existing_candidate_links"][0]["source_id"], "D1")

    def test_adapters_accept_actual_sahs_and_ewv3_dataclass_outputs(self):
        source_ref = CandidateLink(
            candidate_link_id="actual-link", need_id="actual-need", slot_id="actual-slot",
            source_id="D1", source_version="v1", representation_id="R1",
            start_offset=10, end_offset=52, exact_text="Valve leaked during the incident.",
            title="Inspection log", source_kind="incident_log", channel="keyword", score=0.8)
        ew = EvidenceWorkerResult(
            schema_version="1", assignment_id="ew-assignment", work_item_id="actual-work",
            event_id="actual-event", case_snapshot_id="case:s1", board_version="b1",
            corpus_snapshot_id="corpus-1", material_catalog_version="catalog-1",
            representation_version="repr-1", status="ready_for_assessor",
            work_phase=WorkPhase.AWAITING_ASSESSOR,
            search_pass_status=SearchPassStatus.COMPLETE,
            slot_results=(SlotResult("actual-need", "actual-slot", "candidate_found", (source_ref,)),))
        candidate = CandidateExplanation(
            candidate_id="actual-candidate", target_proposition_id="p1", proposition_ids=("p1",),
            rule_ids=(), reported_premise_ids=(), assumptions=(), source_refs=(), solver_trace=(),
            candidate_fingerprint="fingerprint")
        sahs = SpecialistResult(
            schema_version="1", assignment_id="sahs-assignment", case_snapshot_id="case:s1",
            board_version="b1", history_version="history-1", input_fingerprint="fp",
            status="completed", graph_delta=CausalGraph(), candidates=(candidate,))
        route = {"task_id": "actual-task", "work_item_id": "actual-work", "event_id": "actual-event",
            "case_id": "c1", "case_snapshot_id": "case:s1", "board_version": "b1",
            "specialist_assignment_id": "sahs-assignment",
            "worker_id": "ew-actual", "candidate_id": "actual-candidate", "need_id": "actual-need",
            "slot_ids": ["actual-slot"], "hypothesis_parts": [{"part_id": "p1", "board_ids": ["p1"],
            "claim_type": "incident_fact", "text": "The valve leaked during the incident."}]}
        task = HeraPipelineAdapter.evidence_review(sahs, ew, route)
        self.assertEqual(task.materials[0].source_id, "D1")
        self.assertEqual(task.materials[0].offset_base, 10)
        self.assertEqual(task.hypothesis["hypothesis_id"], "actual-candidate")

    def test_adapter_maps_sahs_clarification_and_human_answer(self):
        sahs = {"assignment_id": "sa-8", "case_snapshot_id": "case:s1", "board_version": "b1",
                "clarification_items": [{"clarification_id": "q3", "question": "What does YOLK mean?",
                                         "why_it_matters": "Configuration is unclear."}]}
        route = {"task_id": "t8", "work_item_id": "w8", "event_id": "e8", "case_id": "c1",
                 "case_snapshot_id": "case:s1", "board_version": "b1", "clarification_id": "q3",
                 "specialist_assignment_id": "sa-8"}
        task = HeraPipelineAdapter.clarification_review(
            sahs, route, {"kind": "human", "question_id": "q3", "text": "It is the yellow overload lock."})
        self.assertEqual(task.clarification["question_id"], "q3")
        self.assertEqual(task.answer["kind"], "human")

    def test_adapter_rejects_mixed_snapshot_outputs(self):
        sahs = {"case_snapshot_id": "case:s1", "board_version": "b1", "candidates": []}
        ewv3 = {"case_snapshot_id": "case:s2", "board_version": "b1", "slot_results": []}
        route = {"case_snapshot_id": "case:s1", "board_version": "b1"}
        with self.assertRaises(ValueError):
            HeraPipelineAdapter.evidence_review(sahs, ewv3, route)


if __name__ == "__main__":
    unittest.main()

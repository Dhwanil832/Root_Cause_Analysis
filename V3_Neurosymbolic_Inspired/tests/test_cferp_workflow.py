"""Scenario checks for the complete standalone CFERP workflow layer."""
from dataclasses import replace
import unittest

from cferp import CFERPWorkflow, RoleResult
from cferp.contracts import (
    CandidateAction, EvidencePacket, InformationSlot, JobState, Need, NeedState, OutwardRequest,
    RequestDisposition, Role, SlotState,
)
from cferp.engine import CFERPError
from cferp.workflow import (
    AssessmentEffect, BranchState, CaseState, MaterialRecord,
)


def setup_workflow():
    wf = CFERPWorkflow("CASE-9")
    wf.register_material(event_id="MAT-E1", material=MaterialRecord(
        "DOC-1", "v1", "hash-1", "Hydraulic manual", "manual",
        content="A leaking valve can cause hydraulic pressure loss."))
    assignments = wf.initialize_case(
        event_id="CASE-E1",
        case_packet={"reported_claims": [{"claim_id": "H0", "text": "Carrier beam fell", "kind": "case_claim"}]},
        specialist_profiles=(
            {"profile_id": "mechanical", "cues": ["carrier beam"], "direction": "develop mechanical alternatives"},
            {"profile_id": "electrical", "cues": ["motor"], "direction": "develop electrical alternatives"},
            {"profile_id": "other", "cues": [], "direction": "check undocumented alternatives"},
        ),
    )
    return wf, assignments[0]


class CFERPWorkflowTests(unittest.TestCase):
    def test_semantic_assignment_refinement_cannot_expand_lead_scope(self):
        class Assistant:
            def suggest_matches(self, kind, candidate, existing):
                return ()

            def clarify_assignment(self, assignment):
                return {"purpose": "clarify the valve configuration",
                        "target_ids": assignment.target_ids,
                        "need_ids": assignment.need_ids,
                        "context_additions": {"routing_note": "configuration ambiguity"}}

        wf, specialist = setup_workflow()
        wf.semantic_assistant = Assistant()
        refined = wf.refine_ambiguous_assignment(specialist.assignment_id)
        self.assertEqual(refined.purpose, "clarify the valve configuration")
        self.assertEqual(refined.target_ids, specialist.target_ids)
        self.assertEqual(refined.context["routing_note"], "configuration ambiguity")
        self.assertEqual(refined.context["refined_from"], specialist.assignment_id)
        self.assertEqual(wf.lead.work[specialist.assignment_id].state, JobState.SUPERSEDED)
        self.assertNotIn(specialist.assignment_id, {a.assignment_id for a in wf.schedule()})

        class ScopeExpander(Assistant):
            def clarify_assignment(self, assignment):
                return {"target_ids": ("unassigned-claim",)}

        wf.semantic_assistant = ScopeExpander()
        with self.assertRaisesRegex(CFERPError, "cannot expand assignment targets"):
            wf.refine_ambiguous_assignment(refined.assignment_id)

    def test_semantic_refinement_is_discarded_if_snapshot_changes_during_call(self):
        wf, specialist = setup_workflow()

        class MutatingAssistant:
            def suggest_matches(self, kind, candidate, existing):
                return ()

            def clarify_assignment(self, assignment):
                wf.lead.ingest_event("BOARD-CHANGED-IN-CALL", "board_changed",
                                     {"changed_dependency_ids": ("H0",)})
                return {"purpose": "stale refined work"}

        wf.semantic_assistant = MutatingAssistant()
        before = set(wf.assignments)
        with self.assertRaisesRegex(CFERPError, "snapshot changed while"):
            wf.refine_ambiguous_assignment(specialist.assignment_id)
        self.assertEqual(set(wf.assignments), before)
        self.assertEqual(wf.lead.work[specialist.assignment_id].state, JobState.STALE)

    def test_semantic_provider_failure_falls_back_without_aborting_material_scope(self):
        wf, _ = setup_workflow()

        class FailingAssistant:
            def suggest_matches(self, kind, candidate, existing):
                raise TimeoutError("simulated provider timeout")
            def clarify_assignment(self, assignment):
                raise TimeoutError("simulated provider timeout")

        wf.semantic_assistant = FailingAssistant()
        self.assertEqual(wf.suggest_semantic_matches(kind="material_scope",
            candidate={"id": "DOC-X"}, existing=({"id": "need:N1"},)), ())
        self.assertEqual(wf.semantic_diagnostics[-1], "semantic_match_failed:TimeoutError")
        material = MaterialRecord("DOC-X", "v1", "hash-x", "New log", "log",
                                  provenance_complete=True)
        wf.register_material(event_id="MAT-X", material=material)
        self.assertIn("DOC-X", wf.materials)
        self.assertEqual(wf.materials["DOC-X"].related_need_ids, ())

        wf2, specialist = setup_workflow()
        wf2.semantic_assistant = FailingAssistant()
        result = wf2.refine_ambiguous_assignment(specialist.assignment_id)
        self.assertEqual(result, specialist)
        self.assertEqual(wf2.lead.work[specialist.assignment_id].state, JobState.QUEUED)
        self.assertEqual(wf2.semantic_diagnostics[-1], "assignment_refinement_failed:TimeoutError")

    def test_semantic_match_rejects_bad_ids_and_stale_results_without_failing_intake(self):
        wf, _ = setup_workflow()

        class UnknownIDAssistant:
            def suggest_matches(self, kind, candidate, existing):
                return ("need:invented",)
            def clarify_assignment(self, assignment):
                return {}

        wf.semantic_assistant = UnknownIDAssistant()
        self.assertEqual(wf.suggest_semantic_matches(kind="material_scope",
            candidate={"id": "DOC-X"}, existing=({"id": "need:N1"},)), ())
        self.assertEqual(wf.semantic_diagnostics[-1], "semantic_match_out_of_scope_ids")

        class StaleAssistant(UnknownIDAssistant):
            def suggest_matches(self, kind, candidate, existing):
                wf.lead.ingest_event("SEMANTIC-BOARD-CHANGE", "board_changed",
                                     {"changed_dependency_ids": ("H0",)})
                return ("need:N1",)

        wf.semantic_assistant = StaleAssistant()
        self.assertEqual(wf.suggest_semantic_matches(kind="material_scope",
            candidate={"id": "DOC-X"}, existing=({"id": "need:N1"},)), ())
        self.assertEqual(wf.semantic_diagnostics[-1], "semantic_match_stale_snapshot")

    def test_assignment_refinement_cannot_remove_all_scope(self):
        wf, specialist = setup_workflow()

        class EmptyScopeAssistant:
            def suggest_matches(self, kind, candidate, existing):
                return ()
            def clarify_assignment(self, assignment):
                return {"target_ids": [], "need_ids": []}

        wf.semantic_assistant = EmptyScopeAssistant()
        before = set(wf.assignments)
        with self.assertRaisesRegex(CFERPError, "cannot remove all assignment targets and needs"):
            wf.refine_ambiguous_assignment(specialist.assignment_id)
        self.assertEqual(set(wf.assignments), before)
        self.assertEqual(wf.lead.work[specialist.assignment_id].state, JobState.QUEUED)

    def test_semantic_false_positive_only_routes_retrieval_not_an_assessment(self):
        wf, _ = setup_workflow()
        wf.lead.add_need(Need("N-open", "specialist", "H0", ("H0",),
            (InformationSlot("S-open", "check a maintenance detail"),)))

        class FalsePositiveAssistant:
            def suggest_matches(self, kind, candidate, existing):
                return ("need:N-open",)
            def clarify_assignment(self, assignment):
                return {}

        wf.semantic_assistant = FalsePositiveAssistant()
        routed = wf.register_material(event_id="MAT-FP", material=MaterialRecord(
            "DOC-FP", "v1", "hash-fp", "Possibly relevant document", "record"))
        self.assertEqual(wf.materials["DOC-FP"].related_need_ids, ("N-open",))
        self.assertTrue(any(item.role == Role.EVIDENCE_WORKER for item in routed))
        self.assertEqual(wf.assessments, {})

    def test_initialization_replay_returns_same_assignments_without_duplicate_claims(self):
        wf, first = setup_workflow()
        replay = wf.initialize_case(
            event_id="CASE-E1",
            case_packet={"reported_claims": [{"claim_id": "H0", "text": "Carrier beam fell",
                                               "kind": "case_claim"}]},
            specialist_profiles=(
                {"profile_id": "mechanical", "cues": ["carrier beam"], "direction": "develop mechanical alternatives"},
                {"profile_id": "electrical", "cues": ["motor"], "direction": "develop electrical alternatives"},
                {"profile_id": "other", "cues": [], "direction": "check undocumented alternatives"},
            ),
        )
        self.assertEqual(replay, (first, next(a for a in wf.assignments.values() if a.owner_id == "other")))
        self.assertEqual(tuple(wf.claims), ("H0",))
        with self.assertRaisesRegex(CFERPError, "reused with different content"):
            wf.initialize_case(event_id="CASE-E1", case_packet={"reported_claims": []},
                specialist_profiles=({"profile_id": "other", "cues": [], "direction": "other"},))

    def test_material_event_replay_cannot_partially_mutate_catalog(self):
        wf, _ = setup_workflow()
        original_manifest = wf.lead.manifest()
        exact = MaterialRecord("DOC-1", "v1", "hash-1", "Hydraulic manual", "manual",
                               content="A leaking valve can cause hydraulic pressure loss.")
        self.assertEqual(wf.register_material(event_id="MAT-E1", material=exact), ())
        with self.assertRaisesRegex(CFERPError, "reused with different material"):
            wf.register_material(event_id="MAT-E1", material=MaterialRecord(
                "DOC-1", "v2", "hash-2", "Revised hydraulic manual", "manual", content="Revised text."))
        self.assertEqual(wf.materials["DOC-1"].version, "v1")
        self.assertEqual(wf.lead.manifest(), original_manifest)

    def test_material_event_replay_does_not_duplicate_external_response(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked",
                "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [
                    {"slot_id": "s1", "description": "leak"}]}]}))
        request = OutwardRequest("REQ-R", ("N1",), ("H1",), ("s1",), "Provide record",
                                 "question", state=RequestDisposition.WAITING_RESPONSE)
        wf.lead.add_request(request)
        material = MaterialRecord("R-DOC", "v1", "rh", "response", "witness", content="Response text")
        wf.register_external_response(event_id="RESP-E1", request_id="REQ-R", material=material)
        wf.register_external_response(event_id="RESP-E1", request_id="REQ-R", material=material)
        self.assertEqual(wf.request_responses["REQ-R"], ["R-DOC"])
        self.assertEqual(wf.lead.requests["REQ-R"].response_material_ids, ("R-DOC",))

    def test_initial_selection_includes_cue_match_and_other_then_scheduler_caps(self):
        wf, _ = setup_workflow()
        self.assertEqual({a.owner_id for a in wf.assignments.values()}, {"mechanical", "other"})
        selected = wf.schedule()
        self.assertEqual(len(selected), 2)
        for assignment in selected:
            wf.start_assignment(assignment.assignment_id)

    def test_specialist_delta_creates_board_need_and_worker_assignment(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        output = RoleResult(
            "SR-1", specialist.assignment_id, Role.SPECIALIST, specialist.manifest,
            {"claims": [{"claim_id": "H1", "text": "A valve leak reduced hydraulic pressure",
                         "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
             "causal_links": [{"source_claim_ids": ["H1"], "target_claim_id": "H0",
                               "relation": "may_cause", "basis": "model_proposed"}],
             "needs": [{"need_id": "N1", "target_ids": ["H1"],
                        "slots": [{"slot_id": "leak", "description": "Was a valve leaking?"}]}]},
        )
        created = wf.submit_specialist_result(output)
        self.assertIn("H1", wf.claims)
        self.assertEqual(wf.claims["H1"].incident_status, "hypothetical")
        self.assertEqual(len(wf.causal_links), 1)
        self.assertIn("N1", wf.lead.needs)
        ew = next(a for a in created if a.role == Role.EVIDENCE_WORKER)
        self.assertEqual(ew.context["source_catalog"][0].material_id, "DOC-1")

    def test_invalid_specialist_delta_is_rejected_before_board_mutation(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        result = RoleResult("SR-invalid", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H-bad", "text": "invented", "branch_id": "B1",
                "kind": "incident_event", "parent_claim_ids": ["missing-claim"]}]})
        with self.assertRaisesRegex(CFERPError, "unknown parent"):
            wf.submit_specialist_result(result)
        self.assertNotIn("H-bad", wf.claims)
        self.assertNotIn("SR-invalid", wf.result_fingerprints)
        self.assertEqual(wf.lead.work[specialist.assignment_id].state, JobState.RUNNING)

    def test_worker_passages_are_routed_to_assessor_not_promoted(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked",
            "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(ew.assignment_id)
        result = RoleResult("EWR-1", ew.assignment_id, Role.EVIDENCE_WORKER, ew.manifest,
            {"packets": [{"packet_id": "P1", "covered_slot_ids": ["s1"],
                "candidate_links": [{"claim_id": "H1", "material_id": "DOC-1", "material_version": "v1",
                    "passage_id": "p1", "start_offset": 0, "end_offset": 51,
                    "exact_text": "A leaking valve can cause hydraulic pressure loss."}]}]})
        assessors = wf.submit_worker_result(result)
        self.assertEqual(len(assessors), 1)
        self.assertEqual(assessors[0].role, Role.ASSESSOR)
        self.assertEqual(wf.claims["H1"].incident_status, "hypothetical")
        wf.start_assignment(assessors[0].assignment_id)
        specialist_revisions = wf.submit_assessor_result(RoleResult("AR-1", assessors[0].assignment_id,
            Role.ASSESSOR, assessors[0].manifest,
            {"task_kind": "evidence_review", "assessments": [{"claim_id": "H1", "material_id": "DOC-1",
                "material_version": "v1", "passage_id": "p1",
                "exact_text": "A leaking valve can cause hydraulic pressure loss.",
                "effect": "supports", "rationale": "Describes a general mechanism."}]}))
        self.assertEqual(len(wf.assessments), 1)
        self.assertEqual(next(iter(wf.assessments.values())).effect, AssessmentEffect.SUPPORTS)
        self.assertEqual(wf.claims["H1"].incident_status, "hypothetical")
        self.assertTrue(any(a.role == Role.SPECIALIST for a in specialist_revisions))
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.COMPLETE)

    def test_worker_cannot_return_known_claim_outside_assignment_scope(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked",
                "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [
                    {"slot_id": "s1", "description": "leak"}]}]}))
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(ew.assignment_id)
        result = RoleResult("EWR-OUT-OF-SCOPE", ew.assignment_id, Role.EVIDENCE_WORKER, ew.manifest,
            {"packets": [{"packet_id": "P-bad", "target_ids": ["H0"], "covered_slot_ids": ["s1"],
                "candidate_links": [{"claim_id": "H0", "material_id": "DOC-1", "material_version": "v1",
                    "passage_id": "p1", "exact_text": "A leaking valve can cause hydraulic pressure loss."}]}]})
        with self.assertRaisesRegex(CFERPError, "targets exceed"):
            wf.submit_worker_result(result)
        self.assertNotIn(result.result_id, wf.result_fingerprints)
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.RUNNING)
        wrong_request = RoleResult("EWR-OUT-OF-SCOPE-REQUEST", ew.assignment_id, Role.EVIDENCE_WORKER,
            ew.manifest, {"requests": [{"request_id": "REQ-BAD", "target_ids": ["H0"],
                "origin_ids": ["N1"], "slot_ids": ["s1"], "wording": "Investigate unrelated claim",
                "request_kind": "question"}]})
        with self.assertRaisesRegex(CFERPError, "request targets exceed"):
            wf.submit_worker_result(wrong_request)
        self.assertNotIn(wrong_request.result_id, wf.result_fingerprints)

    def test_assessor_cannot_review_a_different_claim_or_passage(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked",
                "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [
                    {"slot_id": "s1", "description": "leak"}]}]}))
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(ew.assignment_id)
        assessor = wf.submit_worker_result(RoleResult("EWR-1", ew.assignment_id, Role.EVIDENCE_WORKER,
            ew.manifest, {"packets": [{"packet_id": "P1", "covered_slot_ids": ["s1"],
                "candidate_links": [{"claim_id": "H1", "material_id": "DOC-1", "material_version": "v1",
                    "passage_id": "p1", "exact_text": "A leaking valve can cause hydraulic pressure loss."}]}]}))[0]
        wf.start_assignment(assessor.assignment_id)
        malicious = RoleResult("AR-WRONG-LINK", assessor.assignment_id, Role.ASSESSOR, assessor.manifest,
            {"assessments": [{"claim_id": "H0", "material_id": "DOC-1", "material_version": "v1",
                "passage_id": "p1", "exact_text": "A leaking valve can cause hydraulic pressure loss.",
                "effect": "supports", "rationale": "wrong target"}]})
        with self.assertRaisesRegex(CFERPError, "outside the assigned target"):
            wf.submit_assessor_result(malicious)
        self.assertNotIn(malicious.result_id, wf.result_fingerprints)
        wrong_passage = RoleResult("AR-WRONG-PASSAGE", assessor.assignment_id, Role.ASSESSOR,
            assessor.manifest, {"assessments": [{"claim_id": "H1", "material_id": "DOC-1", "material_version": "v1",
                "passage_id": "p2", "exact_text": "A leaking valve can cause hydraulic pressure loss.",
                "effect": "neutral", "rationale": "wrong passage ID"}]})
        with self.assertRaisesRegex(CFERPError, "differs from its assigned candidate passage"):
            wf.submit_assessor_result(wrong_passage)

    def test_clarification_answer_must_pass_assessor_before_specialist_reuse(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "clarifications": [{"need_id": "N-term", "target_ids": ["H1"], "question": "What is a yolk?"}]}))
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(ew.assignment_id)
        reviewers = wf.submit_worker_result(RoleResult("EWR-1", ew.assignment_id, Role.EVIDENCE_WORKER,
            ew.manifest, {"clarification_answers": [{"need_id": "N-term", "answer_id": "ANS1",
                "answer_text": "In this plant, yolk means the actuator sleeve."}]}))
        self.assertEqual(reviewers[0].context["task_kind"], "clarification_review")
        wf.start_assignment(reviewers[0].assignment_id)
        wrong_review = RoleResult("AR-WRONG-CLARIFICATION", reviewers[0].assignment_id,
            Role.ASSESSOR, reviewers[0].manifest,
            {"task_kind": "clarification_review", "clarification_id": "clarification:another-answer",
             "decision": "accepted"})
        with self.assertRaisesRegex(CFERPError, "does not match its assigned answer"):
            wf.submit_assessor_result(wrong_review)
        revised = wf.submit_assessor_result(RoleResult("AR1", reviewers[0].assignment_id,
            Role.ASSESSOR, reviewers[0].manifest, {"task_kind": "clarification_review",
                "clarification_id": "clarification:N-term", "decision": "accepted"}))
        self.assertEqual(len(revised), 1)
        self.assertEqual(revised[0].role, Role.SPECIALIST)
        self.assertEqual(wf.clarifications["clarification:N-term"].assessor_status, "accepted")

    def test_ambiguous_clarification_stays_for_lead_and_does_not_spawn_specialist(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-amb", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
                "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "clarifications": [{"need_id": "N-term", "target_ids": ["H1"], "question": "What is a yolk?"}]}))
        worker = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(worker.assignment_id)
        assessor = wf.submit_worker_result(RoleResult("EWR-amb", worker.assignment_id, Role.EVIDENCE_WORKER,
            worker.manifest, {"clarification_answers": [{"need_id": "N-term", "answer_id": "ANS-amb",
                "answer_text": "It might mean the sleeve, but I am unsure."}]}))[0]
        wf.start_assignment(assessor.assignment_id)
        before = set(wf.assignments)
        routed = wf.submit_assessor_result(RoleResult("AR-amb", assessor.assignment_id, Role.ASSESSOR,
            assessor.manifest, {"task_kind": "clarification_review", "clarification_id": "clarification:N-term",
                "decision": "ambiguous", "assessor_context": {"status": "conflicting"}}))
        self.assertEqual(routed, ())
        self.assertEqual(set(wf.assignments), before)
        self.assertEqual(wf.clarifications["clarification:N-term"].assessor_status, "ambiguous")

    def test_assessor_request_revision_text_is_preserved_for_worker_retry(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-revise", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
                "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        worker = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(worker.assignment_id)
        review = wf.submit_worker_result(RoleResult("EWR-revise", worker.assignment_id, Role.EVIDENCE_WORKER,
            worker.manifest, {"requests": [{"request_id": "REQ-revise", "target_ids": ["H1"],
                "origin_ids": ["N1"], "slot_ids": ["s1"], "wording": "Provide the inspection record.",
                "request_kind": "document_request"}]}))[0]
        wf.start_assignment(review.assignment_id)
        revised_text = "Provide the inspection record for V-13 during the incident window."
        result = wf.submit_assessor_result(RoleResult("AR-revise", review.assignment_id, Role.ASSESSOR,
            review.manifest, {"task_kind": "request_review", "request_id": "REQ-revise",
                "disposition": "revise", "feedback": "Name the component and time window.",
                "revised_request": revised_text}))
        retry = next(item for item in result if item.role == Role.EVIDENCE_WORKER)
        self.assertEqual(retry.context["revised_request"], revised_text)

    def test_request_review_requires_lead_send_and_external_reply_remains_unassessed(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(ew.assignment_id)
        review = wf.submit_worker_result(RoleResult("EWR-1", ew.assignment_id, Role.EVIDENCE_WORKER,
            ew.manifest, {"requests": [{"request_id": "REQ-A", "target_ids": ["H1"], "origin_ids": ["N1"],
                "slot_ids": ["s1"], "wording": "Provide the valve inspection record", "request_kind": "document_request"}]}))[0]
        wf.start_assignment(review.assignment_id)
        wrong_review = RoleResult("AR-wrong-request", review.assignment_id, Role.ASSESSOR,
            review.manifest, {"task_kind": "request_review", "request_id": "REQ-OTHER", "disposition": "pass"})
        with self.assertRaisesRegex(CFERPError, "does not match its assigned request"):
            wf.submit_assessor_result(wrong_review)
        wf.submit_assessor_result(RoleResult("AR-req", review.assignment_id, Role.ASSESSOR,
            review.manifest, {"task_kind": "request_review", "request_id": "REQ-A", "disposition": "pass"}))
        self.assertEqual(wf.lead.requests["REQ-A"].state, RequestDisposition.APPROVED)
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.AWAITING_ASSESSOR)
        action = wf.send_approved_request("REQ-A")
        wf.acknowledge_request_dispatch(action.action_id, success=True)
        self.assertEqual(wf.lead.requests["REQ-A"].state, RequestDisposition.WAITING_RESPONSE)
        response_assignments = wf.register_external_response(event_id="RESP-1", request_id="REQ-A",
            material=MaterialRecord("WIT-1", "v1", "hw1", "Witness response", "witness",
                content="I did not see a leak."), answered_slot_ids=("s1",))
        self.assertEqual(wf.lead.requests["REQ-A"].state, RequestDisposition.PARTIALLY_ANSWERED)
        self.assertIn("WIT-1", wf.materials)
        self.assertTrue(any(a.role == Role.EVIDENCE_WORKER for a in response_assignments))
        self.assertEqual(wf.lead.needs["N1"].slots[0].state, SlotState.OPEN)

    def test_a_prime_gets_own_packet_and_assessor_route_without_merging_request_identity(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        manifest = wf.lead.manifest()
        common = dict(target_ids=("H1",), slot_ids=("s1",), source_scope=("DOC-1",),
            entity_ids=("valve-1",), time_scope="incident", record_types=("inspection",),
            source_versions=(("DOC-1", "v1", "hash-1"),), material_index_version=manifest.material_index_version)
        wf.lead.add_request(OutwardRequest("REQ-A", ("N1",), wording="Find the valve inspection record",
            request_kind="document_request", **common))
        wf.lead.add_request(OutwardRequest("REQ-A-prime", ("N1",), wording="Was the valve inspected?",
            request_kind="question", **common))
        candidate_link = {"claim_id": "H1", "material_id": "DOC-1", "material_version": "v1",
            "passage_id": "p1", "exact_text": "A leaking valve can cause hydraulic pressure loss."}
        source = EvidencePacket("P-A", "REQ-A", ("H1",), ("s1",), ("DOC-1",), ("valve-1",),
            "incident", ("inspection",), (("DOC-1", "v1", "hash-1"),), manifest.material_index_version,
            {"candidate_links": [candidate_link]})
        wf.lead.register_packet(source)
        copied, ew_copy, assessor_routes = wf.reuse_search_packet(
            source_packet_id="P-A", target_request_id="REQ-A-prime", new_packet_id="P-A-prime")
        self.assertEqual(copied.request_id, "REQ-A-prime")
        self.assertEqual(copied.parent_packet_id, "P-A")
        self.assertEqual(wf.lead.requests["REQ-A"].wording, "Find the valve inspection record")
        self.assertEqual(wf.lead.requests["REQ-A-prime"].wording, "Was the valve inspected?")
        self.assertEqual(len(assessor_routes), 2)  # claim-material review plus request review
        self.assertTrue(all(a.role == Role.ASSESSOR for a in assessor_routes))
        self.assertEqual(wf.lead.work[ew_copy.assignment_id].state, JobState.AWAITING_ASSESSOR)

    def test_stale_a_packet_cannot_be_reused_after_new_material_arrives(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked",
                "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [
                    {"slot_id": "s1", "description": "inspection", "entity_id": "valve-1",
                     "time_scope": "incident", "record_type": "inspection"}]}]}))
        manifest = wf.lead.manifest()
        scope = dict(target_ids=("H1",), slot_ids=("s1",), source_scope=("DOC-1",),
            entity_ids=("valve-1",), time_scope="incident", record_types=("inspection",),
            source_versions=(("DOC-1", "v1", "hash-1"),), material_index_version=manifest.material_index_version)
        wf.lead.add_request(OutwardRequest("REQ-A", ("N1",), wording="Request A",
            request_kind="document_request", **scope))
        wf.lead.add_request(OutwardRequest("REQ-A-prime", ("N1",), wording="Request A prime",
            request_kind="question", **scope))
        source = EvidencePacket("P-A", "REQ-A", ("H1",), ("s1",), ("DOC-1",), ("valve-1",),
            "incident", ("inspection",), (("DOC-1", "v1", "hash-1"),), manifest.material_index_version,
            {"candidate_links": [{"claim_id": "H1", "need_ids": ["N1"], "material_id": "DOC-1",
                "material_version": "v1", "passage_id": "p1",
                "exact_text": "A leaking valve can cause hydraulic pressure loss."}]})
        wf.lead.register_packet(source)
        wf.register_material(event_id="MAT-E2", material=MaterialRecord("DOC-2", "v1", "hash-2",
            "New inspection record", "inspection", content="Valve inspection record."))
        with self.assertRaisesRegex(CFERPError, "material index changed"):
            wf.reuse_search_packet(source_packet_id="P-A", target_request_id="REQ-A-prime",
                                   new_packet_id="P-A-prime")

    def test_partial_a_prime_packet_copy_still_gets_evidence_assessor_review(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked",
                "branch_id": "B1", "kind": "incident_event", "parent_claim_ids": ["H0"]}],
                "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [
                    {"slot_id": "s1", "description": "inspection", "entity_id": "valve-1",
                     "time_scope": "incident", "record_type": "inspection"}]}]}))
        manifest = wf.lead.manifest()
        common = dict(target_ids=("H1",), source_scope=("DOC-1",), entity_ids=("valve-1",),
            time_scope="incident", record_types=("inspection",), source_versions=(("DOC-1", "v1", "hash-1"),),
            material_index_version=manifest.material_index_version)
        wf.lead.add_request(OutwardRequest("REQ-A", ("N1",), ("H1",), ("s1",), wording="A",
            request_kind="question", **{k: v for k, v in common.items() if k != "target_ids"}))
        wf.lead.add_request(OutwardRequest("REQ-A-prime", ("N1",), ("H1",), ("s1", "s2"),
            wording="A prime", request_kind="question",
            **{k: v for k, v in common.items() if k != "target_ids"}))
        link = {"claim_id": "H1", "need_ids": ["N1"], "material_id": "DOC-1", "material_version": "v1",
            "passage_id": "p1", "exact_text": "A leaking valve can cause hydraulic pressure loss."}
        source = EvidencePacket("P-A", "REQ-A", ("H1",), ("s1",), ("DOC-1",), ("valve-1",),
            "incident", ("inspection",), (("DOC-1", "v1", "hash-1"),), manifest.material_index_version,
            {"candidate_links": [link]}, slot_payloads=(("s1", {"candidate_links": [link]}),))
        wf.lead.register_packet(source)
        copied, _, reviews = wf.reuse_search_packet(source_packet_id="P-A", target_request_id="REQ-A-prime",
                                                     new_packet_id="P-A-prime")
        self.assertTrue(copied.is_partial_reuse)
        self.assertEqual(copied.result_payload["uncovered_slot_ids"], ("s2",))
        self.assertEqual([a.context["task_kind"] for a in reviews], ["evidence_review", "request_review"])

    def test_first_arriving_need_runs_search_and_second_gets_a_separate_packet_copy(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        # A one-word question is too short for intake folding to compare, so the
        # second need is kept and served by a packet copy instead.
        slot = {"slot_id": "s1", "description": "inspection",
                "entity_id": "valve-1", "time_scope": "incident",
                "record_type": "inspection"}
        created = wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id,
            Role.SPECIALIST, specialist.manifest,
            {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
                "kind": "incident_event", "parent_claim_ids": ["H0"]}],
             "needs": [
                {"need_id": "N1", "target_ids": ["H1"], "source_scope": ["DOC-1"], "slots": [slot]},
                {"need_id": "N2", "target_ids": ["H1"], "source_scope": ["DOC-1"], "slots": [slot]},
             ]}))
        workers = [a for a in created if a.role == Role.EVIDENCE_WORKER]
        self.assertEqual(len(workers), 1)
        first = workers[0]
        wf.start_assignment(first.assignment_id)
        source_versions = wf.lead.manifest().source_versions
        produced = wf.submit_worker_result(RoleResult("EW-1", first.assignment_id,
            Role.EVIDENCE_WORKER, first.manifest,
            {"packets": [{"packet_id": "P-N1", "target_ids": ["H1"],
                "covered_slot_ids": ["s1"], "source_scope": ["DOC-1"],
                "entity_ids": ["valve-1"], "time_scope": "incident",
                "record_types": ["inspection"], "source_versions": source_versions,
                "candidate_links": [{"claim_id": "H1", "need_ids": ["N1"],
                    "material_id": "DOC-1", "material_version": "v1", "passage_id": "p1",
                    "exact_text": "A leaking valve can cause hydraulic pressure loss."}]}]}))
        copies = [a for a in produced if a.role == Role.EVIDENCE_WORKER
                  and a.context.get("copied_from_need_id") == "N1"]
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].need_ids, ("N2",))
        self.assertNotEqual(wf.need_packets["N1"].packet_id, wf.need_packets["N2"].packet_id)
        self.assertEqual(wf.need_packets["N2"].parent_packet_id, "P-N1")
        self.assertEqual(wf.lead.work[copies[0].assignment_id].state, JobState.AWAITING_ASSESSOR)
        self.assertEqual(wf.pending_need_reuse, {})

    def test_later_need_reuses_completed_search_with_separate_assessor_review(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        slot = {"slot_id": "s1", "description": "pin inspection record", "entity_id": "valve-1",
                "time_scope": "incident", "record_type": "inspection"}
        created = wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id,
            Role.SPECIALIST, specialist.manifest,
            {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
                "kind": "incident_event", "parent_claim_ids": ["H0"]}],
             "needs": [{"need_id": "N1", "target_ids": ["H1"], "source_scope": ["DOC-1"],
                        "slots": [slot]}]}))
        worker = next(a for a in created if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(worker.assignment_id)
        versions = wf.lead.manifest().source_versions
        link = {"claim_id": "H1", "need_ids": ["N1"], "material_id": "DOC-1", "material_version": "v1",
                "passage_id": "p1", "exact_text": "A leaking valve can cause hydraulic pressure loss."}
        reviewers = wf.submit_worker_result(RoleResult("EW-1", worker.assignment_id, Role.EVIDENCE_WORKER,
            worker.manifest, {"packets": [{"packet_id": "P-N1", "target_ids": ["H1"],
                "covered_slot_ids": ["s1"], "source_scope": ["DOC-1"], "entity_ids": ["valve-1"],
                "time_scope": "incident", "record_types": ["inspection"], "source_versions": versions,
                "candidate_links": [link]}]}))
        evidence_review = next(a for a in reviewers if a.context.get("task_kind") == "evidence_review")
        wf.start_assignment(evidence_review.assignment_id)
        wf.submit_assessor_result(RoleResult("AR-N1", evidence_review.assignment_id, Role.ASSESSOR,
            evidence_review.manifest, {"task_kind": "evidence_review", "assessments": [{
                "claim_id": "H1", "material_id": "DOC-1", "material_version": "v1", "passage_id": "p1",
                "exact_text": link["exact_text"], "effect": "neutral", "rationale": "Generic mechanism only."}]}))
        self.assertEqual(wf.lead.work[worker.assignment_id].state, JobState.COMPLETE)

        wf.lead.add_need(Need("N2", "specialist_gap", "SR-2", ("H1",),
                              (InformationSlot(**slot),), source_scope=("DOC-1",)))
        created_later = wf._queue_available()
        copied = next(a for a in created_later if a.role == Role.EVIDENCE_WORKER and a.need_ids == ("N2",))
        self.assertEqual(copied.context["copied_from_need_id"], "N1")
        self.assertEqual(wf.need_packets["N2"].parent_packet_id, "P-N1")
        self.assertTrue(any(a.role == Role.ASSESSOR and a.need_ids == ("N2",)
                            for a in created_later))

    def test_stale_result_is_archived_and_reissued_at_current_snapshot(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        old_manifest = specialist.manifest
        wf.register_material(event_id="MAT-E2", material=MaterialRecord(
            "DOC-1", "v2", "h2", "Revised hydraulic manual", "manual", content="Updated valve guidance."))
        result = RoleResult("SR-stale", specialist.assignment_id, Role.SPECIALIST, old_manifest,
                            {"claims": []})
        fresh = wf.submit_specialist_result(result)
        self.assertIn("SR-stale", wf.result_archive)
        self.assertTrue(any(a.context.get("reissued_from") == specialist.assignment_id for a in fresh))
        self.assertTrue(all(a.manifest == wf.lead.manifest() for a in fresh))
        self.assertEqual(wf.lead.work[specialist.assignment_id].state, JobState.STALE)

    def test_unrequested_material_with_incomplete_provenance_triggers_bounded_recheck(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        assignments = wf.register_material(event_id="MAT-UNREQUESTED", material=MaterialRecord(
            "DOC-UNREQUESTED", "v1", "h-unrequested", "Unrequested maintenance note",
            provenance_complete=False, content="Valve seal replaced."))
        self.assertTrue(any("N1" in a.need_ids for a in assignments))
        self.assertIn("DOC-UNREQUESTED", wf.materials)
        self.assertEqual(wf.lead.material_index_version, f"materials:2:v1")

    def test_late_external_reply_is_registered_after_request_withdrawal(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        request = OutwardRequest("REQ-LATE", ("N1",), ("H1",), ("s1",), "Send valve report",
                                 "document_request", state=RequestDisposition.PROPOSED)
        wf.lead.add_request(request)
        wf.lead.apply_request_review("REQ-LATE", "pass")
        send = wf.send_approved_request("REQ-LATE")
        withdraw = wf.lead.submit_dispatch("REQ-LATE", "withdraw")
        wf.lead.acknowledge_dispatch(send.action_id, success=True)
        wf.acknowledge_request_dispatch(withdraw.action_id, success=True)
        self.assertEqual(wf.lead.requests["REQ-LATE"].state, RequestDisposition.WITHDRAWN)
        wf.register_external_response(event_id="LATE-REPLY", request_id="REQ-LATE",
            material=MaterialRecord("LATE-DOC", "v1", "latehash", "Late valve report", content="Valve replaced."))
        self.assertIn("LATE-DOC", wf.materials)
        self.assertEqual(wf.lead.requests["REQ-LATE"].state, RequestDisposition.WITHDRAWN)
        self.assertEqual(wf.lead.requests["REQ-LATE"].response_material_ids, ("LATE-DOC",))

    def test_complete_unrequested_material_is_indexed_without_full_case_fanout(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        assignments = wf.register_material(event_id="MAT-UNREQUESTED", material=MaterialRecord(
            "DOC-UNREQUESTED", "v1", "h-unrequested", "Unrequested maintenance note",
            provenance_complete=True, content="Valve seal replaced."))
        self.assertEqual(assignments, ())
        self.assertIn("DOC-UNREQUESTED", wf.materials)

    def test_branch_inactivation_preserves_history_and_does_not_follow_from_assessment(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}]}))
        self.assertEqual(wf.branches["B1"].state, BranchState.ACTIVE)
        transition = wf.apply_branch_decision("B1", BranchState.INACTIVE, reason="Lead accepted contradictory evidence")
        self.assertEqual(transition.to_state, BranchState.INACTIVE)
        self.assertEqual(len(wf.branch_history), 1)
        self.assertEqual(wf.branches["B1"].claim_ids, ("H1",))

    def test_case_closure_requires_no_open_work_or_requests(self):
        wf, specialist = setup_workflow()
        with self.assertRaisesRegex(CFERPError, "cannot close"):
            wf.close_case(result_ref="draft")
        self.assertNotEqual(wf.current_result()["state"], CaseState.CLOSED.value)


if __name__ == "__main__":
    unittest.main()

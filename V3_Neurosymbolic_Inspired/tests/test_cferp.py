"""Standard-library behavioral checks for the CFERP core."""
from dataclasses import replace
import unittest

from cferp.contracts import (
    CandidateAction, EvidencePacket, InformationSlot, JobState, Need,
    NeedState, OutwardRequest, RequestDisposition, Role, SlotState, WorkItem,
)
from cferp.engine import CFERPError, CFERPLead
from cferp.planner import PlannerResponse


def request(request_id="A", *, slot_ids=("pin_at_1029",), wording="Find pin record"):
    return OutwardRequest(
        request_id=request_id, origin_ids=(f"origin-{request_id}",),
        target_ids=("H-pin",), slot_ids=slot_ids, wording=wording,
        request_kind="document_request", state=RequestDisposition.APPROVED,
        source_scope=("all-maintenance-records",), entity_ids=("L2",),
        time_scope="2026-03-14 10:29", record_types=("job_card",),
        source_versions=(("D2", "v1", "hash2"),), material_index_version="idx:7",
    )


def packet(packet_id="P-A", request_id="A", *, slots=("pin_at_1029",)):
    return EvidencePacket(
        packet_id=packet_id, request_id=request_id, target_ids=("H-pin",),
        covered_slot_ids=slots, source_scope=("all-maintenance-records",),
        entity_ids=("L2",), time_scope="2026-03-14 10:29",
        record_types=("job_card",), source_versions=(("D2", "v1", "hash2"),),
        searched_material_index_version="idx:7", result_payload={"candidate": "p.4"},
    )


class CFERPTests(unittest.TestCase):
    def test_a_and_a_prime_keep_identity_while_compatible_packet_is_copied(self):
        lead = CFERPLead("C-01")
        lead.add_request(request("A"))
        lead.add_request(request("A-prime", wording="Was the pin seated at 10:29?"))
        lead.register_packet(packet())
        copied = lead.clone_packet_for_request("P-A", "A-prime", new_packet_id="P-A-prime")
        self.assertEqual(copied.request_id, "A-prime")
        self.assertEqual(copied.parent_packet_id, "P-A")
        self.assertEqual(lead.requests["A"].wording, "Find pin record")
        self.assertEqual(lead.requests["A-prime"].wording, "Was the pin seated at 10:29?")
        self.assertNotEqual(lead.requests["A"].request_id, lead.requests["A-prime"].request_id)

    def test_packet_reuse_requires_exact_scope(self):
        changes = [
            {"slot_ids": ("pin_between_1029_1030",)}, {"entity_ids": ("L3",)},
            {"time_scope": "2026-03-14 10:30"}, {"record_types": ("telemetry",)},
            {"source_versions": (("D2", "v2", "hash-new"),)},
            {"material_index_version": "idx:8"}, {"source_scope": ("operator-interview",)},
        ]
        for changed in changes:
            with self.subTest(changed=changed):
                lead = CFERPLead("C-01")
                lead.add_request(request("A"))
                lead.add_request(replace(request("A-prime"), **changed))
                lead.register_packet(packet())
                with self.assertRaisesRegex(CFERPError, "incompatible"):
                    lead.clone_packet_for_request("P-A", "A-prime", new_packet_id="P-copy")

    def test_packet_registration_rejects_wrong_target_or_slots(self):
        lead = CFERPLead("C-01")
        lead.add_request(request("A"))
        with self.assertRaisesRegex(CFERPError, "target_ids"):
            lead.register_packet(replace(packet(), target_ids=("H-other",)))
        with self.assertRaisesRegex(CFERPError, "covered slots"):
            lead.register_packet(replace(packet(), covered_slot_ids=("unrelated",)))

    def test_partial_packet_reuse_copies_only_explicit_slot_results(self):
        lead = CFERPLead("C-01")
        lead.add_request(request("A"))
        lead.add_request(request("A-prime", slot_ids=("pin_at_1029", "pin_between_1029_1030")))
        source = replace(packet(), slot_payloads=(("pin_at_1029", {"passage": "p.4"}),))
        lead.register_packet(source)
        copied = lead.clone_packet_for_request("P-A", "A-prime", new_packet_id="P-partial")
        self.assertEqual(copied.covered_slot_ids, ("pin_at_1029",))
        self.assertTrue(copied.is_partial_reuse)
        self.assertEqual(copied.result_payload["uncovered_slot_ids"], ("pin_between_1029_1030",))
        copied.result_payload["reused_slot_payloads"]["pin_at_1029"]["passage"] = "mutated"
        self.assertEqual(lead.packets["P-partial"].result_payload["reused_slot_payloads"]["pin_at_1029"]["passage"], "p.4")

    def test_packet_clone_payloads_are_independent_and_terminal_target_is_rejected(self):
        lead = CFERPLead("C-01")
        lead.add_request(request("A"))
        lead.add_request(request("A-prime"))
        source = replace(packet(), result_payload={"findings": ["record"]})
        lead.register_packet(source)
        copied = lead.clone_packet_for_request("P-A", "A-prime", new_packet_id="P-copy")
        copied.result_payload["findings"].append("mutated")
        self.assertEqual(lead.packets["P-A"].result_payload["findings"], ["record"])
        self.assertNotIn("mutated", lead.packets["P-copy"].result_payload["findings"])
        terminal_lead = CFERPLead("C-terminal")
        terminal_lead.add_request(request("A"))
        terminal_lead.add_request(replace(request("A-prime"), state=RequestDisposition.ANSWERED))
        terminal_lead.register_packet(packet())
        with self.assertRaisesRegex(CFERPError, "terminal request"):
            terminal_lead.clone_packet_for_request("P-A", "A-prime", new_packet_id="P-copy-2")

    def test_packet_registration_rejects_terminal_request(self):
        lead = CFERPLead("C-01")
        lead.add_request(replace(request("A"), state=RequestDisposition.ANSWERED))
        with self.assertRaisesRegex(CFERPError, "terminal request"):
            lead.register_packet(packet())

    def test_partial_request_must_use_child_request_for_remaining_slots(self):
        lead = CFERPLead("C-01")
        lead.add_request(request("A"))
        lead.add_request(replace(request("A-prime"), state=RequestDisposition.PARTIALLY_ANSWERED))
        lead.register_packet(packet())
        with self.assertRaisesRegex(CFERPError, "terminal request"):
            lead.clone_packet_for_request("P-A", "A-prime", new_packet_id="P-copy")

    def test_multislot_need_resolves_only_explicit_slots(self):
        lead = CFERPLead("C-01")
        lead.add_need(Need("N1", "specialist_gap", "Q1", ("H1",), (
            InformationSlot("pin", "pin state"), InformationSlot("verification", "verification record"),
        )))
        updated = lead.update_need_slots("N1", {"pin": (SlotState.RESOLVED_BY_MATERIAL, ("MAT-9",))})
        self.assertEqual(updated.state, NeedState.PARTIALLY_RESOLVED)
        self.assertEqual(updated.slots[1].state, SlotState.OPEN)
        updated = lead.update_need_slots("N1", {"verification": (SlotState.ANSWERED, ("ANS-2",))})
        self.assertEqual(updated.state, NeedState.RESOLVED)

    def test_duplicate_event_is_noop_but_changed_payload_is_rejected(self):
        lead = CFERPLead("C-01")
        one = lead.ingest_event("EV-1", "material_registered", {"material_id": "D1", "version": "v1"})
        replay = lead.ingest_event("EV-1", "material_registered", {"material_id": "D1", "version": "v1"})
        self.assertEqual(one, replay)
        self.assertEqual(len(lead.events), 1)
        with self.assertRaisesRegex(CFERPError, "different payload"):
            lead.ingest_event("EV-1", "material_registered", {"material_id": "D1", "version": "v2"})

    def test_event_payload_is_detached_from_log(self):
        lead = CFERPLead("C-01")
        payload = {"nested": {"version": "v1"}}
        event = lead.ingest_event("EV-1", "case_packet", payload)
        payload["nested"]["version"] = "mutated"
        event.payload["nested"]["version"] = "also-mutated"
        self.assertEqual(lead.events[0].payload["nested"]["version"], "v1")

    def test_new_material_stales_only_dependents_when_provenance_is_complete(self):
        lead = CFERPLead("C-01")
        for wid, deps in (("W1", ("D1:v1",)), ("W2", ("D2:v1",))):
            lead.register_work(WorkItem(wid, Role.ASSESSOR, "pair-1", ("H1",), (), JobState.RUNNING, 2, 1, dependency_ids=deps))
        self.assertEqual(lead.stale_dependents(("D1:v2",), reason="source revised"), ("W1",))
        self.assertEqual(lead.work["W2"].state, JobState.RUNNING)
        self.assertEqual(lead.stale_dependents(("D3:v1",), reason="index changed", provenance_complete=False), ("W2",))

    def test_material_revision_invalidates_old_version_dependency(self):
        lead = CFERPLead("C-01")
        lead.register_work(WorkItem("W1", Role.ASSESSOR, "pair-1", ("H1",), (), JobState.RUNNING, 2, 1,
                                    dependency_ids=("D1:v1",)))
        event = lead.ingest_event("EV-MAT", "material_revised", {
            "material_id": "D1", "version": "v2", "material_index_version": "idx:2",
        })
        self.assertEqual(event.kind, "material_revised")
        self.assertEqual(lead.last_event_affected_work_ids, ("W1",))
        self.assertEqual(lead.work["W1"].state, JobState.STALE)

    def test_opaque_material_version_ids_invalidate_prior_dependencies(self):
        lead = CFERPLead("C-01")
        lead.register_work(WorkItem("W1", Role.ASSESSOR, "pair-1", ("H1",), (), JobState.RUNNING, 2, 1,
                                    dependency_ids=("D1:rev6",)))
        lead.ingest_event("EV-REV", "material_revised", {"material_id": "D1", "version": "rev7"})
        self.assertEqual(lead.last_event_affected_work_ids, ("W1",))
        self.assertEqual(lead.work["W1"].state, JobState.STALE)

    def test_dispatch_ack_race_requires_confirmed_final_withdrawal(self):
        lead = CFERPLead("C-01")
        lead.add_request(replace(request("A"), state=RequestDisposition.READY_TO_SEND))
        send = lead.submit_dispatch("A", "send")
        withdrawal = lead.submit_dispatch("A", "withdraw")
        self.assertEqual(lead.acknowledge_dispatch(withdrawal.action_id, success=True).state, RequestDisposition.WITHDRAWAL_PENDING)
        self.assertEqual(lead.acknowledge_dispatch(send.action_id, success=True).state, RequestDisposition.WITHDRAWAL_PENDING)
        final_withdrawal = lead.submit_dispatch("A", "withdraw")
        self.assertEqual(final_withdrawal.target_send_sequence, send.sequence)
        self.assertEqual(lead.acknowledge_dispatch(final_withdrawal.action_id, success=True).state, RequestDisposition.WITHDRAWN)
        self.assertEqual(lead.acknowledge_dispatch(send.action_id, success=True).state, RequestDisposition.WITHDRAWN)
        with self.assertRaisesRegex(CFERPError, "conflicting duplicate"):
            lead.acknowledge_dispatch(send.action_id, success=False)

    def test_failed_withdrawal_never_claims_sent_without_send_ack(self):
        lead = CFERPLead("C-01")
        lead.add_request(replace(request("A"), state=RequestDisposition.READY_TO_SEND))
        send = lead.submit_dispatch("A", "send")
        withdrawal = lead.submit_dispatch("A", "withdraw")
        self.assertEqual(lead.acknowledge_dispatch(withdrawal.action_id, success=False).state,
                         RequestDisposition.WITHDRAWAL_PENDING)
        self.assertEqual(lead.acknowledge_dispatch(send.action_id, success=False).state,
                         RequestDisposition.DISPATCH_FAILED)

    def test_successful_send_cannot_be_retried_as_a_duplicate(self):
        lead = CFERPLead("C-01")
        lead.add_request(replace(request("A"), state=RequestDisposition.READY_TO_SEND))
        first = lead.submit_dispatch("A", "send")
        self.assertEqual(lead.acknowledge_dispatch(first.action_id, success=True).state,
                         RequestDisposition.SENT)
        with self.assertRaisesRegex(CFERPError, "not ready to send"):
            lead.submit_dispatch("A", "send")

    def test_duplicate_withdrawal_submission_returns_existing_pending_action(self):
        lead = CFERPLead("C-01")
        lead.add_request(replace(request("A"), state=RequestDisposition.READY_TO_SEND))
        lead.submit_dispatch("A", "send")
        first = lead.submit_dispatch("A", "withdraw")
        second = lead.submit_dispatch("A", "withdraw")
        self.assertEqual(first.action_id, second.action_id)

    def test_failed_child_request_creation_does_not_mutate_parent(self):
        lead = CFERPLead("C-01")
        lead.add_request(request("A", slot_ids=("s1", "s2")))
        with self.assertRaisesRegex(CFERPError, "duplicate request_id"):
            lead.update_request_slots("A", ("s2",), new_request_id="A")
        self.assertEqual(lead.requests["A"].state, RequestDisposition.APPROVED)

    def test_assessor_pass_does_not_send_until_lead_queues_request(self):
        lead = CFERPLead("C-01")
        lead.add_request(replace(request("A"), state=RequestDisposition.PROPOSED))
        with self.assertRaisesRegex(CFERPError, "only an Assessor-approved"):
            lead.queue_approved_request("A")
        self.assertEqual(lead.apply_request_review("A", "pass").state, RequestDisposition.APPROVED)
        self.assertEqual(lead.queue_approved_request("A").state, RequestDisposition.READY_TO_SEND)
        action = lead.submit_dispatch("A", "send")
        self.assertEqual(lead.acknowledge_dispatch(action.action_id, success=True).state, RequestDisposition.SENT)

    def test_declined_information_does_not_resolve_need(self):
        lead = CFERPLead("C-01")
        lead.add_need(Need("N1", "specialist_gap", "Q1", ("H1",), (
            InformationSlot("pin", "pin state"),
        )))
        updated = lead.update_need_slots("N1", {"pin": (SlotState.DECLINED, ("ANS-3",))})
        self.assertEqual(updated.state, NeedState.OPEN)

    def test_terminal_slot_cannot_be_reopened_without_explicit_reopen(self):
        lead = CFERPLead("C-01")
        lead.add_need(Need("N1", "specialist_gap", "Q1", ("H1",), (
            InformationSlot("pin", "pin state"),
        )))
        lead.update_need_slots("N1", {"pin": (SlotState.ANSWERED, ("ANS-1",))})
        with self.assertRaisesRegex(CFERPError, "terminal"):
            lead.update_need_slots("N1", {"pin": (SlotState.OPEN, ())})
        reopened = lead.reopen_need_slots("N1", ("pin",), reason="new relevant material arrived")
        self.assertEqual(reopened.slots[0].state, SlotState.OPEN)
        answered = lead.update_need_slots("N1", {"pin": (SlotState.ANSWERED, ("ANS-2",))})
        self.assertEqual(answered.state, NeedState.RESOLVED)

    def test_scheduler_enforces_three_specialists_and_two_workers(self):
        lead = CFERPLead("C-01")
        actions = [CandidateAction(f"S{i}", Role.SPECIALIST, (f"H{i}",), priority_tier=1) for i in range(5)]
        actions += [CandidateAction(f"E{i}", Role.EVIDENCE_WORKER, (f"N{i}",), priority_tier=2) for i in range(3)]
        selected = lead.schedule(actions)
        self.assertEqual(sum(item.role == Role.SPECIALIST for item in selected), 3)
        self.assertEqual(sum(item.role == Role.EVIDENCE_WORKER for item in selected), 2)
        self.assertEqual(len(selected), 5)
        self.assertEqual(lead.schedule(actions), ())

    def test_scheduler_releases_slot_and_fills_next_queued_action(self):
        lead = CFERPLead("C-01", concurrency={Role.SPECIALIST: 1, Role.EVIDENCE_WORKER: 0, Role.ASSESSOR: 0})
        actions = [CandidateAction("S1", Role.SPECIALIST, ("H1",), created_sequence=1),
                   CandidateAction("S2", Role.SPECIALIST, ("H2",), created_sequence=2)]
        self.assertEqual(tuple(a.action_id for a in lead.schedule(actions)), ("S1",))
        lead.release_reservation("S1")
        self.assertEqual(tuple(a.action_id for a in lead.schedule(actions)), ("S1",))

    def test_worker_holds_capacity_through_assessor_and_external_wait(self):
        lead = CFERPLead("C-hold", concurrency={Role.EVIDENCE_WORKER: 1}, global_concurrency=1)
        lead.register_work(WorkItem("EW-1", Role.EVIDENCE_WORKER, "pair-1", ("H1",), ("N1",),
                                    JobState.AWAITING_ASSESSOR, 2, 1))
        candidate = CandidateAction("EW-2", Role.EVIDENCE_WORKER, ("H2",), ("N2",),
                                    priority_tier=1, created_sequence=2)
        self.assertEqual(lead.schedule((candidate,)), ())
        lead.transition_work("EW-1", JobState.WAITING_EXTERNAL)
        self.assertEqual(lead.schedule((candidate,)), ())

    def test_scheduler_deduplicates_identical_action_ids_and_rejects_conflicts(self):
        lead = CFERPLead("C-01", concurrency={Role.SPECIALIST: 2, Role.EVIDENCE_WORKER: 0, Role.ASSESSOR: 0})
        action = CandidateAction("S1", Role.SPECIALIST, ("H1",))
        self.assertEqual(len(lead.schedule((action, action))), 1)
        other = CandidateAction("S1", Role.SPECIALIST, ("H2",))
        with self.assertRaisesRegex(CFERPError, "conflicting CandidateAction"):
            CFERPLead("C-02").schedule((action, other))

    def test_reserved_action_rejects_changed_payload_and_work_scope(self):
        lead = CFERPLead("C-01")
        action = CandidateAction("X", Role.SPECIALIST, ("H1",), ("N1",), dependency_ids=("D1:v1",))
        lead.schedule((action,))
        with self.assertRaisesRegex(CFERPError, "ID reused with changed payload"):
            lead.schedule((replace(action, target_ids=("H2",)),))
        wrong_work = WorkItem("X", Role.SPECIALIST, "s1", ("H2",), ("N2",), JobState.QUEUED, 1, 1,
                              dependency_ids=("D2:v1",))
        with self.assertRaisesRegex(CFERPError, "scope/dependencies"):
            lead.register_scheduled_work("X", wrong_work)

    def test_source_bearing_manifest_uses_intake_current_snapshot(self):
        lead = CFERPLead("C-01")
        lead.ingest_event("EV-SOURCE", "material_registered", {
            "material_id": "D1", "version": "rev7", "content_hash": "abc",
            "material_index_version": "idx:7",
        })
        current = lead.manifest()
        action = CandidateAction("S1", Role.SPECIALIST, ("H1",), manifest=current)
        self.assertEqual(tuple(a.action_id for a in lead.schedule((action,))), ("S1",))

    def test_planner_snapshot_change_drops_old_candidates(self):
        lead = CFERPLead("C-01")
        actions = [CandidateAction("A1", Role.SPECIALIST, ("H1",)),
                   CandidateAction("A2", Role.SPECIALIST, ("H2",))]

        class MutatingPlanner:
            def rank_actions(self, request):
                lead.ingest_event("EV-BOARD", "board_changed", {"changed_dependency_ids": ("H1",)})
                return PlannerResponse(tuple(a.action_id for a in request.actions),
                                       request.manifest.case_snapshot_id,
                                       request.manifest.board_version,
                                       request.manifest.material_index_version)

        self.assertEqual(lead.schedule(actions, planner=MutatingPlanner(), ambiguous=True), ())
        self.assertEqual(lead.last_planner_diagnostics, ("case_changed_during_planner_call",))

    def test_material_change_releases_reservations_but_does_not_free_live_call_slot(self):
        lead = CFERPLead("C-01", concurrency={Role.SPECIALIST: 1, Role.EVIDENCE_WORKER: 0, Role.ASSESSOR: 0})
        action_a = CandidateAction("A", Role.SPECIALIST, ("H1",), dependency_ids=("D1:v1",))
        lead.ingest_event("EV-0", "material_registered", {"material_id": "D1", "version": "v1"})
        lead.schedule((action_a,))
        lead.ingest_event("EV-1", "material_revised", {"material_id": "D1", "version": "v2"})
        self.assertEqual(lead.last_invalidated_action_ids, ("A",))
        self.assertEqual(lead.schedule((action_a,)), ())
        action_a2 = CandidateAction("A2", Role.SPECIALIST, ("H1",), dependency_ids=("D1:v2",))
        action_b = CandidateAction("B", Role.SPECIALIST, ("H2",), dependency_ids=("D2:v1",))
        lead.schedule((action_a2,))
        lead.register_scheduled_work("A2", WorkItem("A2", Role.SPECIALIST, "s1", ("H1",), (),
                                                     JobState.QUEUED, 1, 1, dependency_ids=("D1:v2",)))
        lead.start_work("A2")
        lead.ingest_event("EV-2", "material_revised", {"material_id": "D1", "version": "v3"})
        self.assertEqual(lead.work["A2"].state, JobState.STALE)
        self.assertEqual(lead.schedule((action_b,)), ())
        self.assertEqual(lead.finish_work("A2", state=JobState.COMPLETE).state, JobState.STALE)
        self.assertEqual(tuple(a.action_id for a in lead.schedule((action_b,))), ("B",))

    def test_lead_planner_can_only_reorder_supplied_actions_when_ambiguous(self):
        class SimulatedPlanner:
            def __init__(self, response_builder):
                self.called = 0
                self.response_builder = response_builder
            def rank_actions(self, request):
                self.called += 1
                return self.response_builder(request)

        lead = CFERPLead("C-01", concurrency={Role.SPECIALIST: 1, Role.EVIDENCE_WORKER: 0, Role.ASSESSOR: 0})
        actions = [CandidateAction("A1", Role.SPECIALIST, ("H1",), priority_tier=1, created_sequence=1),
                   CandidateAction("A2", Role.SPECIALIST, ("H2",), priority_tier=1, created_sequence=1)]
        planner = SimulatedPlanner(lambda req: PlannerResponse(
            ("A2", "A1"), req.manifest.case_snapshot_id, req.manifest.board_version,
            req.manifest.material_index_version,
        ))
        selected = lead.schedule(actions, planner=planner, ambiguous=True)
        self.assertEqual(planner.called, 1)
        self.assertTrue(lead.last_planner_accepted)
        self.assertEqual(selected[0].action_id, "A2")

    def test_invalid_planner_ids_fall_back_to_python_order_and_no_call_when_clear(self):
        class SimulatedPlanner:
            def __init__(self, response_builder):
                self.called = 0
                self.response_builder = response_builder
            def rank_actions(self, request):
                self.called += 1
                return self.response_builder(request)

        lead = CFERPLead("C-01", concurrency={Role.SPECIALIST: 1, Role.EVIDENCE_WORKER: 0, Role.ASSESSOR: 0})
        actions = [CandidateAction("A1", Role.SPECIALIST, ("H1",), created_sequence=1),
                   CandidateAction("A2", Role.SPECIALIST, ("H2",), created_sequence=1)]
        planner = SimulatedPlanner(lambda req: PlannerResponse(
            ("invented-action", "A1"), req.manifest.case_snapshot_id,
            req.manifest.board_version, req.manifest.material_index_version,
        ))
        selected = lead.schedule(actions, planner=planner, ambiguous=True)
        self.assertEqual(selected[0].action_id, "A1")
        self.assertFalse(lead.last_planner_accepted)
        self.assertIn("exact_candidate_id_permutation", lead.last_planner_diagnostics[0])
        lead2 = CFERPLead("C-02", concurrency={Role.SPECIALIST: 1, Role.EVIDENCE_WORKER: 0, Role.ASSESSOR: 0})
        lead2.schedule(actions, planner=planner, ambiguous=False)
        self.assertEqual(planner.called, 1)

    def test_planner_malformed_and_failed_responses_fall_back_safely(self):
        actions = [CandidateAction("A1", Role.SPECIALIST, ("H1",), created_sequence=1),
                   CandidateAction("A2", Role.SPECIALIST, ("H2",), created_sequence=1)]

        class SimulatedPlanner:
            def __init__(self, outcome):
                self.outcome = outcome
            def rank_actions(self, request):
                if isinstance(self.outcome, Exception):
                    raise self.outcome
                return self.outcome

        for malformed in (None, {"ordered_action_ids": ["A2", "A1"]}):
            lead = CFERPLead("C-malformed", concurrency={Role.SPECIALIST: 1})
            selected = lead.schedule(actions, planner=SimulatedPlanner(malformed), ambiguous=True)
            self.assertEqual(selected[0].action_id, "A1")
            self.assertFalse(lead.last_planner_accepted)
            self.assertIn("planner_malformed_response", lead.last_planner_diagnostics)

        lead = CFERPLead("C-malformed-ids", concurrency={Role.SPECIALIST: 1})
        malformed_ids = type("BadIDs", (), {"rank_actions": lambda self, req: PlannerResponse(
            ("A2", 7), req.manifest.case_snapshot_id, req.manifest.board_version,
            req.manifest.material_index_version)})()
        selected = lead.schedule(actions, planner=malformed_ids, ambiguous=True)
        self.assertEqual(selected[0].action_id, "A1")
        self.assertIn("planner_malformed_response", lead.last_planner_diagnostics)

        lead = CFERPLead("C-timeout", concurrency={Role.SPECIALIST: 1})
        selected = lead.schedule(actions, planner=SimulatedPlanner(TimeoutError()), ambiguous=True)
        self.assertEqual(selected[0].action_id, "A1")
        self.assertIn("planner_failed:TimeoutError", lead.last_planner_diagnostics)

    def test_planner_model_order_does_not_override_fifo_age(self):
        lead = CFERPLead("C-age", concurrency={Role.SPECIALIST: 1})
        actions = [CandidateAction("OLDER", Role.SPECIALIST, ("H1",), priority_tier=1, created_sequence=1),
                   CandidateAction("NEWER", Role.SPECIALIST, ("H2",), priority_tier=1, created_sequence=2)]
        planner = type("Planner", (), {"rank_actions": lambda self, req: PlannerResponse(
            ("NEWER", "OLDER"), req.manifest.case_snapshot_id, req.manifest.board_version,
            req.manifest.material_index_version)})()
        selected = lead.schedule(actions, planner=planner, ambiguous=True)
        self.assertEqual(selected[0].action_id, "OLDER")
        self.assertTrue(lead.last_planner_accepted)


if __name__ == "__main__":
    unittest.main()

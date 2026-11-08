"""An empty search settles without repeating; a new document does not re-queue unchanged
claim-passage assessments, but is searched for every open need; a revision still invalidates."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from cferp import RoleResult
from cferp.contracts import JobState, Role
from cferp.integration import IntegrationError, ew_result_to_cferp
from cferp.workflow import MaterialRecord
from tests.test_cferp_workflow import setup_workflow


def with_claim_and_search():
    wf, specialist = setup_workflow()
    wf.start_assignment(specialist.assignment_id)
    wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
        specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
        "kind": "incident_event", "parent_claim_ids": ["H0"]}],
        "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
    ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
    wf.start_assignment(ew.assignment_id)
    return wf, ew


def ew_output(ew, status="no_candidate_in_scope"):
    return SimpleNamespace(assignment_id=ew.assignment_id, work_item_id=ew.assignment_id,
        case_snapshot_id=ew.manifest.case_snapshot_id, board_version=ew.manifest.board_version,
        status=status, slot_results=(SimpleNamespace(need_id="N1", slot_id="s1", candidate_links=()),),
        preserved_candidate_links=(), request_drafts=())


def queued_searches(wf):
    return [a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER
            and wf.lead.work[a.assignment_id].state == JobState.QUEUED]


def new_doc(material_id="DOC-NEW", version="v1", content="Unrelated canteen menu for the week."):
    return MaterialRecord(material_id, version, f"hash-{material_id}-{version}", "Late upload", "log",
                          provenance_complete=False, content=content)


class EmptySearch(unittest.TestCase):
    def test_an_empty_search_settles_the_pass(self):
        wf, ew = with_claim_and_search()
        packet = ew_result_to_cferp(ew_output(ew), ew)
        self.assertEqual(packet.payload, {"packets": [], "requests": []})
        wf.submit_worker_result(packet)
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.RETURNED)

    def test_the_same_need_is_not_searched_again_over_the_same_corpus(self):
        wf, ew = with_claim_and_search()
        created = wf.submit_worker_result(ew_result_to_cferp(ew_output(ew), ew))
        self.assertEqual(created, ())
        self.assertEqual(queued_searches(wf), [])

    def test_new_material_lets_the_waiting_need_be_searched_again(self):
        wf, ew = with_claim_and_search()
        wf.submit_worker_result(ew_result_to_cferp(ew_output(ew), ew))
        wf.register_material(event_id="MAT-NEW", material=new_doc())
        self.assertTrue(any(a.context.get("new_material_id") == "DOC-NEW" for a in queued_searches(wf)))

    def test_other_failure_statuses_still_raise(self):
        _wf, ew = with_claim_and_search()
        with self.assertRaises(IntegrationError):
            ew_result_to_cferp(ew_output(ew, status="generation_failed"), ew)


def with_queued_assessment():
    wf, ew = with_claim_and_search()
    assessor, = wf.submit_worker_result(RoleResult("EW-1", ew.assignment_id, Role.EVIDENCE_WORKER,
        ew.manifest, {"packets": [{"packet_id": "P1", "covered_slot_ids": ["s1"], "candidate_links": [{
            "claim_id": "H1", "material_id": "DOC-1", "material_version": "v1", "passage_id": "p1",
            "start_offset": 0, "end_offset": 51,
            "exact_text": "A leaking valve can cause hydraulic pressure loss."}]}]}))
    return wf, assessor


class BridgeEmptySearch(unittest.TestCase):
    def test_the_bridge_settles_an_empty_search_instead_of_failing(self):
        from orchestration.v3_bridge import V3PackageBridge
        wf, ew = with_claim_and_search()
        engine = SimpleNamespace(run=lambda typed: ew_output(ew))
        bridge = V3PackageBridge(wf, specialist_engine=None, evidence_worker_engine=engine,
                                 assessor_engine=None, max_job_failures=0)
        bridge.execute(ew.assignment_id)
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.RETURNED)
        self.assertEqual(bridge.job_failures, [])


class NewMaterial(unittest.TestCase):
    def test_a_new_document_does_not_requeue_an_unchanged_assessment(self):
        wf, assessor = with_queued_assessment()
        wf.register_material(event_id="MAT-NEW", material=new_doc())
        self.assertEqual(wf.lead.work[assessor.assignment_id].state, JobState.QUEUED)
        self.assertFalse(any(a.context.get("reissued_from") == assessor.assignment_id
                             for a in wf.assignments.values()))

    def test_a_new_document_is_still_searched_for_open_needs(self):
        wf, _assessor = with_queued_assessment()
        created = wf.register_material(event_id="MAT-NEW", material=new_doc())
        self.assertTrue(any(a.role == Role.EVIDENCE_WORKER and a.context.get("new_material_id") == "DOC-NEW"
                            for a in created))

    def test_a_revision_of_the_assessed_material_still_invalidates_it(self):
        wf, assessor = with_queued_assessment()
        wf.register_material(event_id="MAT-REV", material=MaterialRecord(
            "DOC-1", "v2", "hash-1-v2", "Hydraulic manual", "manual", provenance_complete=False,
            content="Revised: the valve was replaced."))
        self.assertEqual(wf.lead.work[assessor.assignment_id].state, JobState.STALE)

    def test_a_revision_without_provenance_still_invalidates_unrelated_work(self):
        wf, assessor = with_queued_assessment()
        wf.register_material(event_id="MAT-X", material=new_doc("DOC-X"))
        wf.register_material(event_id="MAT-X2", material=new_doc("DOC-X", "v2", "Revised canteen menu."))
        self.assertEqual(wf.lead.work[assessor.assignment_id].state, JobState.STALE)


if __name__ == "__main__":
    unittest.main()


def second_search_for(wf, claim_id="H1", need_id="N2", slot_id="t1"):
    """Another need on the same claim, searched separately."""
    wf.lead.add_need(__import__("cferp.contracts", fromlist=["Need"]).Need(
        need_id, "specialist_gap", "SR-2", (claim_id,),
        (__import__("cferp.contracts", fromlist=["InformationSlot"]).InformationSlot(slot_id, "valve state"),)))
    wf._queue_available()
    ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER and need_id in a.need_ids)
    wf.start_assignment(ew.assignment_id)
    return ew


def links_packet(ew, *links, slot_id="t1"):
    return RoleResult(f"EW-{ew.assignment_id}", ew.assignment_id, Role.EVIDENCE_WORKER, ew.manifest,
                      {"packets": [{"packet_id": f"P-{ew.assignment_id}", "covered_slot_ids": [slot_id],
                                    "candidate_links": [dict(l) for l in links]}]})


SAME = {"claim_id": "H1", "material_id": "DOC-1", "material_version": "v1", "passage_id": "other-run-id",
        "start_offset": 0, "end_offset": 51, "exact_text": "A leaking valve can cause hydraulic pressure loss."}


class DuplicatePairs(unittest.TestCase):
    def test_the_same_claim_and_passage_from_another_search_gets_no_new_job(self):
        wf, first = with_queued_assessment()
        created = wf.submit_worker_result(links_packet(second_search_for(wf), SAME))
        self.assertFalse([a for a in created if a.role == Role.ASSESSOR])
        event = [e for e in wf.lead.events if e.kind == "worker_result_received"][-1]
        self.assertEqual(event.payload["already_assessed_passage_ids"], ("other-run-id",))

    def test_a_different_passage_is_still_assessed(self):
        wf, _first = with_queued_assessment()
        other = {**SAME, "end_offset": 19, "exact_text": "A leaking valve can"}
        created = wf.submit_worker_result(links_packet(second_search_for(wf), other))
        self.assertEqual(len([a for a in created if a.role == Role.ASSESSOR]), 1)

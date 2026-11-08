"""Concurrency-aware scheduling and bounded revisit work in the Lead workflow."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from cferp import RoleResult
from cferp.contracts import JobState, Role
from cferp.engine import CFERPError
from cferp.integration import ew_assignment_from_cferp
from cferp.workflow import REVISIT_PURPOSE
from orchestration.v3_bridge import V3PackageBridge
from tests.test_cferp_workflow import setup_workflow

TEXT = "A leaking valve can cause hydraulic pressure loss."


def _evidence_round(wf, specialist, *, need_id, slot_id, passage_id, start, end, result_id):
    """One real Specialist -> Worker -> Assessor pass that annotates claim H1."""
    wf.start_assignment(specialist.assignment_id)
    claims = [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
               "kind": "incident_event", "parent_claim_ids": ["H0"]}] if "H1" not in wf.claims else []
    wf.submit_specialist_result(RoleResult(f"SR-{result_id}", specialist.assignment_id, Role.SPECIALIST,
        specialist.manifest, {"claims": claims, "needs": [{"need_id": need_id, "target_ids": ["H1"],
            "slots": [{"slot_id": slot_id, "description": "leak"}]}]}))
    ew = next(a for a in wf.assignments.values()
              if a.role == Role.EVIDENCE_WORKER and need_id in a.need_ids
              and wf.lead.work[a.assignment_id].state == JobState.QUEUED)
    wf.start_assignment(ew.assignment_id)
    assessor, = wf.submit_worker_result(RoleResult(f"EW-{result_id}", ew.assignment_id,
        Role.EVIDENCE_WORKER, ew.manifest, {"packets": [{"packet_id": f"P-{result_id}",
            "covered_slot_ids": [slot_id], "candidate_links": [{"claim_id": "H1", "material_id": "DOC-1",
                "material_version": "v1", "passage_id": passage_id, "start_offset": start,
                "end_offset": end, "exact_text": TEXT[start:end]}]}]}))
    wf.start_assignment(assessor.assignment_id)
    wf.submit_assessor_result(RoleResult(f"AR-{result_id}", assessor.assignment_id, Role.ASSESSOR,
        assessor.manifest, {"task_kind": "evidence_review", "assessments": [{
            "claim_id": "H1", "material_id": "DOC-1", "material_version": "v1",
            "passage_id": passage_id, "exact_text": TEXT[start:end], "effect": "neutral",
            "rationale": "No relevant source statement was extracted."}]}))


def _revisits(wf):
    return [(a, wf.lead.work[a.assignment_id].state) for a in wf.assignments.values()
            if a.role == Role.SPECIALIST and a.purpose == REVISIT_PURPOSE]


class PriorPacketTests(unittest.TestCase):
    def test_second_worker_pass_on_a_need_carries_its_prior_candidate_links(self):
        wf, specialist = setup_workflow()
        _evidence_round(wf, specialist, need_id="N1", slot_id="s1", passage_id="p1",
                        start=0, end=51, result_id="1")
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)

        typed = ew_assignment_from_cferp(ew, wf)

        link, = typed.prior_candidate_links
        self.assertEqual((link.need_id, link.source_id, link.exact_text), ("N1", "DOC-1", TEXT))


class CanStartTests(unittest.TestCase):
    def test_can_start_reports_a_full_role_slot_without_raising(self):
        wf, first = setup_workflow()
        second = next(a for a in wf.assignments.values() if a.role == Role.SPECIALIST
                      and a.assignment_id != first.assignment_id
                      and wf.lead.work[a.assignment_id].state == JobState.QUEUED)
        wf.lead.concurrency[Role.SPECIALIST] = 1

        self.assertTrue(wf.lead.can_start(first.assignment_id))
        wf.start_assignment(first.assignment_id)
        self.assertFalse(wf.lead.can_start(second.assignment_id))
        self.assertFalse(wf.lead.can_start(first.assignment_id))  # already running
        with self.assertRaisesRegex(CFERPError, "concurrency limit reached"):
            wf.start_assignment(second.assignment_id)


class RunReadySkipsBlockedWorkTests(unittest.TestCase):
    def test_a_blocked_head_of_queue_does_not_stop_runnable_work_behind_it(self):
        def item(work_id, tier, seq):
            return SimpleNamespace(work_id=work_id, role=Role.EVIDENCE_WORKER, state=JobState.QUEUED,
                                   priority_tier=tier, created_sequence=seq)
        work = {"blocked": item("blocked", 1, 1), "runnable": item("runnable", 2, 2)}
        workflow = SimpleNamespace(
            assignments=dict.fromkeys(work, object()),
            lead=SimpleNamespace(work=work, can_start=lambda wid: wid != "blocked"))
        bridge = V3PackageBridge(workflow, specialist_engine=None, evidence_worker_engine=None,
                                 assessor_engine=None)
        ran = []
        bridge.execute = lambda wid: (ran.append(wid), setattr(work[wid], "state", JobState.RETURNED),
                                      bridge.completed.append((wid, "evidence_worker")))

        done = bridge.run_ready(max_jobs=10)

        self.assertEqual(ran, ["runnable"])
        self.assertEqual(done, (("runnable", "evidence_worker"),))
        self.assertEqual(work["blocked"].state, JobState.QUEUED)


class RevisitCoalescingTests(unittest.TestCase):
    def test_a_newer_revisit_supersedes_the_older_one_instead_of_accumulating(self):
        wf, first = setup_workflow()
        other = next(a for a in wf.assignments.values() if a.role == Role.SPECIALIST
                     and a.assignment_id != first.assignment_id
                     and wf.lead.work[a.assignment_id].state == JobState.QUEUED)

        _evidence_round(wf, first, need_id="N1", slot_id="s1", passage_id="p1",
                        start=0, end=51, result_id="1")
        (older, older_state), = _revisits(wf)
        self.assertEqual(older_state, JobState.QUEUED)

        _evidence_round(wf, other, need_id="N2", slot_id="s2", passage_id="p2",
                        start=0, end=20, result_id="2")

        states = {a.assignment_id: state for a, state in _revisits(wf)}
        self.assertEqual(states[older.assignment_id], JobState.SUPERSEDED)
        self.assertEqual(sum(s in {JobState.QUEUED, JobState.STALE} for s in states.values()), 1)
        self.assertFalse(any(a.context.get("reissued_from") == older.assignment_id
                             for a in wf.assignments.values()))
        newest = next(a for a, s in _revisits(wf) if s == JobState.QUEUED)
        self.assertEqual(len(newest.context["assessor_annotations"]), 2)

    def test_a_running_revisit_is_left_alone(self):
        wf, first = setup_workflow()
        other = next(a for a in wf.assignments.values() if a.role == Role.SPECIALIST
                     and a.assignment_id != first.assignment_id
                     and wf.lead.work[a.assignment_id].state == JobState.QUEUED)
        _evidence_round(wf, first, need_id="N1", slot_id="s1", passage_id="p1",
                        start=0, end=51, result_id="1")
        (running, _), = _revisits(wf)
        wf.start_assignment(running.assignment_id)

        _evidence_round(wf, other, need_id="N2", slot_id="s2", passage_id="p2",
                        start=0, end=20, result_id="2")

        self.assertNotEqual(wf.lead.work[running.assignment_id].state, JobState.SUPERSEDED)


if __name__ == "__main__":
    unittest.main()

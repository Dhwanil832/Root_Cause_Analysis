"""A role engine's own rejection ends one job as FAILED; the run, the board and the status stay honest."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cferp import RoleResult
from cferp.contracts import JobState, Role
from cferp.engine import CFERPError
from orchestration.v3_bridge import V3BridgeError, V3PackageBridge
from tests.test_cferp_workflow import setup_workflow

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FailAssignmentTests(unittest.TestCase):
    def test_a_failed_job_commits_nothing_logs_why_and_frees_its_slot(self):
        wf, first = setup_workflow()
        second = next(a for a in wf.assignments.values() if a.role == Role.SPECIALIST
                      and a.assignment_id != first.assignment_id
                      and wf.lead.work[a.assignment_id].state == JobState.QUEUED)
        wf.lead.concurrency[Role.SPECIALIST] = 1
        wf.start_assignment(first.assignment_id)
        self.assertFalse(wf.lead.can_start(second.assignment_id))
        claims_before, version_before = dict(wf.claims), wf.lead.board_version

        wf.fail_assignment(first.assignment_id, "SAHS rejected: invalid_proposal")

        self.assertEqual(wf.lead.work[first.assignment_id].state, JobState.FAILED)
        self.assertTrue(wf.lead.can_start(second.assignment_id))
        self.assertEqual((dict(wf.claims), wf.lead.board_version), (claims_before, version_before))
        event = next(e for e in wf.lead.events if e.kind == "assignment_failed")
        self.assertEqual(event.payload["reason"], "SAHS rejected: invalid_proposal")

    def test_failing_the_last_assessor_job_still_settles_the_worker_pass(self):
        wf, specialist = setup_workflow()
        wf.start_assignment(specialist.assignment_id)
        wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
            specialist.manifest, {"claims": [{"claim_id": "H1", "text": "A valve leaked", "branch_id": "B1",
            "kind": "incident_event", "parent_claim_ids": ["H0"]}],
            "needs": [{"need_id": "N1", "target_ids": ["H1"], "slots": [{"slot_id": "s1", "description": "leak"}]}]}))
        ew = next(a for a in wf.assignments.values() if a.role == Role.EVIDENCE_WORKER)
        wf.start_assignment(ew.assignment_id)
        assessor, = wf.submit_worker_result(RoleResult("EW-1", ew.assignment_id, Role.EVIDENCE_WORKER,
            ew.manifest, {"packets": [{"packet_id": "P1", "covered_slot_ids": ["s1"], "candidate_links": [{
                "claim_id": "H1", "material_id": "DOC-1", "material_version": "v1", "passage_id": "p1",
                "start_offset": 0, "end_offset": 51,
                "exact_text": "A leaking valve can cause hydraulic pressure loss."}]}]}))
        wf.start_assignment(assessor.assignment_id)
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.AWAITING_ASSESSOR)

        wf.fail_assignment(assessor.assignment_id, "HERA returned assessment_failed")

        self.assertEqual(wf.lead.work[assessor.assignment_id].state, JobState.FAILED)
        self.assertEqual(wf.lead.work[ew.assignment_id].state, JobState.COMPLETE)  # not held forever
        self.assertEqual(len(wf.assessments), 0)  # the passage stays unassessed


class FakeWorkflow:
    def __init__(self):
        self.failed, self.submitted = [], []
        self.assignments, self.lead = {}, SimpleNamespace(work={})

    def add(self, role, assignment_id):
        self.assignments[assignment_id] = SimpleNamespace(
            assignment_id=assignment_id, role=role, target_ids=("H1",), context={"task_kind": "evidence_review"})
        self.lead.work[assignment_id] = SimpleNamespace(state=JobState.RUNNING)

    def fail_assignment(self, assignment_id, reason):
        self.failed.append((assignment_id, reason))

    def submit_assessor_result(self, packet):
        self.submitted.append(packet)
        raise CFERPError("candidate membership references unknown causal rules")

    submit_specialist_result = submit_worker_result = submit_assessor_result


def make_bridge(workflow, role, output, *, max_job_failures):
    engine = SimpleNamespace(run=lambda task: output, versions=None)
    return V3PackageBridge(workflow, specialist_engine=engine, evidence_worker_engine=engine,
                           assessor_engine=engine, max_job_failures=max_job_failures)


PATCH_TASKS = (
    patch("orchestration.v3_bridge.sahs_assignment_from_cferp", return_value=object()),
    patch("orchestration.v3_bridge.ew_assignment_from_cferp", return_value=object()),
    patch("orchestration.v3_bridge.hera_task_from_cferp", return_value=SimpleNamespace(task_id="t", task_kind="evidence_review")),
)


class BridgeContainmentTests(unittest.TestCase):
    def setUp(self):
        for p in PATCH_TASKS:
            p.start()
            self.addCleanup(p.stop)

    def test_each_role_engines_rejection_is_recorded_and_the_run_carries_on(self):
        cases = [
            (Role.SPECIALIST, SimpleNamespace(status="invalid_proposal", diagnostics=("bad",)), "SAHS rejected"),
            (Role.EVIDENCE_WORKER, SimpleNamespace(status="failed", diagnostics=("bad",)), "EWV3 did not return"),
            (Role.ASSESSOR, SimpleNamespace(status="assessment_failed", diagnostics=("bad",)), "HERA returned"),
        ]
        for role, output, text in cases:
            with self.subTest(role=role.value):
                workflow = FakeWorkflow()
                workflow.add(role, "A1")
                bridge = make_bridge(workflow, role, output, max_job_failures=3)

                result, created = bridge.execute("A1")

                self.assertEqual(created, ())
                self.assertEqual(bridge.completed, [("A1", role.value)])   # still counts against the job budget
                failure, = bridge.job_failures
                self.assertEqual((failure["assignment_id"], failure["role"], failure["status"]),
                                 ("A1", role.value, output.status))
                self.assertIn(text, failure["message"])
                self.assertEqual(workflow.failed, [("A1", failure["message"])])
                self.assertEqual(workflow.submitted, [])                   # nothing committed

    def test_the_failure_cap_stops_a_run_that_keeps_failing(self):
        workflow = FakeWorkflow()
        output = SimpleNamespace(status="assessment_failed", diagnostics=("bad",))
        bridge = make_bridge(workflow, Role.ASSESSOR, output, max_job_failures=2)
        for name in ("A1", "A2", "A3"):
            workflow.add(Role.ASSESSOR, name)

        bridge.execute("A1"), bridge.execute("A2")
        with self.assertRaisesRegex(V3BridgeError, r"job failure limit 2 reached"):
            bridge.execute("A3")
        self.assertEqual(len(bridge.job_failures), 2)

    def test_default_still_aborts_on_the_first_rejection_with_the_same_message(self):
        workflow = FakeWorkflow()
        workflow.add(Role.ASSESSOR, "A1")
        bridge = make_bridge(workflow, Role.ASSESSOR,
                             SimpleNamespace(status="assessment_failed", diagnostics=("bad",)), max_job_failures=0)

        with self.assertRaisesRegex(V3BridgeError, r"^HERA returned assessment_failed for A1: \('bad',\)$"):
            bridge.execute("A1")
        self.assertEqual((bridge.job_failures, workflow.failed), ([], []))

    def test_commit_gate_errors_are_not_contained(self):
        workflow = FakeWorkflow()
        workflow.add(Role.ASSESSOR, "A1")
        bridge = make_bridge(workflow, Role.ASSESSOR,
                             SimpleNamespace(status="completed", diagnostics=()), max_job_failures=5)

        with patch("orchestration.v3_bridge.hera_result_to_cferp", return_value=object()):
            with self.assertRaisesRegex(CFERPError, "unknown causal rules"):
                bridge.execute("A1")
        self.assertEqual((bridge.job_failures, workflow.failed), ([], []))


class RunStatusTests(unittest.TestCase):
    def test_a_contained_failure_is_never_reported_as_a_clean_completion(self):
        runner = load_script("run_v3_closed_loop")
        self.assertEqual(runner._run_status(None, []), "completed")
        self.assertEqual(runner._run_status(None, [{"assignment_id": "A1"}]), "completed_with_job_failures")
        self.assertEqual(runner._run_status({"type": "X"}, [{"assignment_id": "A1"}]), "failed_or_partial")
        self.assertEqual(runner.RUN_EXIT_CODES, {"completed": 0, "failed_or_partial": 1,
                                                 "completed_with_job_failures": 2})


class ScorecardTests(unittest.TestCase):
    def report(self, **meta):
        a = lambda claim, text, effect, why="r": {"claim_id": claim, "exact_text": text, "effect": effect, "rationale": why,
                                                 "material_id": {"s1": "M1"}.get(text, "M2")}
        return {
            "run_metadata": {"run_status": "completed_with_job_failures", "role_job_budget": 10,
                             "completed_role_jobs": [["A1", "assessor"], ["A2", "assessor"]],
                             "job_failures": [{"role": "assessor", "status": "assessment_failed"}], **meta},
            "work": [{"role": "assessor", "state": "returned"}, {"role": "assessor", "state": "failed"},
                     {"role": "assessor", "state": "queued"}, {"role": "specialist", "state": "stale"}],
            "board": {"assessments": [a("C1", "s1", "supports"),
                                      a("C1", "s2", "neutral", "No relevant source statement was extracted."),
                                      a("C1", "s2", "neutral", "No relevant source statement was extracted."),
                                      a("C2", "s2", "neutral")],
                      "materials": [{"material_id": "M1"}, {"material_id": "M2"}, {"material_id": "M3"}],
                      "claims": [{}], "causal_links": [], "requests": [{"state": "approved"}], "needs": [{"state": "open"}]},
            "model_raw_responses": [{"task": "extract_statements", "outcome": "accepted"},
                                    {"task": "sahs_proposal", "outcome": "empty_content"}],
            "closed_loop_simulation": {"dispatched_request_ids": ["r1"], "responded_request_ids": [],
                                       "outward_trace": [{"event": "fixture_material_arrival"}]},
        }

    def test_summary_reports_reliability_efficiency_and_evidence_signals(self):
        score = load_script("score_run").summarize(self.report())

        self.assertEqual((score["status"], score["job_failures"]), ("completed_with_job_failures", 1))
        self.assertEqual(score["job_failure_kinds"], {"assessor:assessment_failed": 1})
        self.assertEqual((score["assessments"], score["distinct_claim_sentence_pairs"], score["repeat_factor"]),
                         (4, 3, 1.33))
        self.assertEqual(score["nothing_extracted_share"], 0.5)
        self.assertEqual(score["extractions_per_assessor_job"], 0.5)   # 1 extraction / 2 assessor jobs run
        self.assertEqual((score["open_work"], score["stale"], score["model_attempts_not_accepted"]),
                         ({"assessor": 1}, 1, 1))
        self.assertEqual((score["requests_dispatched"], score["requests_responded"], score["fixture_waves_arrived"]),
                         (1, 0, 1))
        self.assertEqual((score["materials_registered"], score["materials_assessed"]), (3, 2))
        self.assertEqual(score["jobs_by_role"], {"assessor": 2})

    def test_older_outputs_without_the_job_failure_fields_still_score(self):
        old = self.report()
        del old["run_metadata"]["job_failures"]
        self.assertEqual(load_script("score_run").summarize(old)["job_failures"], 0)


if __name__ == "__main__":
    unittest.main()

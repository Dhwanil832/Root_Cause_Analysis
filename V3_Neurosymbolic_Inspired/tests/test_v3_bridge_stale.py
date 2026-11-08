"""Assessor staleness at the HERA/CFERP boundary of the V3 bridge."""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cferp.contracts import JobState, Role
from orchestration.v3_bridge import V3BridgeError, V3PackageBridge, WorkflowVersionReader

AID = "assessor-assignment:c:10"


def fake_workflow(*, state=JobState.RUNNING, snapshot="case:9", board=3):
    manifest = SimpleNamespace(case_snapshot_id=snapshot, board_version=board)
    assignment = SimpleNamespace(
        assignment_id=AID, role=Role.ASSESSOR,
        manifest=SimpleNamespace(case_snapshot_id="case:8", board_version=2))
    workflow = SimpleNamespace(
        case_id="c", assignments={AID: assignment},
        lead=SimpleNamespace(work={AID: SimpleNamespace(state=state)}, manifest=lambda: manifest),
        materials={"m1": SimpleNamespace(version="v7")},
        submitted=[], start_assignment=lambda _aid: None)
    workflow.submit_assessor_result = lambda packet: workflow.submitted.append(packet) or ("requeued",)
    return workflow, assignment


class ReaderPinningTests(unittest.TestCase):
    def test_pinned_current_assignment_reads_its_own_snapshot_with_live_materials(self):
        workflow, assignment = fake_workflow()
        reader = WorkflowVersionReader(workflow)

        live = reader.read("c", ("m1",))
        self.assertEqual((live.case_snapshot_id, live.board_version), ("case:9", "3"))

        reader.pinned = assignment
        pinned = reader.read("c", ("m1",))
        self.assertEqual((pinned.case_snapshot_id, pinned.board_version), ("case:8", "2"))
        self.assertEqual(dict(pinned.material_versions), {"m1": "v7"})

    def test_pin_is_ignored_once_lead_marks_the_assignment_stale(self):
        workflow, assignment = fake_workflow(state=JobState.STALE)
        reader = WorkflowVersionReader(workflow)
        reader.pinned = assignment

        self.assertEqual(reader.read("c", ()).board_version, "3")


class StaleAssessorRoutingTests(unittest.TestCase):
    def bridge(self, workflow, *, stale_in_flight):
        reader = WorkflowVersionReader(workflow)
        seen = {}

        def run(task):
            seen["pinned_during_run"] = reader.pinned
            if stale_in_flight:
                workflow.lead.work[AID].state = JobState.STALE
            return SimpleNamespace(status="stale", diagnostics=("material_version_changed:m1",))

        engine = SimpleNamespace(versions=reader, run=run)
        bridge = V3PackageBridge(workflow, specialist_engine=None, evidence_worker_engine=None,
                                 assessor_engine=engine)
        return bridge, reader, seen

    def execute(self, bridge):
        task = SimpleNamespace(task_id="t10", task_kind="evidence_review")
        with patch("orchestration.v3_bridge.hera_task_from_cferp", return_value=task):
            return bridge.execute(AID)

    def test_stale_result_is_requeued_through_cferp_when_lead_marked_it_stale(self):
        workflow, assignment = fake_workflow()
        bridge, reader, seen = self.bridge(workflow, stale_in_flight=True)

        _output, created = self.execute(bridge)

        self.assertEqual(created, ("requeued",))
        packet, = workflow.submitted
        self.assertEqual((packet.result_id, packet.assignment_id, packet.role),
                         ("hera:t10", AID, Role.ASSESSOR))
        self.assertIs(packet.manifest, assignment.manifest)
        self.assertEqual(packet.payload, {"task_kind": "evidence_review"})
        self.assertIs(seen["pinned_during_run"], assignment)
        self.assertIsNone(reader.pinned)

    def test_stale_result_is_not_committed_when_cferp_still_holds_it_current(self):
        workflow, _ = fake_workflow()
        bridge, reader, _ = self.bridge(workflow, stale_in_flight=False)

        with self.assertRaisesRegex(V3BridgeError, "still holds it as running.*material_version_changed:m1"):
            self.execute(bridge)
        self.assertEqual(workflow.submitted, [])
        self.assertIsNone(reader.pinned)


class NonCompletedResultTests(unittest.TestCase):
    def test_failed_assessment_error_carries_hera_diagnostics_and_commits_nothing(self):
        workflow, _ = fake_workflow()
        output = SimpleNamespace(status="assessment_failed",
                                 diagnostics=("non-revise request disposition must leave revision fields empty",))
        engine = SimpleNamespace(versions=WorkflowVersionReader(workflow), run=lambda task: output)
        bridge = V3PackageBridge(workflow, specialist_engine=None, evidence_worker_engine=None,
                                 assessor_engine=engine)
        task = SimpleNamespace(task_id="t10", task_kind="request_review")

        with patch("orchestration.v3_bridge.hera_task_from_cferp", return_value=task):
            with self.assertRaisesRegex(V3BridgeError,
                    f"HERA returned assessment_failed for {AID}.*must leave revision fields empty"):
                bridge.execute(AID)
        self.assertEqual(workflow.submitted, [])
        self.assertIsNone(engine.versions.pinned)


if __name__ == "__main__":
    unittest.main()

"""PIRIS-to-CFERP handoff checks for the complete V3 runtime boundary."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from cferp import CFERPWorkflow
from orchestration.v3_runtime import V3CaseRuntime
from piris import IncomingItem, InMemoryMaterialIndexer, IntakeEngine, ParserRouter


class StubBridge:
    def __init__(self, workflow):
        self.workflow = workflow

    def run_ready(self, *, max_jobs=100):
        return ()


class V3RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.workflow = CFERPWorkflow("runtime-case")
        self.runtime = V3CaseRuntime(
            self.workflow,
            IntakeEngine(parser=ParserRouter(), indexer=InMemoryMaterialIndexer()),
            StubBridge(self.workflow),
        )

    def test_initial_intake_registers_material_before_lead_launch_and_maps_provenance(self):
        assignments = self.runtime.initialize_case(
            case_packet={"incident_summary": "A carrier beam fell.", "reported_claims": [{
                "claim_id": "C0", "text": "The carrier beam fell.",
                "kind": "incident_event", "source_item_ids": ["E01"],
            }]},
            specialist_profiles=({"profile_id": "mechanical", "cues": ["beam"],
                                  "direction": "Explore mechanical possibilities."},
                                 {"profile_id": "other", "cues": [],
                                  "direction": "Explore alternatives."}),
            initial_items=(IncomingItem.text(
                "E01", "The carrier beam fell.", filename="E01.md",
                declared_kind="incident_notification"),),
            submission_id="opening",
            received_at="2026-10-28T00:00:00Z",
        )

        self.assertTrue(assignments)
        self.assertEqual(len(self.workflow.materials), 1)
        material_id = self.runtime.intake_item_material_ids["E01"]
        self.assertIn(material_id, self.workflow.claims["C0"].provenance)
        self.assertEqual(self.workflow.materials[material_id].content, "The carrier beam fell.")
        specialist = next(a for a in assignments if a.role.value == "specialist")
        self.assertEqual(specialist.context["source_catalog"][0].material_id, material_id)

    def test_later_unsolicited_material_is_registered_via_piris_and_visible_to_lead(self):
        self.runtime.initialize_case(
            case_packet={"reported_claims": [{"claim_id": "C0", "text": "The carrier beam fell.",
                                               "kind": "incident_event"}]},
            specialist_profiles=({"profile_id": "other", "cues": [], "direction": "Explore alternatives."},),
            initial_items=(IncomingItem.text("E01", "The carrier beam fell."),),
            submission_id="opening", received_at="2026-10-28T00:00:00Z",
        )

        rows = self.runtime.submit_material(
            submission_id="unsolicited-upload",
            items=(IncomingItem.text("D2", "Inspection note: the carrier keeper was intact."),),
            received_at="2026-10-28T01:00:00Z",
        )

        material_id = dict(rows)["D2"]
        self.assertIn(material_id, self.workflow.materials)
        self.assertEqual(self.workflow.materials[material_id].content,
                         "Inspection note: the carrier keeper was intact.")
        self.assertTrue(any(event.event_id.startswith(
            f"intake-material:unsolicited-upload:{material_id}:")
            for event in self.workflow.lead.events))
        json.dumps(self.runtime.snapshot())

    def test_openrouter_factory_passes_ask_callable_to_intake_interpreter(self):
        class Model:
            def __init__(self):
                self.calls = []

            def ask(self, task, system, payload):
                self.calls.append((task, system, payload))
                return {"items": [{
                    "item_id": "E01", "suggested_kind": "incident_notification",
                    "request_ids": [], "note": "Opening incident record.",
                }]}

        model = Model()
        legacy_root = (Path(__file__).resolve().parents[2] / "V1_V2_Prompt_and_Rules" /
                       "source" / "RCA_Version_Labeled_Codebase")
        sys.path.insert(0, str(legacy_root))
        try:
            import shared.llm.client as client
            with patch.object(client, "ChatCompletionsModel", return_value=model):
                runtime = V3CaseRuntime.from_openrouter(
                    "runtime-openrouter-factory", enable_lead_semantics=False,
                )
        finally:
            sys.path.remove(str(legacy_root))
        runtime.initialize_case(
            case_packet={"reported_claims": [{
                "claim_id": "C0", "text": "The carrier beam fell.",
                "kind": "incident_event", "source_item_ids": ["E01"],
            }]},
            specialist_profiles=({"profile_id": "other", "cues": [],
                                 "direction": "Explore alternatives."},),
            initial_items=(IncomingItem.text("E01", "The carrier beam fell."),),
        )
        self.assertEqual(model.calls[0][0], "suggest_intake_metadata")


if __name__ == "__main__":
    unittest.main()

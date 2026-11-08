from __future__ import annotations

from types import SimpleNamespace
import unittest

from sahs.archive_adapter import ArchiveSpecialistAdapter


class ScriptedArchiveModel:
    def __init__(self):
        self.calls = []

    def ask(self, task, system, payload):
        self.calls.append(SimpleNamespace(model="test-model", actual_call_performed=False))
        target_id = payload["task"]["focal_proposition_id"]
        if len(self.calls) > 1:
            return {
                "schema_version": "1",
                "proposed_propositions": [{
                    "proposition_id": "control-power-lost",
                    "text": "Control power was lost before the actuator failure",
                    "kind": "incident_event", "source_refs": [], "time_scope": "incident",
                }],
                "proposed_rules": [{
                    "rule_id": "power-loss-led-to-actuator-failure",
                    "antecedent_ids": ["control-power-lost"], "consequent_id": target_id,
                    "relation": "may_cause", "modality": "may", "conditions": [],
                    "time_constraint": None, "basis": "model_proposed", "source_refs": [],
                    "source_relation": None, "vetted_rule_id": None,
                }],
                "clarification_items": [], "information_gaps": [],
            }
        return {
            "schema_version": "1",
            "proposed_propositions": [{
                "proposition_id": "actuator-failed",
                "text": "The actuator failed during the incident",
                "kind": "incident_event", "source_refs": [], "time_scope": "incident",
            }],
            "proposed_rules": [{
                "rule_id": "actuator-caused-fall", "antecedent_ids": ["actuator-failed"],
                "consequent_id": target_id, "relation": "may_cause", "modality": "may",
                "conditions": [], "time_constraint": None, "basis": "model_proposed",
                "source_refs": [], "source_relation": None, "vetted_rule_id": None,
            }],
            "clarification_items": [], "information_gaps": [],
        }


class TestArchiveAdapter(unittest.TestCase):
    def test_maps_archive_snapshot_calls_configured_model_and_keeps_board_read_only(self):
        model = ScriptedArchiveModel()
        investigator = SimpleNamespace(
            _models={"specialist": model},
            session=SimpleNamespace(
                case_id="archive-case",
                kernel=SimpleNamespace(revision=7, rules=[], sources={}),
                documents={},
            ),
            claims={}, hypotheses={}, gaps={}, focal_event="Carrier beam fell",
            model_calls=[], model_input_history=[],
            _claim_projection=lambda: [],
        )
        before = (investigator.session.kernel.revision, len(investigator.session.kernel.rules))
        adapter = ArchiveSpecialistAdapter(investigator)
        assignment = adapter.assignment_from_archive(
            investigator,
            assignment_id="sahs-run-1",
            operation_goal="generate_alternatives",
            lead_direction={"focus": "mechanical"},
        )
        result = adapter.run(assignment)

        self.assertEqual(result.status, "open_frontier")
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(investigator.model_input_history[0]["task"], "sahs_proposal")
        self.assertEqual(
            (investigator.session.kernel.revision, len(investigator.session.kernel.rules)), before
        )


if __name__ == "__main__":
    unittest.main()

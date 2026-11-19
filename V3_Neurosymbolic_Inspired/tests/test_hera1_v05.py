"""Assessor changes for v0.5 Step 1: packet IDs from the quote, consistent_with, and absence of a record."""
from __future__ import annotations

import unittest

from hera1 import EvidenceMaterial, Hera1Engine

from test_hera1 import FixedVersions, ScriptedModel, evidence_task, finding


def one_part(text, claim_type="other"):
    return {"hypothesis_id": "h1", "parts": [{"part_id": "p1", "claim_type": claim_type, "text": text}]}


def statement(quote, *, material_id="L1", source_id="D1", version="v1", rep="R1",
              kind="incident_observation", modality="asserted"):
    return {"statement_id": "s1", "material_id": material_id, "source_id": source_id,
            "source_version": version, "representation_id": rep, "quote": quote, "start_offset": 0,
            "kind": kind, "modality": modality, "scope": "incident", "timing": "incident"}


def run(text, claim, relation, *, row=None, materials=None, claim_type="other", versions=None):
    materials = materials or (EvidenceMaterial("L1", "D1", "v1", "R1", text),)
    task = evidence_task(materials=materials, hypothesis=one_part(claim, claim_type))
    compared = {"parts": [{"part_id": "p1", "findings": [finding(relation, ["s1"], "reason")]}]}
    if relation == "consistent_with":
        compared["parts"][0]["findings"][0]["inference_bridge"] = "it fits"
    model = ScriptedModel([{"statements": [row or statement(text)]}, compared])
    return Hera1Engine(model, FixedVersions(versions=versions)).run(task)


class PacketIds(unittest.TestCase):
    TEXT = "The keeper plate remained bolted to the recovered link arm."

    def test_miscopied_ids_are_taken_from_the_packet_when_the_quote_is_found(self):
        row = statement(self.TEXT, source_id="D1x", version="v1-typo", rep="R9")
        result = run(self.TEXT, "The keeper plate stayed bolted.", "supports", row=row)
        out = result.payload["source_statements"][0]
        self.assertEqual((out["source_id"], out["source_version"], out["representation_id"]), ("D1", "v1", "R1"))
        self.assertTrue(out["ids_filled_from_packet"])
        self.assertEqual(result.payload["parts"][0]["relation"], "supports")

    def test_correct_ids_are_left_unmarked(self):
        result = run(self.TEXT, "The keeper plate stayed bolted.", "supports")
        self.assertNotIn("ids_filled_from_packet", result.payload["source_statements"][0])

    def test_a_quote_found_in_two_packet_materials_cannot_be_resolved(self):
        mats = (EvidenceMaterial("L1", "D1", "v1", "R1", self.TEXT), EvidenceMaterial("L2", "D2", "v1", "R2", self.TEXT))
        row = statement(self.TEXT, material_id="L?", source_id="D?")
        result = run(self.TEXT, "The keeper plate stayed bolted.", "supports", row=row, materials=mats,
                     versions={"D1": "v1", "D2": "v1"})
        self.assertEqual(result.status, "assessment_failed")


class ConsistentWith(unittest.TestCase):
    def test_consistent_with_is_kept_and_summarised(self):
        text = "The upper carrier edge contacts the housing in this view."
        result = run(text, "The carrier was wedged against the housing.", "consistent_with")
        self.assertEqual(result.payload["parts"][0]["relation"], "consistent_with")
        self.assertEqual(result.payload["evidence_effect"], "consistent")


class AbsenceOfRecord(unittest.TestCase):
    def test_a_record_of_nothing_seen_does_not_support_that_something_happened(self):
        text = "No branch hydraulic pressure is visible."
        result = run(text, "There was a drop in hydraulic pressure in the lifting yokes.", "supports")
        self.assertEqual(result.payload["source_statements"][0]["modality"], "not_recorded")
        self.assertEqual(result.payload["parts"][0]["relation"], "insufficient_or_unclear")
        self.assertEqual(result.payload["scope_guard_flags"][0]["rule"], "absence_of_record_does_not_settle_the_claim")

    def test_nor_contradict_it(self):
        text = "This sheet does not record the pressure on the isolated cylinder side of that valve."
        result = run(text, "The valve held pressure on the cylinder side.", "contradicts")
        self.assertEqual(result.payload["parts"][0]["relation"], "insufficient_or_unclear")

    def test_it_can_support_a_claim_about_what_was_recorded(self):
        text = "No sensor channel measuring flow through IV-RB3-17 was configured in the exported historian set."
        result = run(text, "Flow through valve IV-RB3-17 was not measured during the event.", "supports")
        self.assertEqual(result.payload["parts"][0]["relation"], "supports")

    def test_an_inspection_finding_no_defect_is_not_an_absence_of_record(self):
        text = "No gross fracture or missing portion of that plate was recorded."
        result = run(text, "The keeper plate was intact after the fall.", "supports")
        self.assertNotEqual(result.payload["source_statements"][0]["modality"], "not_recorded")
        self.assertEqual(result.payload["parts"][0]["relation"], "supports")

    def test_a_person_saying_they_did_not_act_is_negated_not_absent(self):
        text = "I did not install a pin, block, or crib during my preparation."
        result = run(text, "No restraint pin was installed.", "supports")
        self.assertEqual(result.payload["source_statements"][0]["modality"], "negated")
        self.assertEqual(result.payload["parts"][0]["relation"], "supports")


if __name__ == "__main__":
    unittest.main()

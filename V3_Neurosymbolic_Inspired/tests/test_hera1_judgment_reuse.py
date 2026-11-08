"""Reusing HERA's judgment when the same claim and passage are assessed again."""
from __future__ import annotations

import unittest

from hera1 import EvidenceMaterial, Hera1Engine
from hera1.config import AssessorConfig
from tests.test_hera1 import FixedVersions, ScriptedModel, comparison, evidence_task, extraction

TEXT = "A leaking valve can cause pressure loss."


def second_need_task(text=TEXT, claim_text=None):
    """The same claim and passage, surfaced again under a different link ID."""
    base = evidence_task()
    hypothesis = base.hypothesis
    if claim_text is not None:
        hypothesis = {**hypothesis, "parts": [{**hypothesis["parts"][0], "text": claim_text},
                                              *hypothesis["parts"][1:]]}
    return evidence_task(
        task_id="t2", work_item_id="w2", event_id="e2", hypothesis=hypothesis,
        materials=(EvidenceMaterial("L9", "D1", "v1", "R1", text, "manual", 0,
                                    {"page": 2, "candidate_link_id": "L9"}),))


def engine(model, *, reuse=True):
    return Hera1Engine(model, FixedVersions(), config=AssessorConfig(reuse_identical_judgments=reuse))


class JudgmentReuseTests(unittest.TestCase):
    def test_identical_claim_and_passage_reuses_the_judgment_without_a_model_call(self):
        model = ScriptedModel([extraction(), comparison()])
        hera = engine(model)

        first = hera.run(evidence_task())
        second = hera.run(second_need_task())

        self.assertEqual(len(model.calls), 2)          # the second task asked nothing
        self.assertEqual((first.model_calls, second.model_calls), (2, 0))
        self.assertEqual(second.status, "completed")
        self.assertIn("reused from task t1", second.diagnostics[0])
        self.assertEqual(second.payload["evidence_effect"], first.payload["evidence_effect"])
        self.assertEqual(second.payload["parts"], first.payload["parts"])
        # Retargeted to the new passage; the first result is left untouched.
        statement, = second.payload["source_statements"]
        self.assertEqual((statement["material_id"], statement["location"]["candidate_link_id"]), ("L9", "L9"))
        self.assertEqual(first.payload["source_statements"][0]["material_id"], "L1")

    def test_an_empty_extraction_is_reused_too(self):
        model = ScriptedModel([{"statements": []}])
        hera = engine(model)

        first = hera.run(evidence_task())
        second = hera.run(second_need_task())

        self.assertEqual(len(model.calls), 1)
        self.assertEqual(second.payload["evidence_effect"], "insufficient")
        self.assertEqual(second.payload["source_statements"], [])
        self.assertEqual((first.model_calls, second.model_calls), (1, 0))

    def test_a_different_claim_or_passage_is_judged_afresh(self):
        for variant in (second_need_task(claim_text="The valve was open."),
                        second_need_task(text="A different sentence about the pump.")):
            with self.subTest(variant=variant.hypothesis["parts"][0]["text"] + variant.materials[0].text):
                model = ScriptedModel([{"statements": []}, {"statements": []}])
                hera = engine(model)
                hera.run(evidence_task())
                hera.run(variant)
                self.assertEqual(len(model.calls), 2)

    def test_reuse_is_off_by_default(self):
        model = ScriptedModel([{"statements": []}, {"statements": []}])
        hera = Hera1Engine(model, FixedVersions())

        hera.run(evidence_task())
        second = hera.run(second_need_task())

        self.assertEqual(len(model.calls), 2)
        self.assertEqual(second.diagnostics, ())

    def test_a_judgment_that_failed_validation_is_never_cached(self):
        bad = extraction()
        bad["statements"][0]["exact_quote"] = bad["statements"][0].pop("quote")
        model = ScriptedModel([bad, {"statements": []}])
        hera = engine(model)

        failed = hera.run(evidence_task())
        later = hera.run(second_need_task())

        self.assertEqual(failed.status, "assessment_failed")
        self.assertEqual(len(model.calls), 2)           # the later task asked afresh
        self.assertEqual(later.status, "completed")
        self.assertEqual(later.diagnostics, ())


if __name__ == "__main__":
    unittest.main()

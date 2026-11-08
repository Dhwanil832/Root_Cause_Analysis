"""Bounded re-ask when a HERA reply fails its Python validation."""
from __future__ import annotations

import unittest

from hera1 import AssessmentTask, Hera1Engine
from hera1.config import AssessorConfig
from tests.test_hera1 import FixedVersions, ScriptedModel, comparison, evidence_task, extraction


def request_task(task_id="t-retry"):
    return AssessmentTask("1", task_id, f"w-{task_id}", f"e-{task_id}", "c1", "case:s1", "b1",
        "request_review", "evidence_worker", "ew1",
        request={"request_id": "r1", "target_id": "g1", "kind": "question", "text": "Was it open?"})


def review(**overrides):
    reply = {"disposition": "not_eligible", "rationale": "The target cannot supply this.",
             "existing_evidence_status": "unresolved",
             "existing_evidence_rationale": "No retrieved item resolves this gap.",
             "proportionality": "proportionate", "revision_feedback": "", "revised_request": ""}
    reply.update(overrides)
    return reply


# The reply gpt-oss gave: not_eligible, but with revision fields filled in.
BREAKS_PROMPT_RULE = review(revision_feedback="Limit the request to a time window.")


def engine(model, retries):
    return Hera1Engine(model, FixedVersions(), config=AssessorConfig(max_output_retries=retries))


class OutputRetryTests(unittest.TestCase):
    def test_rejected_reply_is_re_asked_with_the_reason_and_the_corrected_reply_is_used(self):
        model = ScriptedModel([BREAKS_PROMPT_RULE, review()])

        result = engine(model, 1).run(request_task())

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.payload["disposition"], "not_eligible")
        self.assertEqual(result.payload["revision_feedback"], "")
        self.assertEqual(result.model_calls, 2)
        self.assertNotIn("previous_response_rejected", model.calls[0][2])
        feedback = model.calls[1][2]["previous_response_rejected"]
        self.assertIn("must leave revision fields empty", feedback["reason"])
        self.assertEqual(feedback["previous_reply"], BREAKS_PROMPT_RULE)

    def test_a_reply_that_still_fails_is_rejected_not_repaired(self):
        model = ScriptedModel([BREAKS_PROMPT_RULE, BREAKS_PROMPT_RULE, review()])

        result = engine(model, 1).run(request_task())

        self.assertEqual(result.status, "assessment_failed")
        self.assertEqual(result.payload, {})
        self.assertEqual(result.model_calls, 2)  # bounded: the third reply is never requested
        self.assertIn("rejected on 2 attempts", result.diagnostics[0])
        self.assertIn("must leave revision fields empty", result.diagnostics[0])

    def test_retries_are_off_by_default(self):
        model = ScriptedModel([BREAKS_PROMPT_RULE, review()])

        result = Hera1Engine(model, FixedVersions()).run(request_task())

        self.assertEqual(result.status, "assessment_failed")
        self.assertEqual(result.model_calls, 1)
        self.assertEqual(result.diagnostics, ("non-revise request disposition must leave revision fields empty",))

    def test_feedback_goes_only_to_the_step_that_was_rejected(self):
        bad_extraction = extraction()
        bad_extraction["statements"][0]["exact_quote"] = bad_extraction["statements"][0].pop("quote")
        model = ScriptedModel([bad_extraction, extraction(), comparison()])

        result = engine(model, 1).run(evidence_task())

        self.assertEqual(result.status, "completed")
        self.assertEqual([call[0] for call in model.calls],
                         ["extract_statements", "extract_statements", "compare_statements"])
        self.assertIn("exact_quote", model.calls[1][2]["previous_response_rejected"]["reason"])
        self.assertNotIn("previous_response_rejected", model.calls[2][2])

    def test_missing_link_citation_error_lists_the_ids_to_copy_and_stays_strict(self):
        links = [{"candidate_link_id": f"cl:{c * 6}", "source_id": "m1", "slot_id": "s1",
                  "exact_text": "keeper plate on each link arm"} for c in "abc"]
        task = request_task("t-links")
        task = AssessmentTask(task.schema_version, task.task_id, task.work_item_id, task.event_id,
            task.case_id, task.case_snapshot_id, task.board_version, task.task_kind, task.sender_role,
            task.sender_id, request=task.request, context={"existing_candidate_links": links})
        no_prefix = review(existing_evidence_rationale="Only keeper plates appear (IDs: aaaaaa, bbbbbb).")
        exact = review(existing_evidence_rationale="Only keeper plates appear in cl:aaaaaa.")
        model = ScriptedModel([no_prefix, exact])

        result = engine(model, 1).run(task)

        self.assertEqual(result.status, "completed")
        reason = model.calls[1][2]["previous_response_rejected"]["reason"]
        self.assertIn("copy an ID exactly as written, including any prefix", reason)
        self.assertIn("cl:aaaaaa, cl:bbbbbb, cl:cccccc", reason)
        # Still strict: an unprefixed citation is never accepted, only re-asked.
        rejected = engine(ScriptedModel([no_prefix]), 0).run(task)
        self.assertEqual(rejected.status, "assessment_failed")
        self.assertIn("cl:aaaaaa", rejected.diagnostics[0])

    def test_compare_prompt_states_when_an_inference_bridge_is_required(self):
        from hera1.prompts import COMPARE_STATEMENTS

        flat = " ".join(COMPARE_STATEMENTS.split())
        self.assertIn("`inference_bridge` (for supports, weakens, or contradicts: one nonempty sentence", flat)
        self.assertIn("for any other relation: an empty string", flat)

    def test_negative_retry_count_is_refused(self):
        with self.assertRaises(ValueError):
            AssessorConfig(max_output_retries=-1)


if __name__ == "__main__":
    unittest.main()

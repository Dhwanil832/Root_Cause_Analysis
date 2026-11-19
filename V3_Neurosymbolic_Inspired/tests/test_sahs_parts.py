"""Specialist changes for v0.5 Step 1: claim parts and claims that deny each other."""
from __future__ import annotations

import unittest

from sahs.prompt_builder import PROPOSAL_FORMAT_SCHEMA
from sahs.validation import ProposalValidationError, claim_parts, validate_proposal_batch

from test_sahs_engine import assignment, batch

VALVE = "Valve IV-RB3-17 was closed at 10:47."


def prop(pid, text, parts=None, denies=None, kind="component_state"):
    row = {"proposition_id": pid, "text": text, "kind": kind, "source_refs": [], "time_scope": None}
    if parts is not None:
        row["parts"] = parts
    if denies is not None:
        row["denies"] = denies
    return row


def validate(*props):
    out = validate_proposal_batch(batch(proposed_propositions=list(props), proposed_rules=[]), assignment())
    return {p.proposition_id: p for p in out.proposed_propositions}, out.rejected_fragments


class Parts(unittest.TestCase):
    def test_parts_that_cover_the_claim_are_kept(self):
        self.assertEqual(claim_parts(VALVE, ["Valve IV-RB3-17", "was closed", "at 10:47"]),
                         ("Valve IV-RB3-17", "was closed", "at 10:47"))

    def test_one_part_or_none_means_the_whole_claim(self):
        self.assertEqual(claim_parts(VALVE, []), ())
        self.assertEqual(claim_parts(VALVE, [VALVE]), ())

    def test_case_and_spacing_do_not_matter(self):
        self.assertEqual(len(claim_parts(VALVE, ["valve  IV-RB3-17", "WAS CLOSED", "at 10:47"])), 3)

    def test_a_part_not_in_the_text_is_refused(self):
        with self.assertRaisesRegex(ProposalValidationError, "not a phrase"):
            claim_parts(VALVE, ["Valve IV-RB3-17", "was sealed", "at 10:47"])

    def test_parts_that_leave_a_word_out_are_refused(self):
        with self.assertRaisesRegex(ProposalValidationError, "leave out: 10:47"):
            claim_parts(VALVE, ["Valve IV-RB3-17", "was closed"])

    def test_overlapping_parts_are_refused(self):
        with self.assertRaisesRegex(ProposalValidationError, "overlap"):
            claim_parts(VALVE, ["Valve IV-RB3-17 was", "was closed at 10:47"])

    def test_bad_parts_keep_the_claim_as_one_part_and_are_reported(self):
        kept, rejected = validate(prop("V", VALVE, parts=["Valve IV-RB3-17", "was closed"]))
        self.assertEqual(kept["V"].parts, ())
        self.assertEqual(rejected[0].fragment_type, "proposition_parts")

    def test_a_proposal_without_parts_is_still_accepted(self):
        kept, rejected = validate(prop("V", VALVE))
        self.assertEqual((kept["V"].parts, rejected), ((), ()))

    def test_parts_and_denies_are_offered_but_optional(self):
        # Requiring them on every claim doubled answer length and set gpt-oss looping (v0.5 run 1).
        item = PROPOSAL_FORMAT_SCHEMA["properties"]["proposed_propositions"]["items"]
        self.assertTrue({"parts", "denies"} <= set(item["properties"]))
        self.assertFalse({"parts", "denies"} & set(item["required"]))

    def test_rule_modality_cannot_be_left_empty(self):
        # gpt-oss left a free-text modality empty on every rule (v0.5 run 2), and the
        # validator drops a rule with an empty modality, so no links reached the board.
        rule = PROPOSAL_FORMAT_SCHEMA["properties"]["proposed_rules"]["items"]
        self.assertEqual(rule["properties"]["modality"], {"enum": ["possible", "conditional"]})


class Denies(unittest.TestCase):
    def test_a_claim_can_deny_another_in_the_same_proposal(self):
        kept, _ = validate(prop("RAISED", "The carrier was raised at the fall."),
                           prop("NOT-RAISED", "The carrier was not raised at the fall.", denies=["RAISED"]))
        self.assertEqual(kept["NOT-RAISED"].denies, ("RAISED",))

    def test_a_claim_can_deny_one_already_on_the_board(self):
        kept, _ = validate(prop("NOT-FELL", "The carrier beam did not fall.", denies=["beam-fell"]))
        self.assertEqual(kept["NOT-FELL"].denies, ("beam-fell",))

    def test_an_unknown_or_self_denial_is_dropped_and_reported_but_the_claim_kept(self):
        kept, rejected = validate(prop("X", "The carrier was raised.", denies=["NOPE"]),
                                  prop("Y", "The carrier was lowered.", denies=["Y"]))
        self.assertEqual((kept["X"].denies, kept["Y"].denies), ((), ()))
        self.assertEqual([r.fragment_type for r in rejected], ["proposition_denies", "proposition_denies"])


if __name__ == "__main__":
    unittest.main()

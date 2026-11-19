"""Claim and link status rules (cferp/status.py)."""
from __future__ import annotations

import unittest

from cferp import status as st

INCIDENT = {"claim_id": "FALL", "kind": "incident_event", "incident_status": "reported", "text": "beam fell"}


def claim(cid, parts=()):
    return {"claim_id": cid, "kind": "component_state", "incident_status": "not_applicable",
            "text": cid, "parts": list(parts)}


def a(cid, effect, material="m1", status="current", part_effects=None):
    row = {"claim_id": cid, "effect": effect, "material_id": material, "status": status}
    if part_effects:
        row["part_effects"] = part_effects
    return row


def status_of(c, rows, origins=None):
    return st.claim_status(c, rows, origins)


class ClaimStatus(unittest.TestCase):
    def test_incident_stays_reported(self):
        self.assertEqual(status_of(INCIDENT, [a("FALL", "contradicts")])["status"], "reported")

    def test_no_assessment_or_only_not_relevant_is_unchecked(self):
        self.assertEqual(status_of(claim("C"), [])["status"], "unchecked")
        out = status_of(claim("C"), [a("C", "not_relevant"), a("C", "not_relevant", "m2")])
        self.assertEqual((out["status"], out["not_relevant_assessments"]), ("unchecked", 2))

    def test_one_support_on_a_one_part_claim_shows_it(self):
        self.assertEqual(status_of(claim("C"), [a("C", "supports")])["status"], "shown")

    def test_open_effects_and_old_neutral_leave_the_claim_open(self):
        for effect in ("consistent_with", "insufficient", "weakens", "neutral"):
            self.assertEqual(status_of(claim("C"), [a("C", effect)])["status"], "open", effect)

    def test_contradiction_without_support_is_contradicted(self):
        self.assertEqual(status_of(claim("C"), [a("C", "contradicts"), a("C", "neutral")])["status"], "contradicted")

    def test_support_and_contradiction_on_one_part_is_contested(self):
        out = status_of(claim("C"), [a("C", "supports", "m1"), a("C", "contradicts", "m2")])
        self.assertEqual(out["status"], "contested")

    def test_superseded_assessments_do_not_count(self):
        rows = [a("C", "contradicts", status="superseded_by_reassessment"), a("C", "supports", "m2")]
        self.assertEqual(status_of(claim("C"), rows)["status"], "shown")


class Parts(unittest.TestCase):
    PARTS = ("valve IV-RB3-17", "was isolated", "at 11:10")

    def test_support_for_some_parts_is_partly_shown_and_lists_the_rest(self):
        row = a("C", "supports", part_effects={"was isolated": "supports", "at 11:10": "supports",
                                               "valve IV-RB3-17": "insufficient"})
        out = status_of(claim("C", self.PARTS), [row])
        self.assertEqual((out["status"], out["missing_parts"]), ("partly shown", ["valve IV-RB3-17"]))

    def test_parts_supported_by_different_passages_combine_to_shown(self):
        rows = [a("C", "supports", "m1", part_effects={"valve IV-RB3-17": "supports", "was isolated": "supports"}),
                a("C", "supports", "m2", part_effects={"at 11:10": "supports"})]
        out = status_of(claim("C", self.PARTS), rows)
        self.assertEqual((out["status"], out["independent_sources"]), ("shown", 2))

    def test_one_contradicted_part_makes_the_claim_contradicted(self):
        rows = [a("C", "supports", "m1", part_effects={p: "supports" for p in self.PARTS[:2]}),
                a("C", "contradicts", "m2", part_effects={"at 11:10": "contradicts"})]
        self.assertEqual(status_of(claim("C", self.PARTS), rows)["status"], "contradicted")

    def test_an_assessment_marking_no_parts_applies_to_every_part(self):
        self.assertEqual(status_of(claim("C", self.PARTS), [a("C", "supports")])["status"], "shown")


class Sources(unittest.TestCase):
    def test_a_recap_and_its_original_count_once(self):
        rows = [a("C", "supports", "E08"), a("C", "supports", "E16")]
        out = status_of(claim("C"), rows, origins={"E16": "E08", "E08": "E08"})
        self.assertEqual((out["independent_sources"], out["sources_assumed_independent"]), (1, False))

    def test_unknown_origin_counts_as_its_own_source_and_says_so(self):
        out = status_of(claim("C"), [a("C", "supports", "E08"), a("C", "supports", "E16")])
        self.assertEqual((out["independent_sources"], out["sources_assumed_independent"]), (2, True))

    def test_an_origin_loop_stops(self):
        self.assertIn(st.source_of("A", {"A": "B", "B": "A"}), {"A", "B"})


def board(claims, links, assessments):
    return {"claims": claims, "causal_links": links, "assessments": assessments}


def link(lid, sources, target):
    return {"link_id": lid, "source_claim_ids": list(sources), "target_claim_id": target}


class LinksAndChains(unittest.TestCase):
    def setUp(self):
        self.b = board([INCIDENT, claim("VALVE"), claim("BLEED"), claim("LOOSE")],
                       [link("L1", ["VALVE"], "FALL"), link("L2", ["BLEED"], "VALVE")],
                       [a("VALVE", "supports"), a("BLEED", "neutral")])
        self.out = st.board_status(self.b)

    def test_a_link_is_both_ends_shown_only_when_every_end_is(self):
        self.assertEqual(self.out["links"]["L1"]["status"], "both ends shown")
        self.assertEqual(self.out["links"]["L2"]["status"], "proposed")

    def test_chain_runs_from_the_incident_to_the_earliest_cause_and_names_its_weakest_point(self):
        (path,) = self.out["chains"]["paths"]
        self.assertEqual((path["root"], path["weakest"]["id"], path["weakest_claim"]["id"]), ("BLEED", "L2", "BLEED"))

    def test_claims_off_every_path_are_listed(self):
        self.assertEqual(self.out["chains"]["claims_on_no_path"], ["LOOSE"])

    def test_a_cycle_ends_the_path_instead_of_looping(self):
        b = board([INCIDENT, claim("X"), claim("Y")],
                  [link("L1", ["X"], "FALL"), link("L2", ["Y"], "X"), link("L3", ["X"], "Y")], [])
        self.assertEqual([p["root"] for p in st.board_status(b)["chains"]["paths"]], ["Y"])

    def test_a_link_to_a_missing_claim_is_skipped(self):
        b = board([INCIDENT, claim("X")], [link("L1", ["X", "GONE"], "FALL")], [])
        self.assertEqual(len(st.board_status(b)["chains"]["paths"]), 1)


if __name__ == "__main__":
    unittest.main()

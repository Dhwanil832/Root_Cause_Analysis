"""The ground-truth scorer: node matching, key sentences, unresolved nodes, traps."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

_SPEC = importlib.util.spec_from_file_location(
    "score_against_truth", Path(__file__).resolve().parents[1] / "scripts" / "score_against_truth.py")
sat = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sat)

SEEPAGE = "With the handle at closed and differential pressure applied from the cylinder-side port toward the supply-side port, fluid seepage was observed."
NO_SEAL = 'The local valve position is checked "closed" at 10:47. The copy does not contain a sealing test result.'

TRUTH = {
    "chart": {"nodes": [
        {"id": "G00", "text": "Carrier beam fell into mill pit", "focal": True},
        {"id": "G13", "text": "Hydraulic isolation valve has slow bleed through"},
        {"id": "G19", "text": "Only one keeper installed"},
        {"id": "G14", "text": "Isolation valves are not routinely inspected but replaced when found defective"},
    ]},
    "evidence": {
        "node_evidence": {
            "G13": [
                {"doc": "E08", "quote": SEEPAGE, "relation": "supports"},
                {"doc": "E03", "quote": NO_SEAL, "relation": "insufficient"},
            ],
        },
        "nodes_with_no_evidence_in_packet": ["G14 valve replacement practice"],
    },
}


def claim(cid, text, parents=("ROOT",)):
    return {"claim_id": cid, "text": text, "parent_claim_ids": list(parents)}


def assess(cid, doc_mat, text, effect):
    return {"claim_id": cid, "material_id": doc_mat, "exact_text": text, "effect": effect}


def report(claims, assessments):
    return {"board": {
        "claims": [claim("ROOT", "A carrier beam fell into the mill pit", parents=()), *claims],
        "assessments": assessments,
        "materials": [{"material_id": "m8", "title": "E08.md"}, {"material_id": "m3", "title": "E03.md"},
                      {"material_id": "m16", "title": "E16.md"}, {"material_id": "m13", "title": "E13.md"}],
    }}


class NodeCoverage(unittest.TestCase):
    def test_matching_claim_covers_node(self):
        out = sat.score(report([claim("C1", "The hydraulic isolation valve has a slow bleed through")], []), TRUTH)
        self.assertTrue(out["node_matches"]["G13"]["covered"])
        self.assertEqual(out["node_matches"]["G13"]["claim_id"], "C1")

    def test_one_shared_word_does_not_cover(self):
        out = sat.score(report([claim("C1", "Valve IV-RB3-17 was closed")], []), TRUTH)
        self.assertFalse(out["node_matches"]["G13"]["covered"])

    def test_two_shared_words_below_the_share_threshold_do_not_cover(self):
        out = sat.score(report([claim("C1", "The hydraulic valve was inspected")], []), TRUTH)
        self.assertFalse(out["node_matches"]["G13"]["covered"])
        self.assertEqual(out["node_matches"]["G13"]["best_score"], 0.33)

    def test_root_event_claim_cannot_stand_in_for_a_cause(self):
        truth = {**TRUTH, "chart": {"nodes": [*TRUTH["chart"]["nodes"],
                 {"id": "G10", "text": "carrier beam fell into mill pit"}]}}
        out = sat.score(report([], []), truth)
        self.assertFalse(out["node_matches"]["G10"]["covered"])

    def test_claims_matching_no_node_are_off_chart(self):
        out = sat.score(report([claim("C1", "Keeper plate surfaces were inspected"),
                                claim("C2", "Only one keeper installed on the link arm")], []), TRUTH)
        self.assertEqual(out["claims_off_chart"], 1)
        self.assertEqual(out["claims_total"], 2)


class KeySentences(unittest.TestCase):
    def test_assessed_sentence_counts_even_with_trailing_punctuation_difference(self):
        out = sat.score(report([claim("C1", "isolation valve slow bleed")],
                               [assess("C1", "m8", SEEPAGE.rstrip("."), "supports")]), TRUTH)
        self.assertEqual(out["key_sentences_assessed"], 1)
        self.assertEqual(out["supports_found"], 1)

    def test_support_on_a_claim_of_another_node_is_not_found_but_listed(self):
        c = claim("C1", "Only one keeper installed")
        out = sat.score(report([c], [assess("C1", "m8", SEEPAGE, "supports")]), TRUTH)
        self.assertEqual(out["supports_found"], 0)
        self.assertEqual(out["supports_found_any_claim"], 1)
        self.assertEqual(out["supports_on_other_claims"][0]["claims"], ["C1"])

    def test_support_on_the_matching_claim_is_found(self):
        c = claim("C1", "Hydraulic isolation valve has slow bleed through")
        out = sat.score(report([c], [assess("C1", "m8", SEEPAGE, "supports")]), TRUTH)
        self.assertEqual((out["supports_found"], out["supports_on_other_claims"]), (1, []))

    def test_same_sentence_in_the_wrong_document_does_not_count(self):
        out = sat.score(report([claim("C1", "x")], [assess("C1", "m16", SEEPAGE, "supports")]), TRUTH)
        self.assertEqual(out["key_sentences_assessed"], 0)

    def test_insufficient_sentence_called_contradicting_is_overclaimed(self):
        out = sat.score(report([claim("C1", "x")], [assess("C1", "m3", NO_SEAL, "contradicts")]), TRUTH)
        self.assertEqual(len(out["insufficient_overclaimed"]), 1)

    def test_insufficient_sentence_called_neutral_is_fine(self):
        out = sat.score(report([claim("C1", "x")], [assess("C1", "m3", NO_SEAL, "neutral")]), TRUTH)
        self.assertEqual(out["insufficient_overclaimed"], [])

    def test_unassessed_key_sentences_lower_recall(self):
        out = sat.score(report([], []), TRUTH)
        self.assertEqual(out["key_sentences_assessed"], 0)
        self.assertEqual(out["key_sentence_recall"], 0.0)


def labelled(fits_by_text, source="human"):
    labels = {sat.normalise(text): {"source": source, "nodes": [{"id": n, "fit": f} for n, f in fits]}
              for text, fits in fits_by_text.items()}
    return {**TRUTH, "labels": labels}


class Labels(unittest.TestCase):
    def test_a_label_matches_a_claim_that_shares_too_few_words(self):
        c = claim("C1", "Valve IV-RB3-17 was not properly sealed")
        truth = labelled({"Valve IV-RB3-17 was not properly sealed": [("G13", "same")]})
        out = sat.score(report([c], [assess("C1", "m8", SEEPAGE, "supports")]), truth)
        self.assertTrue(out["node_matches"]["G13"]["covered"])
        self.assertEqual((out["supports_found"], out["claim_matching"]), (1, {"human": 1}))

    def test_claims_without_a_label_are_listed_for_labelling(self):
        known, new = claim("C1", "Valve IV-RB3-17 was not properly sealed"), claim("C2", "Keeper plate cracked")
        out = sat.score(report([known, new], []), labelled({known["text"]: [("G13", "same")]}))
        self.assertEqual(out["unlabelled_claims"], ["Keeper plate cracked"])

    def test_a_label_of_no_node_overrides_word_overlap(self):
        c = claim("C1", "Hydraulic isolation valve has slow bleed through")
        out = sat.score(report([c], []), labelled({c["text"]: []}))
        self.assertFalse(out["node_matches"]["G13"]["covered"])
        self.assertEqual(out["claims_off_chart"], 1)

    def test_support_for_a_node_on_a_claim_denying_it_is_flagged(self):
        c = claim("C1", "The valve was sealed during the event")
        truth = labelled({c["text"]: [("G13", "opposite")]})
        out = sat.score(report([c], [assess("C1", "m8", SEEPAGE, "supports")]), truth)
        self.assertEqual(out["supports_found"], 0)
        self.assertEqual(out["supports_on_denying_claims"][0]["claims"], ["C1"])
        self.assertFalse(out["node_matches"]["G13"]["covered"])

    def test_unlabelled_claims_fall_back_to_word_overlap(self):
        c = claim("C1", "Hydraulic isolation valve has slow bleed through")
        out = sat.score(report([c], []), labelled({}))
        self.assertTrue(out["node_matches"]["G13"]["covered"])
        self.assertEqual(out["claim_matching"], {"word_overlap": 1})


class OffChartClaims(unittest.TestCase):
    def test_each_off_chart_claim_is_sorted_by_what_backs_it(self):
        rows = [claim("C1", "Shift handover was verbal"), claim("C2", "Scaffold tag was current"),
                claim("C3", "Crane was parked nearby")]
        rows[0]["provenance"] = ["m3"]
        rows[1]["provenance"] = ["m3"]
        out = sat.score(report(rows, [assess("C1", "m3", "handover note", "supports")]), TRUTH)
        self.assertEqual((out["off_chart_with_support"], out["off_chart_citing_only"],
                          out["off_chart_no_source"]), (1, 1, 1))


EDGE_TRUTH = {**TRUTH, "chart": {**TRUTH["chart"], "edges_effect_caused_by": [["G00", ["G13"]]]}}
VALVE = "Hydraulic isolation valve has slow bleed through"


def link(source, target):
    return {"link_id": f"{source}->{target}", "source_claim_ids": [source], "target_claim_id": target,
            "status": "candidate"}


class ChartEdges(unittest.TestCase):
    def score_links(self, claims, links):
        rep = report(claims, [])
        rep["board"]["causal_links"] = links
        return sat.score(rep, EDGE_TRUTH)

    def test_direct_link_from_cause_to_effect_is_counted(self):
        out = self.score_links([claim("C1", VALVE)], [link("C1", "ROOT")])
        self.assertEqual((out["edges_total"], out["edges_linked_directly"], out["edges_linked_reversed"]), (1, 1, 0))
        self.assertEqual(out["links_by_status"], {"candidate": 1})

    def test_chain_through_an_off_chart_claim_counts_as_indirect_only(self):
        out = self.score_links([claim("C1", VALVE), claim("C2", "Yoke lowered slowly")],
                               [link("C1", "C2"), link("C2", "ROOT")])
        self.assertEqual((out["edges_linked_directly"], out["edges_linked_via_other_claims"]), (0, 1))

    def test_link_pointing_the_wrong_way_is_reported_as_reversed(self):
        out = self.score_links([claim("C1", VALVE)], [link("ROOT", "C1")])
        self.assertEqual((out["edges_linked_directly"], out["edges_linked_reversed"]), (0, 1))

    def test_missing_end_means_the_edge_cannot_be_linked(self):
        out = self.score_links([], [])
        self.assertEqual((out["edges_both_ends_on_board"], out["edges_linked_directly"]), (0, 0))


class UnresolvedAndTraps(unittest.TestCase):
    def test_filling_in_a_node_the_packet_cannot_evidence_is_flagged(self):
        c = claim("C1", "Isolation valves are not routinely inspected but replaced when found defective")
        out = sat.score(report([c], [assess("C1", "m8", "some sentence about valves", "supports")]), TRUTH)
        self.assertEqual(out["unresolved_nodes_wrongly_supported"], ["G14"])

    def test_leaving_that_node_unsupported_is_fine(self):
        c = claim("C1", "Isolation valves are not routinely inspected but replaced when found defective")
        out = sat.score(report([c], [assess("C1", "m8", "some sentence about valves", "neutral")]), TRUTH)
        self.assertEqual(out["unresolved_nodes_wrongly_supported"], [])

    def test_recap_counted_alongside_its_source_is_flagged(self):
        c = claim("C1", "Hydraulic isolation valve has slow bleed through")
        rows = [assess("C1", "m8", SEEPAGE, "supports"), assess("C1", "m16", "found seepage", "supports")]
        out = sat.score(report([c], rows), TRUTH)
        self.assertTrue(out["traps"]["E16_supports_valve_claim"])
        self.assertTrue(out["traps"]["E16_double_counted_with_E08"])

    def test_replacement_configuration_used_for_original_keeper_is_flagged(self):
        c = claim("C1", "Only one keeper installed")
        out = sat.score(report([c], [assess("C1", "m13", "An additional keeper was welded", "supports")]), TRUTH)
        self.assertEqual(out["traps"]["E13_supports_original_keeper_claim"], ["C1"])

    def test_critical_documents_reported(self):
        out = sat.score(report([claim("C1", "x")], [assess("C1", "m3", "text", "neutral")]), TRUTH)
        self.assertTrue(out["critical_docs_reached"]["E03"])
        self.assertFalse(out["critical_docs_reached"]["E10"])


class RealGroundTruthFiles(unittest.TestCase):
    def test_confirmed_files_load_and_score_an_empty_run(self):
        truth = sat.load_truth()
        out = sat.score({"board": {}}, truth)
        self.assertEqual(out["nodes_total"], 22)
        self.assertEqual(out["nodes_covered"], 0)
        self.assertGreater(out["key_sentences_total"], 10)
        self.assertEqual((out["expected_supports"], out["edges_total"]), (14, 22))


if __name__ == "__main__":
    unittest.main()

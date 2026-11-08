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
        out = sat.score(report([claim("C1", "valve seepage")],
                               [assess("C1", "m8", SEEPAGE.rstrip("."), "supports")]), TRUTH)
        self.assertEqual(out["key_sentences_assessed"], 1)
        self.assertEqual(out["supports_found"], 1)

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


if __name__ == "__main__":
    unittest.main()

"""Lexical retrieval: filler words do not match, a passage must share enough content words,
rare words outweigh common ones, and a passage inherits its heading's words."""
from __future__ import annotations

import unittest

from ewv3 import InMemoryRetriever, SourceUnit
from ewv3.retrieval import content_terms


def src(text, sid="D1"):
    return SourceUnit(sid, "v1", f"{sid}:r", sid, text)


def search(query, *docs, **kw):
    sources = tuple(src(t, f"D{i + 1}") for i, t in enumerate(docs))
    return InMemoryRetriever(**kw).search(query, channel="lexical", sources=sources, limit=10)


class Terms(unittest.TestCase):
    def test_filler_and_request_framing_are_dropped(self):
        self.assertEqual(content_terms("Please provide the records of the valve"), frozenset({"valve"}))

    def test_plurals_and_endings_are_stemmed(self):
        self.assertEqual(content_terms("keepers"), content_terms("keeper"))
        self.assertEqual(content_terms("readings"), content_terms("reading"))
        self.assertEqual(content_terms("disengaged"), content_terms("disengage".rstrip("e") + "ed"))

    def test_identifiers_with_digits_are_kept_whole_and_as_parts(self):
        terms = content_terms("valve IV-RB3-17")
        self.assertIn("iv-rb3-17", terms)
        self.assertIn("rb3", terms)


class Matching(unittest.TestCase):
    def test_a_query_of_only_filler_returns_nothing(self):
        self.assertEqual(search("was it the during the", "It was the case during the outage."), ())

    def test_filler_overlap_alone_does_not_match(self):
        hits = search("the hydraulic pressure during the outage",
                      "The outline of the plan was drawn up during the week.")
        self.assertEqual(hits, ())

    def test_one_shared_content_word_is_not_enough_for_a_multiword_query(self):
        self.assertEqual(search("keeper plate engaged", "The plate was cleaned."), ())

    def test_a_single_word_query_can_match_on_one_word(self):
        self.assertEqual(len(search("keeper", "The keeper was bolted.")), 1)

    def test_min_shared_is_configurable(self):
        text = "The plate was cleaned."
        self.assertEqual(len(search("keeper plate engaged", text, min_shared=1)), 1)

    def test_stemmed_forms_match(self):
        hits = search("keepers disengaged", "The keeper disengaged. The weather was fine.")
        self.assertEqual([h.excerpt for h in hits], ["The keeper disengaged."])

    def test_rarer_words_rank_higher_than_common_ones(self):
        docs = ["The valve was shut. The valve was inspected. The valve was fine.",
                "The valve showed seepage."]
        hits = search("valve seepage", *docs)
        self.assertIn("seepage", hits[0].excerpt)

    def test_identifier_matches_itself(self):
        hits = search("local valve IV-RB3-17", "Tag IV-RB3-17 feeds the lifting circuit.", "Valve 22 is separate.")
        self.assertEqual(hits[0].source_id, "D1")

    def test_ranked_by_weighted_coverage_and_deterministic(self):
        docs = ["Keeper plate bolted to link arm.", "Keeper noted."]
        first = search("keeper plate link arm", *docs)
        self.assertEqual(first, search("keeper plate link arm", *docs))
        self.assertEqual(first[0].source_id, "D1")

    def test_passage_inherits_its_heading_words(self):
        doc = ("# Valve workshop examination record\n\n## Bench observation\n"
               "Fluid seepage was observed at the closed handle position.")
        hits = search("valve seepage observed", doc)
        self.assertEqual([h.excerpt for h in hits][-1], "Fluid seepage was observed at the closed handle position.")

    def test_inherited_words_alone_do_not_make_a_match(self):
        doc = "# Valve workshop examination record\n\nThe weather was fine."
        self.assertEqual([h for h in search("valve examination", doc) if "weather" in h.excerpt], [])

    def test_exact_channel_is_unchanged(self):
        hits = InMemoryRetriever().search("single keeper", channel="exact",
                                          sources=(src("There is a single keeper on each arm."),), limit=3)
        self.assertEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main()

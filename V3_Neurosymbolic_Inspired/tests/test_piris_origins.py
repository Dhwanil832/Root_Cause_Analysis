"""Intake changes for v0.5 Step 1: origin records for documents prepared from others."""
from __future__ import annotations

import unittest

from cferp.status import source_of
from piris import IncomingItem, IntakeEngine, InMemoryMaterialIndexer, ParserRouter, resolve_origins
from piris.origins import origin_statements

from test_piris import assignment

WORKSHOP = ("Workshop tag VAL-17 is linked to local valve IV-RB3-17 on the removal docket. "
            "Seepage was seen with the handle at closed.")
RECAP = ("Prepared for the morning briefing from the hydraulic maintenance summary supplied on Day +3.\n"
         "The valve workshop found seepage with the isolation handle at closed.\n"
         "Prepared from workshop record VAL-17. No additional examination was conducted.")
OTHER = "Outage switching sheet UT-81. The B hydraulic supply was isolated at 11:10."


class Statements(unittest.TestCase):
    def test_the_origin_sentence_is_kept_word_for_word_with_its_offset(self):
        rows = origin_statements("E16", RECAP)
        named = [r for r in rows if r.identifiers]
        self.assertEqual(named[0].quote, "Prepared from workshop record VAL-17.")
        self.assertEqual(RECAP[named[0].start_offset:][:len(named[0].quote)], named[0].quote)
        self.assertEqual(named[0].identifiers, ("VAL-17",))

    def test_an_origin_that_names_no_identifier_is_reported_not_matched(self):
        result = resolve_origins({"E08": WORKSHOP, "E16": RECAP})
        self.assertEqual(len(result.unnamed), 1)
        self.assertIn("morning briefing", result.unnamed[0].quote)

    def test_a_document_that_only_mentions_a_code_has_no_origin(self):
        self.assertEqual(origin_statements("E08", WORKSHOP), ())


class Matching(unittest.TestCase):
    def test_the_identifier_is_matched_to_the_document_that_carries_it(self):
        result = resolve_origins({"E08": WORKSHOP, "E16": RECAP, "E10": OTHER})
        self.assertEqual(result.origins, {"E16": "E08"})
        self.assertEqual(source_of("E16", result.origins), "E08")

    def test_a_longer_code_containing_the_identifier_does_not_match(self):
        result = resolve_origins({"X": "Valve IV-RB3-17 and record VAL-170.", "E16": RECAP})
        self.assertEqual(result.origins, {})
        self.assertEqual(result.unresolved, (("E16", "VAL-17"),))

    def test_two_documents_carrying_it_are_ambiguous_and_not_matched(self):
        result = resolve_origins({"A": WORKSHOP, "B": "Bench sheet for VAL-17.", "E16": RECAP})
        self.assertEqual(result.origins, {})
        self.assertEqual(result.ambiguous, (("E16", "VAL-17", ("A", "B")),))

    def test_two_recaps_of_the_same_record_do_not_match_each_other(self):
        result = resolve_origins({"E08": WORKSHOP, "E16": RECAP, "E17": "Copied from record VAL-17 for the file."})
        self.assertEqual(result.origins, {"E16": "E08", "E17": "E08"})


class ArrivalOrder(unittest.TestCase):
    def setUp(self):
        self.engine = IntakeEngine(parser=ParserRouter(), indexer=InMemoryMaterialIndexer())

    def submit(self, sub, item_id, text):
        result = self.engine.run(assignment(sub, [IncomingItem.text(item_id, text, filename=f"{item_id}.md")]))
        return result.event.item_records[0].material_id

    def test_a_recap_that_arrives_first_is_matched_once_its_original_arrives(self):
        recap = self.submit("s1", "E16", RECAP)
        self.assertEqual(self.engine.case_origins("case-1").unresolved, ((recap, "VAL-17"),))
        workshop = self.submit("s2", "E08", WORKSHOP)
        self.assertEqual(self.engine.case_origins("case-1").origins, {recap: workshop})

    def test_either_order_gives_the_same_map(self):
        workshop = self.submit("s1", "E08", WORKSHOP)
        recap = self.submit("s2", "E16", RECAP)
        self.assertEqual(self.engine.case_origins("case-1").origins, {recap: workshop})


if __name__ == "__main__":
    unittest.main()

"""Document structure, structured search, document narrowing, the graded reader,
passage context for the Assessor, and the vision flag at intake."""
from __future__ import annotations

import unittest

import docstruct
from ewv3 import (AnswerSlot, CorpusManifest, EvidenceAssignment, EvidenceWorkerEngine,
                  InformationNeed, InMemoryRetriever, SourceUnit)
from ewv3.config import WorkerConfig
from ewv3.retrieval import BM25Retriever, NarrowingRetriever, default_retriever, passage_units
from piris.components import NEEDS_VISION, ParserRouter, StructuredTextParser
from piris.contracts import IncomingItem

DOC = """# Valve workshop examination record

**SYNTHETIC RESEARCH FIXTURE. Not an authentic company record.**

Record: E08 | Case: FCB-01 | Asset: RB-3
Record owner: Hydraulic maintenance
Coverage: Day +3; tagged valve removed

## Bench observation
With the handle at closed, fluid seepage was observed. No calibrated leakage-rate trace accompanies this record.

## Readings
Time | Yoke marker y | Carrier marker y
11:03 | 210 | 190
13:02:58 | 289 | 190
"""


def item(text=DOC, media_type="text/markdown", item_id="E08"):
    return IncomingItem(item_id, text.encode("utf-8"), media_type=media_type, filename=f"{item_id}.md",
                        declared_kind="case_material")


class Structure(unittest.TestCase):
    def setUp(self):
        self.s = docstruct.parse(DOC)

    def test_every_passage_is_an_exact_span_of_the_original(self):
        for p in self.s.passages:
            self.assertEqual(DOC[p.start:p.end], p.text)

    def test_title_details_and_notice_are_recognised(self):
        self.assertEqual(self.s.title, "Valve workshop examination record")
        self.assertEqual(len(self.s.details), 3)
        self.assertIn("notice", [p.kind for p in self.s.passages])

    def test_only_sentences_and_table_rows_are_evidence(self):
        self.assertEqual({p.kind for p in self.s.evidence()}, {"sentence", "table_row"})
        self.assertFalse(any("SYNTHETIC" in p.text or "Record owner" in p.text for p in self.s.evidence()))

    def test_table_rows_keep_their_header(self):
        rows = [p for p in self.s.passages if p.kind == "table_row"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].readable(), "Time: 13:02:58; Yoke marker y: 289; Carrier marker y: 190")

    def test_sentences_know_their_section_and_neighbours(self):
        first = next(p for p in self.s.evidence() if "seepage" in p.text)
        self.assertEqual(first.section, "Bench observation")
        before, after = self.s.neighbours(first)
        self.assertIsNone(before)
        self.assertIn("No calibrated leakage-rate trace", after.text)

    def test_a_details_line_with_pipes_is_not_a_table(self):
        self.assertFalse(any(p.kind.startswith("table") and "Record:" in p.text for p in self.s.passages))


def source(sid, text):
    return SourceUnit(sid, "1", f"{sid}:r", sid, text)


class StructuredSearch(unittest.TestCase):
    def test_hits_carry_reading_context(self):
        hits = InMemoryRetriever().search("valve seepage observed", channel="lexical",
                                          sources=(source("E08", DOC),), limit=5)
        context = hits[0].structural_context
        self.assertEqual(context["section"], "Bench observation")
        self.assertEqual(context["document_title"], "Valve workshop examination record")
        self.assertIn("No calibrated", context["after"])

    def test_a_table_row_is_found_through_its_column_names(self):
        hits = InMemoryRetriever().search("yoke marker carrier marker 13:02:58", channel="lexical",
                                          sources=(source("E08", DOC),), limit=5)
        self.assertTrue(hits[0].excerpt.startswith("13:02:58"))
        self.assertIn("Yoke marker y: 289", hits[0].structural_context["readable_text"])

    def test_notice_and_details_are_never_returned(self):
        hits = BM25Retriever().search("synthetic research fixture record owner hydraulic maintenance",
                                      channel="bm25", sources=(source("E08", DOC),), limit=10)
        self.assertFalse(any("SYNTHETIC" in h.excerpt or "Record owner" in h.excerpt for h in hits))

    def test_passage_units_are_cached_by_content(self):
        self.assertIs(passage_units(DOC), passage_units(DOC))


class Narrowing(unittest.TestCase):
    def test_caps_documents_and_passages_per_document(self):
        long_doc = "## A\n" + " ".join(f"The valve leak was noted in check {i}." for i in range(20))
        others = [source(f"D{i}", f"## A\nThe valve leak appeared once in note {i}.") for i in range(6)]
        retriever = NarrowingRetriever(InMemoryRetriever(), max_documents=3, per_document=2)
        hits = retriever.search("valve leak", channel="lexical", sources=(source("LONG", long_doc), *others),
                                limit=20)
        self.assertLessEqual(len({h.source_id for h in hits}), 3)
        self.assertLessEqual(sum(h.source_id == "LONG" for h in hits), 2)

    def test_default_retriever_serves_exact_and_lexical(self):
        retriever = default_retriever()
        sources = (source("E08", DOC),)
        self.assertTrue(retriever.search("fluid seepage", channel="exact", sources=sources, limit=3))
        self.assertTrue(retriever.search("valve seepage", channel="lexical", sources=sources, limit=3))


class GradingPlanner:
    def __init__(self, grades=None, fail=False, requests=None):
        self.grades, self.fail = grades, fail
        self.requests = requests or {"requests": []}
        self.grade_rows = None
        self.request_slots = None

    def plan_queries(self, assignment):
        return {"queries": [{"slot_id": "s1", "query": "valve seepage closed handle leakage"}]}

    def draft_requests(self, assignment, unresolved_slot_ids, slot_summaries):
        self.request_slots = unresolved_slot_ids
        return self.requests

    def grade_candidates(self, assignment, slot_rows):
        self.grade_rows = slot_rows
        if self.fail:
            raise RuntimeError("model down")
        if callable(self.grades):
            return self.grades(slot_rows)
        return self.grades


def assignment():
    return EvidenceAssignment(
        schema_version="1", assignment_id="a1", work_item_id="w1", event_id="e1", case_id="c",
        case_snapshot_id="c:1", board_version="1", manifest=CorpusManifest("c1", "m1", "r1"),
        needs=(InformationNeed("n1", "The isolation valve let fluid through when closed", (
            AnswerSlot("s1", "Did the closed valve leak?"),)),),
        sources=(source("E08", DOC),))


def grade_by_text(rule):
    def grades(rows):
        return {"grades": [{"candidate_link_id": c["candidate_link_id"], **rule(c["passage"])}
                           for row in rows for c in row["candidates"]]}
    return grades


class Grading(unittest.TestCase):
    def run_with(self, planner, **config):
        engine = EvidenceWorkerEngine(planner, default_retriever(), config=WorkerConfig(**config))
        return engine.run(assignment())

    def test_reader_sees_section_neighbours_and_details(self):
        planner = GradingPlanner(grade_by_text(lambda t: {"grade": 3, "role": "answers"}))
        self.run_with(planner)
        candidate = planner.grade_rows[0]["candidates"][0]
        self.assertEqual(candidate["document"], "Valve workshop examination record")
        self.assertIn("Coverage: Day +3; tagged valve removed", candidate["document_details"])
        self.assertEqual(planner.grade_rows[0]["question"], "Did the closed valve leak?")

    def test_only_grade_two_and_above_reach_the_assessor(self):
        rule = lambda t: ({"grade": 3, "role": "answers"} if "seepage" in t else {"grade": 1, "role": "background"})
        result = self.run_with(GradingPlanner(grade_by_text(rule)))
        links = result.slot_results[0].candidate_links
        self.assertTrue(links)
        self.assertTrue(all("seepage" in link.exact_text for link in links))
        self.assertEqual(links[0].structural_context["reader_grade"], 3)

    def test_all_candidates_rejected_is_a_coverage_finding_not_evidence(self):
        result = self.run_with(GradingPlanner(grade_by_text(lambda t: {"grade": 0, "role": "unrelated"})))
        slot = result.slot_results[0]
        self.assertEqual(slot.candidate_links, ())
        self.assertIn("judged not relevant", slot.reason)
        self.assertEqual(result.status, "no_candidate_in_scope")

    def test_a_failed_grading_call_keeps_retrieval_order(self):
        result = self.run_with(GradingPlanner(fail=True), max_assessed_per_slot=2)
        self.assertEqual(len(result.slot_results[0].candidate_links), 2)
        self.assertTrue(any("grading unavailable" in d for d in result.diagnostics))

    def test_unknown_ids_and_bad_values_are_ignored(self):
        def grades(rows):
            real = rows[0]["candidates"][0]["candidate_link_id"]
            return {"grades": [{"candidate_link_id": "made-up", "grade": 3, "role": "answers"},
                               {"candidate_link_id": real, "grade": 7, "role": "answers"}]}
        result = self.run_with(GradingPlanner(grades))
        self.assertTrue(any("ignored" in d for d in result.diagnostics))

    def test_an_answered_slot_is_not_requested_again(self):
        planner = GradingPlanner(grade_by_text(
            lambda t: {"grade": 3, "role": "answers"} if "seepage" in t else {"grade": 0, "role": "unrelated"}))
        self.run_with(planner)
        self.assertIsNone(planner.request_slots)   # no requestable slot left, so no request call

    def test_a_limiting_passage_still_allows_a_request(self):
        planner = GradingPlanner(grade_by_text(lambda t: {"grade": 3, "role": "limits"}))
        self.run_with(planner)
        self.assertEqual(planner.request_slots, ("s1",))

    def test_grading_can_be_switched_off(self):
        planner = GradingPlanner(grade_by_text(lambda t: {"grade": 0, "role": "unrelated"}))
        result = self.run_with(planner, grade_candidates=False)
        self.assertIsNone(planner.grade_rows)
        self.assertTrue(result.slot_results[0].candidate_links)


class Ranking(unittest.TestCase):
    def test_candidates_are_ranked_across_queries_before_the_cap(self):
        weak = " ".join(f"Valve check {i} done." for i in range(10))
        doc = f"## Log\n{weak} The closed valve showed fluid seepage at the bench."

        class TwoQueries(GradingPlanner):
            def plan_queries(self, assignment):
                return {"queries": [{"slot_id": "s1", "query": "valve check logged daily"},
                                    {"slot_id": "s1", "query": "closed valve fluid seepage bench"}]}
        a = EvidenceAssignment(
            schema_version="1", assignment_id="a1", work_item_id="w1", event_id="e1", case_id="c",
            case_snapshot_id="c:1", board_version="1", manifest=CorpusManifest("c1", "m1", "r1"),
            needs=(InformationNeed("n1", "valve check", (AnswerSlot("s1", "valve check logged daily"),)),),
            sources=(source("LOG", doc),))
        engine = EvidenceWorkerEngine(TwoQueries(), InMemoryRetriever(),
                                      config=WorkerConfig(max_links_for_grading=1, grade_candidates=False))
        links = engine.run(a).slot_results[0].candidate_links
        self.assertIn("seepage", links[0].exact_text)


class Intake(unittest.TestCase):
    def test_text_keeps_original_and_gains_passage_segments(self):
        result = StructuredTextParser().parse(item())
        self.assertEqual(result.text, DOC)
        kinds = {seg.location.locator.split(":")[0] for seg in result.segments}
        self.assertTrue({"sentence", "table_row", "detail"} <= kinds)
        row = next(seg for seg in result.segments if seg.location.locator.startswith("table_row"))
        self.assertEqual(row.location.table, "Time | Yoke marker y | Carrier marker y")
        self.assertEqual(DOC[row.location.start_offset:row.location.end_offset], row.text)

    def test_router_uses_the_structured_parser_for_text(self):
        self.assertEqual(ParserRouter().parse(item()).parser_name, "StructuredTextParser")

    def test_images_and_drawings_are_flagged_for_a_vision_model(self):
        for media in ("image/png", "application/pdf", "image/vnd.dwg"):
            result = ParserRouter().parse(item(media_type=media))
            self.assertEqual(result.status, "unsupported")
            self.assertTrue(any(w.startswith(NEEDS_VISION) for w in result.warnings), media)

    def test_text_with_an_embedded_image_is_flagged(self):
        result = ParserRouter().parse(item(DOC + "\n## Figure\n![layout](layout.png)\n"))
        self.assertTrue(any(w.startswith(NEEDS_VISION) for w in result.warnings))

    def test_plain_text_is_not_flagged(self):
        self.assertFalse(ParserRouter().parse(item()).warnings)


class AssessorContext(unittest.TestCase):
    def test_passage_context_reaches_the_hera_material(self):
        from cferp.integration import _passage_context
        context = _passage_context({"section": "Bench observation", "after": "No trace.", "reader_grade": 3,
                                    "source_map": ["big"], "parser_name": "x"})
        self.assertEqual(context, {"section": "Bench observation", "after": "No trace.", "reader_grade": 3})


if __name__ == "__main__":
    unittest.main()

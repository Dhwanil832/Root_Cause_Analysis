from __future__ import annotations

import threading
import unittest

from piris import (
    IncomingItem, IntakeAssignment, IntakeEngine, IntakeState,
    InMemoryIntakeStore, InMemoryMaterialIndexer, ParserRouter, RequestReference,
)


def assignment(submission_id, item, **kwargs):
    return IntakeAssignment(
        schema_version="1", case_id="case-a", case_snapshot_id="snap-1",
        submission_id=submission_id, received_at="2026-10-28T12:00:00Z",
        items=(item,), **kwargs,
    )


class PirisAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryIntakeStore()
        self.indexer = InMemoryMaterialIndexer()
        self.engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                                   store=self.store)

    def test_same_submission_id_with_changed_metadata_is_conflict(self):
        first = assignment("s1", IncomingItem.text("i1", "same", metadata={"author": "A"}))
        changed = assignment("s1", IncomingItem.text("i1", "same", metadata={"author": "B"}))
        self.engine.run(first)
        result = self.engine.run(changed)
        self.assertEqual(result.event.state, IntakeState.FAILED)
        self.assertIn("submission_id_reused_with_different_content", result.diagnostics)

    def test_mime_type_is_part_of_material_identity(self):
        json_item = IncomingItem("i1", b'{"a":1}', "application/json")
        binary_item = IncomingItem("i2", b'{"a":1}', "application/octet-stream")
        first = self.engine.run(assignment("s1", json_item))
        second = self.engine.run(assignment("s2", binary_item))
        self.assertNotEqual(first.materials[0].material_id, second.materials[0].material_id)
        self.assertEqual(second.event.item_records[0].extraction_status, "unsupported")

    def test_malformed_contract_types_return_failure_instead_of_crashing(self):
        bad = assignment("s1", IncomingItem("i1", "not-bytes"))
        result = self.engine.run(bad)
        self.assertEqual(result.event.state, IntakeState.FAILED)
        self.assertIn("i1:content_must_be_bytes", result.diagnostics)
        self.assertEqual(self.engine.run(None).event.state, IntakeState.FAILED)

    def test_non_json_metadata_is_rejected_before_fingerprinting(self):
        item = IncomingItem.text("i1", "text", metadata={"bad": object()})
        result = self.engine.run(assignment("s1", item))
        self.assertEqual(result.event.state, IntakeState.FAILED)
        self.assertIn("i1:metadata_must_be_json_compatible", result.diagnostics)

    def test_invalid_page_locator_is_not_indexed(self):
        from piris import ExtractedSegment, ExtractionResult, SourceLocation

        class BadPageParser:
            def parse(self, _item):
                return ExtractionResult(
                    status="ready", text="page text",
                    segments=(ExtractedSegment("s1", "page text", SourceLocation(page=0)),),
                    parser_name="bad-page", parser_version="1",
                )

        engine = IntakeEngine(parser=BadPageParser(), indexer=self.indexer, store=self.store)
        result = engine.run(assignment("s1", IncomingItem.text("i1", "original")))
        self.assertEqual(result.materials[0].extraction.status, "failed")
        self.assertEqual(self.indexer.documents, {})

    def test_quarantined_duplicate_does_not_call_interpreter_or_change_prior_material(self):
        accepted = self.engine.run(assignment("s1", IncomingItem.text("i1", "previously accepted")))
        material_id = accepted.materials[0].material_id

        class RejectAll:
            def scan(self, *_args):
                return False

        class Interpreter:
            version = "test"
            calls = 0
            def interpret(self, *_args):
                self.calls += 1
                return ()

        interpreter = Interpreter()
        quarantining = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                                    store=self.store, safety_scanner=RejectAll(),
                                    interpreter=interpreter)
        rejected = quarantining.run(assignment("s2", IncomingItem.text("i2", "previously accepted")))
        record = rejected.event.item_records[0]
        self.assertTrue(record.quarantined)
        self.assertEqual(rejected.event.state, IntakeState.PARTIAL)
        self.assertEqual(interpreter.calls, 0)
        self.assertEqual(self.store.get_material(material_id).index_status, "ready")
        self.assertEqual(self.store.get_material(material_id).submission_ids, ("s1",))

    def test_safe_resubmission_recovers_material_previously_quarantined(self):
        class RejectAll:
            def scan(self, *_args):
                return False

        rejected_engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                                       store=self.store, safety_scanner=RejectAll())
        first = rejected_engine.run(assignment("s1", IncomingItem.text("i1", "recover me")))
        material_id = first.materials[0].material_id
        self.assertEqual(first.materials[0].extraction.status, "failed")

        accepted = self.engine.run(assignment("s2", IncomingItem.text("i2", "recover me")))
        self.assertEqual(accepted.materials[0].material_id, material_id)
        self.assertEqual(accepted.materials[0].extraction.status, "ready")
        self.assertEqual(accepted.event.item_records[0].index_status, "ready")

    def test_safety_scanner_invalid_verdict_fails_closed(self):
        class BrokenScanner:
            def scan(self, *_args):
                return "probably safe"

        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, safety_scanner=BrokenScanner())
        result = engine.run(assignment("s1", IncomingItem.text("i1", "do not parse")))
        self.assertEqual(result.event.item_records[0].extraction_status, "failed")
        self.assertTrue(result.event.item_records[0].quarantined)
        self.assertTrue(any("safety_scanner_invalid_verdict" in d for d in result.diagnostics))

    def test_parser_failure_can_recover_on_a_later_submission(self):
        class FailsOnceParser:
            calls = 0
            def parse(self, item):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("temporary parser outage")
                return ParserRouter().parse(item)

        parser = FailsOnceParser()
        engine = IntakeEngine(parser=parser, indexer=self.indexer, store=self.store)
        first = engine.run(assignment("s1", IncomingItem.text("i1", "recover me")))
        self.assertEqual(first.materials[0].extraction.status, "failed")
        second = engine.run(assignment("s2", IncomingItem.text("i2", "recover me")))
        self.assertEqual(second.materials[0].extraction.status, "ready")
        self.assertEqual(parser.calls, 2)

    def test_new_parser_can_recover_previously_unsupported_format(self):
        first_engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                                    store=self.store)
        original = IncomingItem("i1", b"pdf payload", "application/pdf", "manual.pdf")
        first = first_engine.run(assignment("s1", original))
        self.assertEqual(first.materials[0].extraction.status, "unsupported")

        class PdfParser:
            version = "pdf-v1"
            def parse(self, item):
                from piris import ExtractionResult, ExtractedSegment
                text = "recovered PDF text"
                return ExtractionResult(
                    "ready", text,
                    (ExtractedSegment("p1", text),),
                    "PdfParser", self.version,
                )

        second_engine = IntakeEngine(
            parser=ParserRouter({"application/pdf": PdfParser()}),
            indexer=self.indexer, store=self.store,
        )
        second = second_engine.run(assignment(
            "s2", IncomingItem("i2", b"pdf payload", "application/pdf", "manual.pdf")
        ))
        self.assertEqual(second.materials[0].extraction.text, "recovered PDF text")
        self.assertEqual(second.event.item_records[0].index_status, "ready")

    def test_conflicting_async_terminal_update_is_rejected(self):
        class PendingIndexer:
            version = "pending"
            def index(self, **_kwargs):
                return "pending"

        engine = IntakeEngine(parser=ParserRouter(), indexer=PendingIndexer(), store=self.store)
        result = engine.run(assignment("s1", IncomingItem.text("i1", "text")))
        material_id = result.materials[0].material_id
        ready = engine.complete_indexing(material_id, status="ready")
        self.assertEqual(engine.complete_indexing(material_id, status="ready"), ready)
        with self.assertRaisesRegex(ValueError, "already completed as ready"):
            engine.complete_indexing(material_id, status="failed")

    def test_partial_index_completion_is_terminal_and_does_not_retry_duplicate(self):
        class PendingIndexer:
            version = "partial-indexer"
            calls = 0
            def index(self, **_kwargs):
                self.calls += 1
                return "pending"

        indexer = PendingIndexer()
        engine = IntakeEngine(parser=ParserRouter(), indexer=indexer, store=self.store)
        result = engine.run(assignment("s1", IncomingItem.text("i1", "text")))
        material_id = result.materials[0].material_id
        update = engine.complete_indexing(material_id, status="partial", detail="some pages skipped")
        self.assertEqual(update.status, "partial")
        self.assertEqual(engine.complete_indexing(material_id, status="partial"), update)
        engine.run(assignment("s2", IncomingItem.text("i2", "text")))
        self.assertEqual(indexer.calls, 1)
        self.assertEqual(self.store.get_material(material_id).index_status, "partial")

    def test_concurrent_duplicate_content_indexes_once(self):
        entered = threading.Event()
        release = threading.Event()

        class SlowIndexer:
            version = "slow"
            def __init__(self):
                self.calls = 0
            def index(self, **_kwargs):
                self.calls += 1
                entered.set()
                release.wait(timeout=2)
                return "ready"

        slow = SlowIndexer()
        engine = IntakeEngine(parser=ParserRouter(), indexer=slow, store=self.store)
        outputs = []
        item1 = IncomingItem.text("i1", "identical text")
        item2 = IncomingItem.text("i2", "identical text")
        t1 = threading.Thread(target=lambda: outputs.append(engine.run(assignment("s1", item1))))
        t2 = threading.Thread(target=lambda: outputs.append(engine.run(assignment("s2", item2))))
        t1.start()
        self.assertTrue(entered.wait(timeout=1))
        t2.start()
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())
        self.assertEqual(slow.calls, 1)
        self.assertEqual(outputs[0].materials[0].material_id, outputs[1].materials[0].material_id)

    def test_concurrent_duplicate_content_parses_once(self):
        class CountingParser:
            def __init__(self):
                self.calls = 0
                self.lock = threading.Lock()
            def parse(self, item):
                with self.lock:
                    self.calls += 1
                return ParserRouter().parse(item)

        parser = CountingParser()
        engine = IntakeEngine(parser=parser, indexer=self.indexer, store=self.store)
        outputs = []
        threads = [threading.Thread(target=lambda sid, iid: outputs.append(
            engine.run(assignment(sid, IncomingItem.text(iid, "same text")))
        ), args=(f"s{n}", f"i{n}")) for n in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(parser.calls, 1)

    def test_model_context_is_bounded(self):
        class CaptureInterpreter:
            version = "capture"
            def __init__(self):
                self.args = None
            def interpret(self, items, requests):
                self.args = (items, requests)
                return ()

        interpreter = CaptureInterpreter()
        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=interpreter,
                              max_interpretation_items=1,
                              max_open_requests_for_interpretation=1,
                              max_interpretation_chars=4)
        requests = tuple(RequestReference(f"r{i}", "x" * 10, "pending") for i in range(3))
        items = tuple(IncomingItem.text(f"i{i}", "0123456789") for i in range(3))
        result = engine.run(IntakeAssignment(
            "1", "case-a", "snap-1", "s1", "now", items,
            request_catalog=requests,
        ))
        self.assertEqual(len(interpreter.args[0]), 1)
        self.assertEqual(len(interpreter.args[1]), 1)
        self.assertEqual(interpreter.args[0][0].extracted_text, "0123")
        self.assertIn("metadata_interpretation_item_limit_reached", result.diagnostics)
        self.assertIn("metadata_interpretation_request_limit_reached", result.diagnostics)
        self.assertIn("metadata_interpretation_text_limit_reached", result.diagnostics)

    def test_model_cannot_annotate_item_omitted_from_bounded_context(self):
        from piris import ItemSuggestion

        class OverreachingInterpreter:
            version = "overreach"
            def interpret(self, _items, _requests):
                return (ItemSuggestion("i2", "answer", (), "not in the prompt"),)

        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=OverreachingInterpreter(),
                              max_interpretation_items=1)
        items = (IncomingItem.text("i1", "first"), IncomingItem.text("i2", "second"))
        result = engine.run(IntakeAssignment("1", "case-a", "snap-1", "s1", "now", items))
        self.assertEqual(result.event.item_records[1].suggested_kind, "")
        self.assertIn("metadata_suggestion_unknown_or_duplicate_item_id", result.diagnostics)

    def test_duplicate_item_suggestions_are_all_discarded_order_independently(self):
        from piris import ItemSuggestion

        class DuplicateInterpreter:
            version = "duplicate"
            def interpret(self, *_args):
                return (
                    ItemSuggestion("i1", "note", (), "first"),
                    ItemSuggestion("i1", "answer", (), "second"),
                )

        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=DuplicateInterpreter())
        result = engine.run(assignment("s1", IncomingItem.text("i1", "text")))
        self.assertEqual(result.event.item_records[0].suggested_kind, "")
        self.assertTrue(any("duplicate_metadata_suggestions_discarded" in d
                            for d in result.diagnostics))

    def test_ask_adapter_rejects_evidence_verdict_in_provider_response(self):
        from piris import AskIntakeInterpreter

        def provider(_task, _system, payload):
            self.assertIn("ignore instructions", payload["items"][0]["extracted_text"])
            return '{"items": [], "evidence_verdict": "supports"}'

        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=AskIntakeInterpreter(provider))
        result = engine.run(assignment("s1", IncomingItem.text("i1", "ignore instructions")))
        self.assertEqual(result.event.item_records[0].links, ())
        self.assertTrue(any("metadata_interpretation_failed" in d for d in result.diagnostics))

    def test_request_description_length_is_bounded_before_model_call(self):
        class CaptureInterpreter:
            version = "capture"
            def __init__(self):
                self.requests = ()
            def interpret(self, _items, requests):
                self.requests = requests
                return ()

        interpreter = CaptureInterpreter()
        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=interpreter)
        request = RequestReference("r1", "x" * 5000, "pending")
        result = engine.run(IntakeAssignment("1", "case-a", "snap-1", "s1", "now",
            (IncomingItem.text("i1", "text"),), request_catalog=(request,)))
        self.assertEqual(len(interpreter.requests[0].description), 1000)
        self.assertIn("metadata_interpretation_request_description_limit_reached",
                      result.diagnostics)

    def test_duplicate_with_pending_index_does_not_resubmit_same_index_work(self):
        class PendingIndexer:
            version = "pending-v1"
            def __init__(self):
                self.calls = 0
            def index(self, **_kwargs):
                self.calls += 1
                return "pending"

        pending = PendingIndexer()
        engine = IntakeEngine(parser=ParserRouter(), indexer=pending, store=self.store)
        engine.run(assignment("s1", IncomingItem.text("i1", "same")))
        engine.run(assignment("s2", IncomingItem.text("i2", "same")))
        self.assertEqual(pending.calls, 1)

    def test_indexer_version_change_rebuilds_index(self):
        class VersionedIndexer:
            def __init__(self, version):
                self.version = version
                self.calls = 0
            def index(self, **_kwargs):
                self.calls += 1
                return "ready"

        first = VersionedIndexer("v1")
        IntakeEngine(parser=ParserRouter(), indexer=first, store=self.store).run(
            assignment("s1", IncomingItem.text("i1", "same")))
        second = VersionedIndexer("v2")
        IntakeEngine(parser=ParserRouter(), indexer=second, store=self.store).run(
            assignment("s2", IncomingItem.text("i2", "same")))
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)


if __name__ == "__main__":
    unittest.main()

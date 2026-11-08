from __future__ import annotations

import unittest

from piris import (
    AskIntakeInterpreter, ExtractedSegment, ExtractionResult, IncomingItem, IntakeAssignment,
    IntakeEngine, IntakeState, InMemoryIntakeStore, InMemoryMaterialIndexer,
    ItemSuggestion, ParserRouter, RequestReference, SourceLocation,
)


def assignment(submission_id, items, *, requests=(), received="2026-10-28T12:00:00Z"):
    return IntakeAssignment(
        schema_version="1", case_id="case-1", case_snapshot_id="case-1:r2",
        submission_id=submission_id, received_at=received, sender_id="human-1",
        items=tuple(items), request_catalog=tuple(requests),
    )


class StaticInterpreter:
    version = "fixture-1"

    def __init__(self, results):
        self.results = tuple(results)
        self.calls = []

    def interpret(self, items, requests):
        self.calls.append((items, requests))
        return self.results


class BadSpanParser:
    def parse(self, item):
        return ExtractionResult(
            status="ready", text="Original words",
            segments=(ExtractedSegment(
                "bad", "different words",
                SourceLocation(start_offset=0, end_offset=14, page=1),
            ),), parser_name="bad", parser_version="1",
        )


class PendingIndexer:
    version = "pending-indexer-1"

    def index(self, **kwargs):
        return "pending"


class FailingIndexer:
    version = "broken-indexer-1"

    def index(self, **kwargs):
        raise RuntimeError("index offline")


class PirisTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryIntakeStore()
        self.indexer = InMemoryMaterialIndexer()
        self.engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                                   store=self.store)

    def test_text_submission_registers_and_indexes_with_source_offsets(self):
        text = "Maintenance log: pressure loss was reported."
        result = self.engine.run(assignment("sub-1", [IncomingItem.text(
            "item-1", text, filename="log.txt", declared_kind="maintenance_log")]))
        self.assertEqual(result.event.state, IntakeState.READY)
        record = result.event.item_records[0]
        self.assertEqual(record.extraction_status, "ready")
        self.assertEqual(record.index_status, "ready")
        self.assertEqual(result.materials[0].extraction.text, text)
        self.assertEqual(result.materials[0].extraction.segments[0].location.start_offset, 0)
        self.assertEqual(result.materials[0].extraction.segments[0].location.end_offset, len(text))
        self.assertEqual(result.materials[0].submission_ids, ("sub-1",))

    def test_retry_same_submission_is_idempotent_but_new_duplicate_arrival_is_preserved(self):
        item = IncomingItem.text("i1", "same note", declared_kind="note")
        first_assignment = assignment("sub-1", [item])
        first = self.engine.run(first_assignment)
        retry = self.engine.run(first_assignment)
        self.assertIs(retry, first)
        delayed_retry = self.engine.run(assignment("sub-1", [item],
                                                   received="2026-10-28T13:00:00Z"))
        self.assertIs(delayed_retry, first)

        second = self.engine.run(assignment("sub-2", [
            IncomingItem.text("i2", "same note", declared_kind="note")
        ], received="2026-10-28T12:10:00Z"))
        self.assertNotEqual(first.event.event_id, second.event.event_id)
        self.assertEqual(first.event.item_records[0].material_id,
                         second.event.item_records[0].material_id)
        self.assertTrue(second.event.item_records[0].exact_duplicate_content)
        self.assertEqual(set(second.materials[0].submission_ids), {"sub-1", "sub-2"})

    def test_reused_submission_id_with_changed_content_is_rejected(self):
        self.engine.run(assignment("sub-1", [IncomingItem.text("i1", "one")]))
        conflict = self.engine.run(assignment("sub-1", [IncomingItem.text("i1", "two")]))
        self.assertEqual(conflict.event.state, IntakeState.FAILED)
        self.assertIn("submission_id_reused_with_different_content", conflict.diagnostics)

    def test_explicit_request_link_and_model_suggestion_are_distinguished(self):
        requests = (
            RequestReference("req-open", "Was the valve leaking?", "pending"),
            RequestReference("req-closed", "Older question", "closed"),
        )
        interpreter = StaticInterpreter((ItemSuggestion(
            "i2", "answer", ("req-open", "invented-id", "req-closed"), "possible match"
        ),))
        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=interpreter)
        result = engine.run(assignment("sub-1", [
            IncomingItem.text("i1", "The requested report is attached.",
                              declared_kind="document", declared_request_id="req-closed"),
            IncomingItem.text("i2", "I found this in the maintenance log."),
        ], requests=requests))
        explicit = result.event.item_records[0]
        self.assertEqual(explicit.links[0].basis.value, "submitter_declared")
        self.assertEqual(explicit.links[0].request_status_at_intake, "closed")
        suggested = result.event.item_records[1]
        self.assertEqual(suggested.suggested_kind, "answer")
        self.assertEqual([(x.request_id, x.basis.value) for x in suggested.links],
                         [("req-open", "model_suggested")])
        self.assertIn("i2:invalid_model_request_link_discarded", result.diagnostics)
        interpreted_text = interpreter.calls[0][0][0].extracted_text
        self.assertEqual(interpreted_text, "I found this in the maintenance log.")

    def test_ask_adapter_emits_only_validated_metadata_suggestion(self):
        calls = []
        def ask(task, system, payload):
            calls.append((task, system, payload))
            return {"items": [{
                "item_id": "i1", "suggested_kind": "note",
                "request_ids": ["r1"], "note": "mentions the requested event",
            }]}
        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=AskIntakeInterpreter(ask))
        result = engine.run(assignment("sub-1", [IncomingItem.text("i1", "event detail")],
                                       requests=(RequestReference("r1", "event detail", "pending"),)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "suggest_intake_metadata")
        self.assertEqual(result.event.item_records[0].suggested_kind, "note")
        self.assertEqual(result.event.item_records[0].links[0].basis.value, "model_suggested")

    def test_malformed_interpreter_output_is_discarded_without_losing_submission(self):
        class MalformedInterpreter:
            version = "malformed-1"
            def interpret(self, items, requests):
                return ({"item_id": "i1", "request_ids": ["invented"]},)
        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              store=self.store, interpreter=MalformedInterpreter())
        result = engine.run(assignment("sub-1", [IncomingItem.text("i1", "A note")]))
        self.assertEqual(result.event.state, IntakeState.READY)
        self.assertEqual(result.event.item_records[0].links, ())
        self.assertIn("invalid_metadata_suggestion_discarded", result.diagnostics)

    def test_unknown_explicit_link_is_preserved_as_warning_and_not_rewritten(self):
        result = self.engine.run(assignment("sub-1", [IncomingItem.text(
            "i1", "Answer", declared_request_id="missing")]))
        self.assertEqual(result.event.item_records[0].links, ())
        self.assertIn("i1:declared_request_link_unknown", result.diagnostics)

    def test_explicit_revision_creates_new_material_linked_to_parent(self):
        first = self.engine.run(assignment("sub-1", [IncomingItem.text(
            "i1", "Version one", declared_kind="procedure")]))
        parent = first.event.item_records[0].material_id
        second = self.engine.run(assignment("sub-2", [IncomingItem.text(
            "i2", "Version two", declared_kind="procedure", declared_revision_of=parent)]))
        current = second.materials[0]
        self.assertNotEqual(current.material_id, parent)
        self.assertEqual(current.revision_of, parent)
        self.assertEqual(current.version_id, "sha256:" + current.content_digest)
        self.assertEqual(second.event.item_records[0].revision_link_status, "linked")

    def test_same_content_labeled_as_revision_is_not_a_new_version(self):
        first = self.engine.run(assignment("sub-1", [IncomingItem.text("i1", "same")]))
        parent = first.event.item_records[0].material_id
        repeated = self.engine.run(assignment("sub-2", [IncomingItem.text(
            "i2", "same", declared_revision_of=parent)]))
        self.assertEqual(repeated.event.item_records[0].material_id, parent)
        self.assertEqual(repeated.event.item_records[0].revision_link_status,
                         "same_content_no_new_version")

    def test_invalid_source_span_is_rejected_from_index_but_original_is_kept(self):
        engine = IntakeEngine(parser=BadSpanParser(), indexer=self.indexer, store=self.store)
        result = engine.run(assignment("sub-1", [IncomingItem(
            "i1", b"file bytes", "application/pdf", "bad.pdf")]))
        material = result.materials[0]
        self.assertEqual(material.extraction.status, "failed")
        self.assertEqual(material.content, b"file bytes")
        self.assertEqual(self.indexer.documents, {})
        self.assertIn("source_span_mismatch:bad", material.extraction.warnings)

    def test_unsupported_file_remains_registered_without_becoming_searchable(self):
        result = self.engine.run(assignment("sub-1", [IncomingItem(
            "i1", b"pdf bytes", "application/pdf", "manual.pdf")]))
        self.assertEqual(result.event.state, IntakeState.PARTIAL)
        self.assertEqual(len(result.materials), 1)
        self.assertEqual(result.event.item_records[0].extraction_status, "unsupported")

    def test_pending_and_failed_index_states_are_reported(self):
        store = InMemoryIntakeStore()
        intake = IntakeEngine(parser=ParserRouter(), indexer=PendingIndexer(), store=store)
        pending = intake.run(
            assignment("sub-p", [IncomingItem.text("i-p", "search me")]))
        self.assertEqual(pending.event.state, IntakeState.REGISTERED)
        self.assertEqual(pending.materials[0].index_status, "pending")
        material_id = pending.materials[0].material_id
        update = intake.complete_indexing(material_id, status="ready", detail="index commit acknowledged")
        retry = intake.complete_indexing(material_id, status="ready", detail="index commit acknowledged")
        self.assertEqual(update, retry)
        self.assertEqual(len(store.processing_updates()), 1)
        self.assertEqual(store.get_material(material_id).index_status, "ready")
        failed = IntakeEngine(parser=ParserRouter(), indexer=FailingIndexer()).run(
            assignment("sub-f", [IncomingItem.text("i-f", "search me")]))
        self.assertEqual(failed.event.state, IntakeState.PARTIAL)
        self.assertEqual(failed.event.item_records[0].index_status, "failed")

    def test_safety_failure_quarantines_item_but_keeps_receipt_and_original(self):
        class Scanner:
            def scan(self, content, media_type, filename):
                return False
        engine = IntakeEngine(parser=ParserRouter(), indexer=self.indexer,
                              safety_scanner=Scanner())
        result = engine.run(assignment("sub-1", [IncomingItem.text("i1", "unsafe")]))
        self.assertEqual(result.event.state, IntakeState.PARTIAL)
        self.assertEqual(result.materials[0].content, b"unsafe")
        self.assertEqual(result.event.item_records[0].extraction_status, "failed")
        self.assertIn("content_quarantined_by_safety_scanner", result.diagnostics[0])

    def test_parser_or_indexer_metadata_does_not_create_evidence_verdict(self):
        result = self.engine.run(assignment("sub-1", [IncomingItem.text("i1", "pressure loss")]))
        self.assertFalse(hasattr(result.event.item_records[0], "effect"))
        self.assertFalse(hasattr(result.event.item_records[0], "supported"))
        self.assertFalse(hasattr(result.event, "board_delta"))


if __name__ == "__main__":
    unittest.main()


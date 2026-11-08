"""Optional adapter test; the PIRIS core itself does not require EWV3."""
from __future__ import annotations

import unittest

from piris import (
    IncomingItem, IntakeAssignment, IntakeEngine, InMemoryIntakeStore,
    InMemoryMaterialIndexer, ParserRouter,
)
from piris.adapters.ewv3 import to_ewv3_sources


class PirisEwv3AdapterTests(unittest.TestCase):
    def test_exports_searchable_source_with_version_and_source_map(self):
        result = IntakeEngine(parser=ParserRouter(), indexer=InMemoryMaterialIndexer()).run(
            IntakeAssignment(
                schema_version="1", case_id="c1", case_snapshot_id="c1:r1",
                submission_id="s1", received_at="2026-10-28T12:00:00Z",
                items=(IncomingItem.text("i1", "A valve pressure log.",
                                         filename="maintenance.txt",
                                         declared_kind="maintenance_log"),),
            )
        )
        sources = to_ewv3_sources(result.materials)
        self.assertEqual(len(sources), 1)
        source = sources[0]
        self.assertEqual(source.source_id, result.event.item_records[0].material_id)
        self.assertEqual(source.source_version, result.materials[0].version_id)
        self.assertEqual(source.text, "A valve pressure log.")
        self.assertEqual(source.source_kind, "maintenance_log")
        self.assertEqual(source.representations[0].structural_context["source_map"][0]
                         ["location"]["start_offset"], 0)

    def test_failed_index_is_not_exported(self):
        class FailingIndexer:
            version = "fail-1"
            def index(self, **kwargs):
                raise RuntimeError("offline")

        result = IntakeEngine(parser=ParserRouter(), indexer=FailingIndexer()).run(
            IntakeAssignment(
                schema_version="1", case_id="c1", case_snapshot_id="c1:r1",
                submission_id="s1", received_at="2026-10-28T12:00:00Z",
                items=(IncomingItem.text("i1", "A valve pressure log."),),
            )
        )
        self.assertEqual(to_ewv3_sources(result.materials), ())

    def test_async_index_completion_makes_material_exportable(self):
        class PendingIndexer:
            version = "pending-1"
            def index(self, **kwargs):
                return "pending"

        store = InMemoryIntakeStore()
        intake = IntakeEngine(parser=ParserRouter(), indexer=PendingIndexer(), store=store)
        result = intake.run(IntakeAssignment(
            schema_version="1", case_id="c1", case_snapshot_id="c1:r1",
            submission_id="s1", received_at="2026-10-28T12:00:00Z",
            items=(IncomingItem.text("i1", "A valve pressure log."),),
        ))
        material_id = result.materials[0].material_id
        self.assertEqual(to_ewv3_sources(result.materials), ())
        update = intake.complete_indexing(material_id, status="ready")
        self.assertEqual(update.processing_stage, "indexing")
        refreshed = store.get_material(material_id)
        self.assertEqual(len(to_ewv3_sources((refreshed,))), 1)


if __name__ == "__main__":
    unittest.main()


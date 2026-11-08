# PIRIS Intake

PIRIS is a standalone, dependency-free Intake core: **Provenance-Preserving
Intake, Registration, Indexing, and Signaling**. It preserves submissions,
registers immutable materials and revisions, extracts searchable renditions,
validates structure and source pointers, and emits a material-arrival event to
the Lead. It does not assess evidence, revise hypotheses, write to the shared
board, or contact the submitter.

## Quick start

```python
from piris import (
    IncomingItem, IntakeAssignment, IntakeEngine,
    InMemoryMaterialIndexer, ParserRouter,
)

index = InMemoryMaterialIndexer()
intake = IntakeEngine(parser=ParserRouter(), indexer=index)
result = intake.run(IntakeAssignment(
    schema_version="1",
    case_id="case-1",
    case_snapshot_id="case-1:r3",
    submission_id="submission-42",  # reuse this ID for transport retries
    received_at="2026-10-28T12:00:00Z",
    sender_id="investigator-1",
    items=(IncomingItem.text(
        "item-1", "Maintenance log: pressure loss was reported.",
        declared_kind="maintenance_log",
    ),),
))
print(result.event.state, result.event.item_records[0].material_id)
```

The included parser handles UTF-8 text and JSON. PDF, office documents, images,
audio, and video require injected parser/OCR/transcription adapters. The
included in-memory indexer is a development adapter, not a production search
engine. `AskIntakeInterpreter` can adapt a structured `ask(task, system,
payload)` client for optional metadata/link suggestions; model suggestions are
validated against known item and request IDs and remain suggestions.

## Guarantees and limits

- Original bytes are retained in the material record.
- A repeated `submission_id` with the same content returns the prior result; a
  repeated ID with different submitted content or metadata is rejected.
  Fingerprints use canonical JSON, and callers should provide a stable
  submission ID for transport retries. `received_at` is excluded so a retry
  with a new transport timestamp remains idempotent.
- Identical content submitted under a new submission ID reuses the content
  record only when its media type also matches, but creates a distinct arrival
  result and submission reference. Concurrent exact duplicates share parsing
  and indexing work within the in-memory store.
- Only an explicitly declared and resolvable parent creates a revision link.
  Similarity does not merge versions.
- Extracted segments may carry exact offsets and page/section/table/region
  locations. Invalid offsets or text spans are rejected from indexing.
- Parser and indexer failures do not erase the registered original.
- A later safe resubmission can retry extraction after an earlier parser
  failure, unsupported format, or quarantine. A quarantined duplicate does not
  enter the metadata interpreter or change an earlier searchable copy.
- If indexing returns `pending`, the caller later reports completion through
  `IntakeEngine.complete_indexing(...)`; it updates material availability and
  returns an idempotent event for delivery to the Lead. `ready`, `partial`, and
  `failed` are terminal completion states; conflicting terminal updates are
  rejected. Repeated material arrivals do not resubmit an index operation
  already pending or completed under the same indexer version.
- LLM output can suggest a kind or open-request link. It cannot set an
  evidence verdict or factual status. The default context is bounded to 20
  items, 50 open requests, and 12,000 extracted characters per item; these
  limits can be configured on `IntakeEngine`.
- The in-memory store is a reference implementation. Production use needs a
  durable transactional store, object storage, a real parser/indexer, and
  durable event delivery to the Lead.

## Evidence Worker adapter

`piris.adapters.ewv3.to_ewv3_sources` converts searchable `MaterialRecord`s to
EWV3 `SourceUnit`s with their version, parser metadata, and source map. The
caller supplies index status so pending or failed materials are not exposed
as searchable.

## Run tests

From the workspace root:

```bash
python -m unittest discover -s tests -p 'test_piris.py' -v
```


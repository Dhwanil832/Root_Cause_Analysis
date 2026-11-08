# Evidence Worker V3 core

This package is the first runnable implementation of the retrieval and
request-drafting boundary in the Evidence Worker v0.4 algorithm. It is
independent of archive storage and registry state. `EvidenceWorkerEngine.run(assignment)`
returns source-span candidate links, per-slot retrieval coverage, bounded
search traces, and request drafts for Assessor review. It does not assess
evidence, send requests, contact a human, or update the shared board.

This is a tested subset of the v0.4 design contract, not complete v0.4
implementation. Lead-assigned bounded comparison is now implemented as
separate answer slots grouped by a `ComparisonSpec`; it searches every assigned
alternative round-robin under the same corpus and reports candidate coverage
per side. It does not detect conflicts automatically or decide what any passage
means. Unassigned-context routing and stale-at-return reconciliation remain
unimplemented.

## Components

- `contracts.py`: versioned assignment, corpus, slot, result, and provenance records.
- `engine.py`: bounded search orchestration and result packaging.
- `validation.py`: assignment, model-output, ID, budget, and source-span checks.
- `ports.py`: replaceable query planner and corpus retriever interfaces.
- `retrieval.py`: exact/lexical fallback, BM25, dense-vector and visual-vector retrieval, hybrid reciprocal-rank fusion, and reranker adapter.
- `optional_models.py`: optional on-prem SentenceTransformers embedder/cross-encoder and CLIP text-image encoder.
- `proposal.py`: adapter to the archive's configured `ask(task, system, payload)` model.
- `ledger.py`: atomic in-memory event idempotency and one-active-attempt guard.
- `lifecycle.py`: work-phase/request-state transitions for multiple pending requests.
- `archive_adapter.py`: read-only boundary to the supplied archive; not registered in V1/V2.

## Run

From the workspace root:

```bash
python -m unittest discover -s tests -p 'test_ewv3.py' -v
python -m examples.ewv3_agent_response_walkthrough
python -m examples.ewv3_comparison_evaluation
```

## Bounded comparison and its evaluation

For a comparison, the Lead defines the dimension and at least two distinct
answer slots. Each slot states what records could address one alternative.
The Worker keeps results separate by slot, applies the same allowed corpus,
versions, channels, and per-slot limits, and round-robins search calls so an
early alternative cannot use the entire global call budget. A comparison
result says which sides have candidate passages and links to them; it has no
winner, support, contradiction, or truth field. The Assessor evaluates meaning.

The offline fixture runner reports four dimensions separately: passage
relevance (precision/recall/MRR against gold passages), comparison completeness
(whether every assigned side yielded a gold-relevant passage), source/location
attribution (source attribution, exact source-location validity, and precision
of links covering a gold span), and cost (elapsed time, retrieval/planner calls,
reranked candidates, and model-token usage when exposed). It uses a scripted
planner and synthetic fixture documents; it is not a live-LLM performance
claim. The default in-memory lexical retriever has no persistent index, so
index-build cost is not measured by this fixture.

For hybrid search, configure `WorkerConfig(channels=("hybrid",))` and inject
`HybridRetriever` with exact/lexical, BM25, semantic, and optional table/visual
backends. It fuses rankings with reciprocal-rank fusion and can apply an
injected reranker. `DenseVectorRetriever` implements cosine ranking over
sentence windows using query/document embedding methods when the model provides
them. Uncached sentence windows are embedded as a batch when the injected
adapter supports it, then retained in a bounded LRU cache. The optional
`SentenceTransformerEmbedder` uses the library's query/document encoding paths
and batched document encoding; the reranker uses a cross-encoder. Both require
the `sentence-transformers` package and locally available model weights. No
model weights or third-party ML packages are bundled.

`SourceRepresentation` carries separate text, table, OCR, or other searchable
renditions with exact offsets and page/table/region metadata. Intake or a
document-specific visual backend must create these renditions. The package
does not perform PDF parsing, OCR, chart understanding, or image embedding by
itself. A returned figure/table link keeps its representation ID and structural
location so the Assessor can open the original source region. The optional
`LocalCLIPImageTextEncoder` plus `VisualVectorRetriever` supports text-to-image
similarity over local page images or crops; it requires `torch`, `transformers`,
Pillow, and local CLIP weights. More specialized late-interaction visual
backends can implement the same retriever port.

The Worker can make one bounded result-aware query-refinement pass for
unresolved slots. It sends structured feedback (queries, slot coverage,
matched/missing facets, source kinds and modalities), not candidate text, then
searches only unresolved assigned slots. Default limits allow at most two
query-planning calls (initial plus one refinement) and one request-drafting
call; `max_search_calls` remains the hard retrieval-call budget. Refinement can
be disabled with `WorkerConfig(max_followup_plans=0)` or restricted to the
initial plan with `max_query_calls=1`.

The in-memory work and lifecycle ledgers are reference implementations, not
durable production storage. Production integration still needs durable
transactional state, Intake representation generation, selected local
embedding/reranking models and modality backends, calibrated budgets, a
Lead-to-`InformationNeed` mapping, snapshot/reconciliation wiring, and an
explicit V3 registry switch. The archive adapter is read-only and sees only
documents registered in `session.documents`; it does not discover external
repositories or mutate archive state. Existing archive V1/V2 behavior is
unchanged.

This build has been checked with 28 focused unit tests and compilation. Tests
exercise hybrid fusion, injected semantic embeddings and reranking, text-bearing
table/figure representations, and the one-pass result-aware refinement loop.
Candidate-link scores are labeled by `score_semantics` and are retrieval
ranking signals only; they are neither probabilities nor evidence-impact
judgments, and scores from different methods are not directly comparable.
The embedding, reranker, and visual-search test backends are controlled test
fixtures, not claims of production model quality. It has also been run
end-to-end with structured responses authored by independent agents. Exact
equipment identifiers are matched as complete literal tokens, so `V-13` does
not match `V-130`. No external LLM provider call, downloaded model, production
semantic index, OCR pipeline, or full archive regression run was performed.
Treat it as a tested V3 core and adapter prototype, not as a
production-integrated worker.

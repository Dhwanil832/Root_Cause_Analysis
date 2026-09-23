# Try 5 — combined engine redesign and optimization plan

Date: 18 September 2026  
Status: replacement engine and independent storyteller code implemented; see try5-implementation.md for verified behavior and limitations. Controlled live-model scientific evaluation remains pending.

## Objective

Build a persistent, evidence-led RCA engine that produces useful, traceable causal updates without repeating the whole investigation, growing every prompt indefinitely, or stopping all work when one item fails.

Optimization is part of the engine design, not a later layer of shortcuts. The target is **less repeated work for the same or better evidence-grounded result**, not fewer questions or a smaller board at any cost.

Basis: [system RCA and saved-run findings](</Users/dhwanilchauhan/Desktop/RCA Try 1/RCA_SYSTEM_REVIEW_2026-09-18.md>). This plan describes intended changes; inherited Try 3/4 architecture and repair notes describe historical implementations, not the new engine.

## 1. Preserve the product; replace the failing core

Keep:

- Incident intake, model selection, history, dashboard, canvas, exports, and human-review actions.
- Independent model tracks, evidence visibility, specialist knowledge bases, and version sequences.
- Three document categories: default references, incident starter documents, and question-response uploads. Preserve synthetic/source-origin labels separately from these categories.
- Baseline understanding before tagging; dynamically selected specialists from the fixed taxonomy.
- Specialists' independent interpretations and ability to ask meaningful follow-up questions.
- Question broker after questions are proposed; common answer fetching; broker routing answers back to every originating specialist. Causal-analysis questions use the same path.
- Separate code sections and prompt folders for each reasoning responsibility.
- Qwen as the initial evaluation model, with its exact model digest/configuration recorded. Keep provider adapters for later models, but no model mixing or fallback.

Replace the full-cycle execution boundary, repeated state assembly, inconsistent source references, growing global prompt catalogs, and whole-board regeneration. Do not merely wrap the old loop in another orchestration layer.

No fixed total question/agent/branch limit is introduced. Individual model requests and retries must nevertheless be controlled: a large archive is accessible through reading/retrieval tasks, not one unlimited prompt. No automatic closure or invented conclusion is used to make a run finish.

## 2. Ownership and lean implementation

**Application code owns:** original evidence, identifiers, exact citations, records and revisions, task dependencies, scheduling, cache decisions, structural validation, graph updates, version history, and metrics.

**Models propose:** interpretations, questions, semantic equivalence, possible mechanisms, competing explanations, evidence assessments, and causal relationships.

**Humans own:** evidence clarification and approval/rejection decisions. Machine review does not become human approval or independent corroboration.

Use one persistent investigation store, one task ledger, and the existing modular stage pattern. Start with a local worker and the current storage boundary; do not add an external queue service, graph database, vector database, agent framework, or manager agent without a demonstrated need. The worker must actually resume independently of the originating browser request; an in-memory promise map is not the durable scheduler.

## 3. Ordered delivery plan

| Phase | Engine change | Optimization included | Observable checkpoint |
|---|---|---|---|
| 0. Preserve the baseline | Keep Try 4 unchanged; isolate Try 5 storage/configuration and identify historical scripts with old paths | Reuse saved failures and artifacts instead of generating another baseline | Try 5 cannot write into Try 4's runtime state; comparison inputs and configurations are recorded |
| 1. Evidence and record foundation | Unified source registry, typed findings, stable identities and revisions | Extract/index unchanged sources once; share references without copying interpretations | Every relevant table row and quotation resolves to its original; re-upload does not redo identical extraction |
| 2. Durable task execution | Task ledger, dependencies, leases, result commits, failure isolation | Reuse completed work and rerun only invalidated tasks | Worker restart preserves committed work; one bad task does not stop independent tasks |
| 3. Focused agent work | Context planner, retrieval, specialist/broker/answer contracts | Reuse evidence retrieval; optionally batch closely related questions | A question gets the right sources without a full global catalog; answers return to all owners |
| 4. Incremental causal reasoning | Persistent hypotheses and relationships, explicit board changes, separate verification | Reuse unchanged reviews; retrieve plausible connections instead of all node pairs | New evidence changes the relevant branch while unrelated findings survive |
| 5. Version and dashboard integration | Immutable input revisions/results, explicit partial progress and change explanations | Render stored projections; do not invoke reasoning for display/export | The UI distinguishes running, failed, waiting, supported, and human-approved states |
| 6. Controlled Qwen demonstration | One incident, frozen evidence, V1 then a controlled V2 release | Measure calls, input size, duplicate work, and valid reuse against semantic quality | Correct expected updates, honest uncertainty, recoverability, and no silent input loss |
| 7. Storyteller and generalization | Independent answer-batch production/release; held-out incident | Reuse the common source contract and task infrastructure | Story and RCA run separately; the same engine handles another incident without scenario-specific rules |

Phases 1–5 form the first working end-to-end slice. Build a minimal source → question/answer → finding → causal update → review → snapshot path early, then migrate the existing specialist roles onto it. Do not wait for a large new infrastructure platform or dashboard redesign before demonstrating that path.

Short automated checks accompany implementation. They are not a separate sequence of expensive preflight model experiments, and passing them is not reported as a successful RCA.

## 4. Phase 1: trustworthy evidence and persistent records

### Source contract

Each original has an immutable document ID, content hash, revision, scope, origin, extraction version, extraction limitations, and model-track attachment. Each passage has a stable ID and an exact source location. Preserve table headers, rows, units, timestamps, and instrument/location context. Preserve images and page/region references; unsupported modalities remain explicitly unread, not silently treated as complete extraction.

Text, OCR/vision observations, answers, and specialist interpretations must not be interchangeable evidence types. Exact quotations come from stored spans, not model recollection. Repeated specialist statements referencing one source are not independent corroboration.

Cache deterministic extraction using content hash plus extraction configuration/version. A source revision creates a new artifact. Even if identical file bytes can be reused internally, evidence visibility and attachment changes remain isolated per model track. No generated interpretation is shared across model tracks.

### Investigation contract

Maintain separate record types for entities/context, observations, testimony, requirements, hypotheses, questions, contradictions, causal propositions, causal relationships, and reviews. Include entity, location, time/interval, units, operating phase, qualifiers, supporting/opposing source references, and specialist ownership where applicable.

Assign record identities in application code. Editing wording creates a revision of a known record, not automatically a new finding. Exact duplicates can be handled deterministically. Possible semantic duplicates become a focused comparison; do not collapse different locations, times, premises, or viewpoints because their wording is similar.

Specialists keep their own interpretations and coverage records. A shared source index is not a central model-written summary that filters what specialists are allowed to notice.

## 5. Phase 2: durable execution and safe reuse

Each task records its model track, input revision, type, owner, target, dependencies, prompt/schema/model versions, selected source revisions, retrieval scope, attempts, execution status, result, and metrics.

Use durable task claiming and leases. Committing an output and recording task completion must be atomic/idempotent. A crash after a provider response but before persistence may require another attempt; record that uncertainty rather than promising exactly-once model inference. Already committed successful tasks must not rerun merely because the worker restarted.

Failure behavior:

- A malformed item or unresolved reference is quarantined; independent valid work continues.
- A wholly unusable response fails its task, not the whole investigation. Retry according to failure type; do not retry indefinitely without new information or a changed execution condition.
- Invalid references never become accepted evidence through permissive fallback.
- A provider outage pauses provider-dependent work while saved results remain available.
- Failed execution is not converted into an “insufficient evidence” scientific verdict.
- Questions awaiting unavailable evidence wait for a response; repeatedly asking the same question is not progress.

### Cache invalidation is a correctness requirement

| Reusable work | Reuse requires | Invalidate when |
|---|---|---|
| Extraction/indexing | Identical bytes and extraction/index configuration | File, parser, OCR settings, or source representation changes |
| Retrieval | Same query/intent and applicable evidence inventory | Relevant new/revised evidence, changed entity mapping, or changed search scope |
| Answer/finding interpretation | Same task, model/prompt contract, premises, and applicable evidence | New support/conflict, corrected context, changed assumptions, or changed source assessment |
| Causal review | Same proposition/relationship and valid reviewed dependencies | Changed premises, opposing evidence, revised mechanism, or relevant human decision |
| UI/report projection | Same stored snapshot | New snapshot or display-only preference change |

Every incoming source also triggers a relevance/novelty check against the investigation's indexed entities, questions, and hypotheses. Do not check only already-cited documents: a new document can contradict a cached conclusion. Route ambiguous relevance broadly enough for review. Record what was considered and why work was retained or invalidated.

“Not found,” “unknown,” and absence-based claims depend on search coverage and must be reconsidered when their applicable evidence inventory grows. Preserve a path for broader cross-specialist review so incremental routing does not lock the investigation into its first theory.

## 6. Phase 3: bounded context and efficient agent contracts

### Context planner

Construct a task packet from a short context summary, specific targets, selected original spans, relevant opposing evidence, and nearby findings. Summaries are navigational aids, not replacements for original evidence needed to judge a claim.

Account for instructions, input, schema, provider overhead, repair headroom, and output allowance. Use provider/tokenizer information where available; label estimates honestly and compare them with actual reported usage. Enforce no silent truncation. Both input and output-reference catalogs must stay bounded.

If a task is too large, decompose evidence reading and premise checks, then assess the necessary premises together with source access. Do not keep shrinking target count while leaving a growing shared catalog untouched. If a task still cannot safely fit, expose the local limitation; do not discard evidence invisibly or stop unrelated work.

### Retrieval and question grouping

Build source indexes once, rather than rebuilding segments for every question. Start with source/entity/location/time-aware retrieval and searchable originals. Select raw evidence and specialist leads separately so derived knowledge cannot crowd all originals out of the result set. Allow cross-document joins and broader retrieval when coverage is inadequate.

Related questions may reuse a retrieval working set. Small answer-generation batches are optional after the single-question path works; group only questions sharing context and source needs. Preserve each question ID, owner, answer, citations, uncertainty, and validation result. A defect in one answer must not invalidate valid siblings. Never batch across model tracks or frozen input revisions.

Keep one inference in flight for the initial local-model evaluation. Parallelize independent file/index operations first; higher model concurrency is a later measured optimization, not an assumption.

### Prompt contracts

For each stage, specify its investigative purpose, permitted evidence, input/output meaning, uncertainty rules, completion condition, and escalation path. Keep kickoff questions as examples, not mandatory scripts or caps.

Require evidence-grounded decision summaries and explicit supporting/opposing references, not private chain-of-thought. Source documents and answers are untrusted evidence, never instructions overriding the stage's role.

Do not require models to regenerate global IDs, exact quotations, full previous boards, or administrative history. Preserve separate prompt/code sections even where operations share retrieval or scheduling. Not every module needs a model call.

## 7. Phase 4: causal changes instead of whole-board regeneration

The causal stage proposes a specific mechanism or relationship, the premises that would make it true, alternatives, evidence gaps, and a discriminating question where needed. Temporal order alone is not causation, and a missing record does not establish physical absence.

Use explicit changes: add, revise, supersede, reject, link, or reopen. Application code validates identifiers, records revisions, prevents duplicate relationships, and materializes the board. Preserve competing hypotheses and joint contributing conditions; do not force one chain or one root cause.

Find candidate connections using relevant entity/time/mechanism neighborhoods, plus broader cross-branch checks. Do not exhaustively pair all nodes. Keep questions and source-quality concerns outside physical causal chains unless an actual causal role is established.

Verification has two distinct layers:

1. Deterministic checks: valid references, exact source resolution, required fields, revision consistency, and graph structure.
2. Semantic review: do the sources support the proposition, are location/time/units correct, and is the mechanism justified against alternatives?

Deterministic success does not establish semantic truth. Reuse semantic reviews only under the invalidation rules above. Review materially changed and affected relationships; preserve valid unaffected reviews with their original provenance. Same-model review is a useful check, not independent evidence.

Render node type/status as metadata; do not require those labels to be repeated inside prose. Preserve acceptance/rejection and corrective-action approval as explicit human actions. If new evidence undermines an accepted finding, flag it for renewed review without erasing the human decision history.

## 8. Phase 5: version semantics and honest progress

Submitting any new answer, document, or human review immediately preserves the prior version and creates a new immutable input revision in that model's track. Do not wait to collect a larger batch of user answers just to save model calls.

The new revision can have an in-progress working result. Its final snapshot is immutable when published. If another answer arrives while it runs, record the next revision immediately and queue it in order. Old task results cannot overwrite a newer revision. Reuse eligible completed tasks across revisions through dependency checks, not by silently mixing evidence sets.

Expose separately:

- Execution state: pending, running, waiting, failed, completed.
- Evidence state: proposed/not reviewed, supported, partial, conflicting, unknown, contradicted.
- Causal status: candidate mechanism versus established relationship.
- Human review state: unreviewed, accepted, rejected, reopened for review.

Display partial work, remaining tasks, local failures, and why a branch changed. A failure on one branch need not hide a valid partial board, but a partial snapshot cannot be labeled a completed investigation. Keep title cleanup, sorting, layout, and exports deterministic; they must not trigger new reasoning.

## 9. Proposed module boundaries

These are planned relative locations inside Try 5, not files already implemented.

| Location | Responsibility |
|---|---|
| `src/orchestrator/main-router.ts` | Readable entry point: accept input revision, schedule affected work, expose progress |
| `src/engine/tasks/` | Durable task lifecycle, dependencies, invalidation, leases, retries, result reuse |
| `src/engine/context/` | Task-specific context planning, local references, coverage and budget accounting |
| `src/knowledge/sources/` | Immutable originals, exact spans, table-aware extraction, source revisions |
| `src/knowledge/retrieval/` | Reusable indexes, related-question working sets, cross-document retrieval |
| `src/domain/` | Typed records, identities, revisions, explicit state contracts |
| `src/stages/<responsibility>/` | Existing clear agent responsibilities adapted to task inputs/results |
| `src/engine/board/` | Persistent causal records, validated changes, version projections |
| `src/server/` and `db/` | Storage/API adapters; no hidden reasoning in request handlers |
| `src/story-agent/` | Independent simulation state and frozen answer-batch production |
| `prompts/<stage>/`, `prompts/specialists/<tag>/` | Inspectable stage contracts and specialist examples |
| `evals/try5/` | Inputs, private expected findings, manifests, scoring, and artifacts separated by visibility |

Keep the current storage approach behind an interface while validating the local worker integration. Do not rewrite every UI/provider component. Route Try 5 exclusively through the replacement engine when the first slice is ready; do not leave an automatic old-engine fallback that hides failures. Historical Try 4 outputs remain available as historical artifacts, not preverified new-engine findings.

## 10. Phase 6: prove correctness and optimization together

Use the saved IA evidence package with the same Qwen configuration. Do not run a new preliminary model experiment merely to reconfirm a known failure. Start with one actual V1, then one controlled evidence release producing V2.

Before the run, record what the released evidence should establish, contradict, and leave uncertain in an evaluator-only file. None of those expected conclusions enters prompts or model-visible documents. Do not special-case IA or R3 in production logic.

Acceptance cases:

- Pressure-table rows, decimal values, timestamps, headers, and units remain available through exact source references.
- Instrument-location mapping is joined with measurements correctly; sampled evidence is not claimed to establish continuous conditions.
- The answerable alarm-signal distinction is recovered without inventing a compressor trip or prematurely establishing a physical cause.
- Procedure alternatives and preparation-versus-execution distinctions survive interpretation.
- A new relevant source invalidates an old “unknown/not found” answer or conflicting conclusion, even if its old cited source is unchanged.
- V2 makes the declared evidence-driven changes and preserves unrelated useful branches; renaming nodes is not counted as progress.
- The saved 148-candidate workload and larger duplicate/distractor catalogs do not produce unbounded prompt/schema growth or blind all-pairs linking. These are stress fixtures, not trusted factual findings.
- A malformed task result and worker restart leave valid committed work intact. No successful output is replaced by a fabricated fallback.
- Every model-visible source belongs to the selected track and input revision; evaluator expectations and other model outputs remain inaccessible.

### Two scorecards, not one misleading pass flag

**Operational:** task completion/coverage, retrieval coverage, truncation events, local versus propagated failures, restart behavior, version integrity, and stale-result prevention.

**Scientific:** correct expected findings, supported-claim precision, causal-link justification, unsupported assertions, contradictions, uncertainty, useful-branch retention, and positive discovery of answerable facts.

Track efficiency alongside both: calls, actual/reported tokens where available, wall time, source-processing repeats, retry waste, reused tasks, schema/context size, and duplicate propositions/relationships. Use comparable workloads and label historical comparisons whose prompts or contracts differ. Do not claim a speedup by comparing a failed short run with a completed investigation, or by excluding required work.

Set package-specific required findings and prohibited assertions before running. Operational failures cannot be averaged away by a semantic score, and an empty/all-unknown board cannot pass when the package contains answerable facts. Repeated matching runs are needed before calling performance consistent; the first correct V1→V2 is an initial demonstration, not proof of general robustness.

Scoped, task-specific evaluation and human-calibrated grading inform this separation of checks. Trace inspection is used to locate failures rather than judging only the final board. See [evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) and [trace grading](https://developers.openai.com/api/docs/guides/trace-grading). The plan uses these general principles locally; it does not require an OpenAI evaluation service or model.

## 11. Phase 7: independent storyteller, then broader validation

After the controlled RCA update works, run the storyteller against the current question set using its own persistent scenario memory. Save its answer batch, source references, limitations, and release identity. RCA then consumes that frozen batch in a separate invocation. Either side can stop or restart without keeping the other alive.

The storyteller may have scenario information that is not yet releasable. Its hidden world state must stay outside RCA inputs. The evaluator's scoring rubric stays outside both models. Released simulated answers remain testimony, not automatically approved facts; the RCA engine must detect inconsistencies against the released originals.

Evaluate a short answer batch first, then the four-version experiment. Test a held-out historical incident from a different scenario with unchanged production rules. Only afterward compare other local models sequentially. Report storyteller answer quality separately from RCA's ability to use or challenge those answers.

## 12. Scope boundaries and first concrete target

Not included now: fine-tuning, model ensembles/fallbacks, production authentication/security hardening, large-scale deployment, a new infrastructure stack, or an embedding database added without a measured retrieval need. Existing credentials must still stay out of prompts/logs, and evidence must remain separated from instructions.

No promised percentage speedup or guaranteed error-free RCA. Optimizations are accepted only when they preserve required evidence coverage and semantic results.

**First concrete target:** one incident, one Qwen track, one correct V1→V2 evidence-driven update through the new task engine, with unchanged work reused, affected work rechecked, original citations preserved, and local failure/restart behavior visible. Then expand to the storyteller and other incidents.

Implementation checklist:

- [x] Isolate Try 5 state and record baseline artifact/configuration references.
- [x] Implement source spans, typed records, stable identities, and extraction reuse.
- [x] Implement durable tasks, dependency invalidation, and independent recovery.
- [x] Implement task context, reusable retrieval, and specialist/broker/answer contracts.
- [x] Implement incremental causal proposals, semantic review, and board changes.
- [x] Connect versioning, partial progress, human review, and reporting.
- [ ] Run and review the controlled Qwen V1→V2 against both scorecards.
- [ ] Reconnect independent story batches, attempt four versions, and test a held-out incident.

# Try 4.3 — implemented repair pass

## 4.3.6 — preserved discovery; consolidated checkpoint restart

### Evidence for the change

The 4.3.5 continuation completed ten discovery calls but materialized 149 nodes
and 1,175 edges. Its Cartesian target/source-page linking required 264 calls;
revision accounting required another 130. Draft nodes included semantically
duplicated facts, evidence limitations and open questions. Some sourceIds were
actually claim IDs or filenames, which the verifier did not resolve. Verification
also ANDed verdicts from separately presented evidence pages. Those are distinct
defects; smaller context alone did not fix them.

The old replay was stopped, not erased. All ten discovery calls, exact inputs,
raw proposals and partial reviews remain in the archived run. Source/prompts/
scripts were copied to `../IA-16036 Controlled Evidence Package/06_run_records/
preserved-before-4.3.6-3NEIXX/` before this repair.

### General implementation, not a case-specific expected answer

- `evidence-index.ts` resolves document IDs, segment IDs, unambiguous filenames,
  and claim references. Cycles, ambiguous names and unavailable refs remain
  unresolved. Resolution never silently replaces a wrong citation with the source
  we hoped it meant. Complementary records are separately selected and coverage
  is explicit. Claims and simulated answers are not independent corroboration.
- `consolidate.ts` assigns every draft a board/merge/context/question/rejected
  disposition with a reason. All candidates remain in the proposal ledger and raw
  checkpoints. There is no total-node quota and no incident-specific cause rule.
- `run.ts` links each target group against one compact consolidated catalog.
  It no longer loops over every target page × every source-node page. Relationship
  identity is endpoints + type; duplicate variants remain in audit, rejected
  proposals remain outside active edges, and disagreement prevents promotion.
- `focused-operation.ts` divides target work while keeping selected evidence
  together. It never combines independent page verdicts with AND. Indivisible
  oversized work is reported, not truncated. The existing no-truncation provider
  controls remain. Explicit source coverage is not a guarantee of retrieval recall.
- Verification differentiates supported, contradicted, insufficient and viable
  hypothesis. It checks source quotations mechanically, reviews causal arrows
  separately from their endpoints, and leaves unproved hypotheses unknown. A
  failed target review is recorded without erasing unrelated completed reviews.
  Exact quote matching checks traceability, not semantic entailment or ground truth.
- New phase-specific prompts are colocated under causal-analysis; discovery's
  prompt and schema are unchanged so exact completed calls can be reused.
- Branch accounting reviews the compact current board; absent old branches are
  not automatically declared false. Human RCA closure is never auto-awarded.

### Restart and checks

`../IA-16036 Controlled Evidence Package/06_run_records/tools/
restart_consolidated_causal_v2.mjs` freezes code/prompts, hashes saved discovery
checkpoints, prohibits fresh discovery requests, and writes durable intermediate
phase artifacts. It does not write to the app database. Original evidence,
model digest, 96 claims, eight documents and four answers are unchanged.

Active continuation: `qwen-v2-consolidated-btG98n`. All ten discovery calls were reused;
148 byte-distinct draft candidates entered consolidation. First new request saw
all eight documents, original incident and four answers together (no omitted
source records). Final performance is not yet established; consult result.json
or failure.json and phase artifacts rather than treating this note as completion.

The first attempt (`qwen-v2-consolidated-2c95T4`) exposed an over-strict cross-field
validator: an unused proposition on a question/rejected row failed the whole
batch. The corrected consumer honors disposition, ignores unused fields, records
unresolved claim references, and quarantines malformed merges locally. The failed
attempt remains preserved; matching successful checkpoints are available to resume.

TypeScript and targeted lint passed. Offline regression tests passed;
no LLM preflight/rehearsal was run. Coverage includes reference routing, ambiguous
aliases, merge cycles, duplicate edges, exact quotations, target-only subdivision,
joint-source review and preservation of unknown hypotheses. These are mechanics
checks, not proof of RCA quality or general robustness. Other incidents, larger
archives, conflicting evidence and provider models still require live evaluation.

## 4.3.5 — managed causal context and isolated V2 replay

### Confirmed failure being repaired

The completed `qwen-focused-v2-no-text-caps-sgaA81` V2 had 96 claims, including
the pressure comparison and alarm mapping, but its seven NODE calls returned
empty node arrays. Every call repeated a 164,275-character previous-board
object, including review and rejection history. Ollama logged truncation of
roughly 49,000–55,000 input tokens to 16,386. The saved V2 has one node and no
edges. Removing the application size stop did not prevent this information loss.

### Implementation

- `src/stages/causal-analysis/context-plan.ts` keeps an evidence archive with
  exact source passages, claims, previous targets/review issues, and open questions.
  Focused operations receive a relevant working set; the model can request records
  by ID. A document ID resolves to all of its passages, not just its first chunk.
- `label-contract.ts` constructs a working-board view without copying audit
  history. The saved comparison shrinks that view from 164,275 to 14,045 characters.
  Historical boards, their statements/statuses, and source documents are unchanged.
- `managed-operation.ts` partitions context records and growing revision catalogs.
  Every selected record is retained on a page; a server context refusal subdivides
  only that operation. Retrieval is finite over the archive and repeated requests
  do not trigger an endless loop. Missing record requests remain visible.
- `providers/context-budget.ts` sizes the complete request, including the prompt,
  schema, evidence, output allowance and headroom. Bytes/2 is a planning estimate,
  **not** an exact tokenizer. Causal generation and verification use `truncate:false`
  and `shift:false`, supported by the installed Ollama 0.32.3; server refusal, not
  an estimated token count, enforces no silent input loss. See the
  [versioned Ollama request definitions](https://github.com/ollama/ollama/blob/v0.32.3/api/types.go).
- Every claim gets a discovery pass; linking examines nodes across discovery
  partitions. Explicit revision records account for every previous node/edge as
  kept, strengthened, weakened, revised, rejected, or unresolved. Invalid/missing
  replacement references cannot silently count as retention. An incomplete
  revision operation leaves those targets unresolved rather than erasing the
  generated graph. The dashboard exposes the revision ledger.
- Exact saved model calls remain reusable. Managed causal request identity has
  a new context-policy marker, preventing reuse of old potentially truncated calls.
  The replay tool can reuse completed calls through its saved replay lineage.

### Verification and live comparison

TypeScript compilation and targeted lint pass. Thirteen small offline regression
checks cover archival immutability, context coverage, growing catalogs, no-truncation
request flags, server-refusal subdivision, record retrieval, and historical wording.
No LLM preflight/rehearsal and no upstream investigation or storyteller rerun.

Current isolated replay: `../IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-managed-causal-RPVgjT`.
It uses the same Qwen model digest, 96 saved claims, eight documents and four
unchanged answers. The exact causal claim view is checked against the saved V2
partitions. Evaluator expectations are not sent to the model. No app database or
committed version is replaced.

Its precursor `qwen-v2-managed-causal-7VC5eM` was stopped after four durable calls
to include the additional growing-catalog safeguard. All four calls were reused
by the continuation, not regenerated. The fifth in-flight precursor request was
interrupted and was not accepted as a completed call.

The first five completed discovery calls processed 9,144–9,901 input tokens and
produced propositions, unlike the old seven empty outputs. They include the
P-U/P-R comparison and AL-44 mapping, but also duplicate propositions and dubious
acknowledgment claims. This establishes progress on input delivery, **not** a
successful RCA. Full mapping and independent verification are still pending at
the time of this note; consult the replay's result/failure/checkpoint artifacts.

### Deliberately not changed / remaining limitations

- Storyteller table citation extraction and inconsistent claim review are unchanged
  so this comparison isolates the causal context repair.
- Lexical relevance selection can miss material; retrieval and coverage labels do
  not guarantee completeness. An indivisible oversized task/record is reported
  explicitly rather than silently truncated; arbitrary-size inputs are not promised.
- More propositions can mean more link/verification operations. Duplicate proposals
  and evidential accuracy must be evaluated separately from execution completion.
- Revision decisions are model interpretations, not human approval or proof. Unknown
  branches may remain in the revision ledger awaiting reconciliation.


## 4.3.4 — remove hard text-size stops and resume V2 exactly

The focused four-question run completed incident understanding and structuring, then tagging was rejected before inference because its request measured 60,159 characters against a 60,000-character application ceiling. The earlier 99-question storyteller run had hit a separate 100,000-character memory ceiling. The user explicitly requested removing these stops.

- Removed the generic RCA packet character rejection and both storyteller scenario/memory character guards. Removed scenario/source count and text ceilings and storyteller response/quotation character ceilings; required fields, unique IDs, exact citations and question coverage are still validated.
- Removed the 160,000-character extracted-document prefix cap. New extraction preserves the complete normalized text. Previously stored truncated documents would need explicit re-extraction; no historical record is silently rewritten.
- Verification keeps a soft 60,000-character batching target and retains all context across partitions. An indivisible oversized record is now sent intact rather than rejected. This preference is not a maximum admissible request size.
- Resume reuses the exact saved incoming answer batch, including delivery timestamps. For a failed story application, it now claims the ready round before resuming and atomically marks the round applied with the committed version. On another failure, the round returns to ready with its error.
- Prompts, RCA output schemas, evidence, model/context configuration, correctness checks and provider execution settings are unchanged. This does not make the model context, RAM, upload transport or output generation unlimited, and it does not ignore invalid output to manufacture a successful board.
- Direct function checks passed for a scenario above 100,000 characters, 61 sources, long story responses, an indivisible 65,000-character verification record, and complete 160,500-character text extraction. Duplicate source IDs still reject. No model preflight/rehearsal was run.

The isolated continuation is `qwen-focused-v2-no-text-caps-sgaA81` on port 3009. The failed port-3008 run and successful V1 remain unchanged. It resumed V2 at **2026-09-17 01:25:31 UTC**, reused both completed model calls, and dispatched the previously rejected tagging input. Storyteller responses were not regenerated. Completion and evidence quality must be judged from subsequent saved results, not from these changes alone.

Live verification: tagging completed successfully at **2026-09-17 01:28:15 UTC** with the previously rejected 60,159-character packet. There were no new stage failures at that point; V2 was still running and not yet committed. TypeScript compilation passed.

## 4.3.3 — size the entire verification packet

The 4.3.2 continuation finished causal analysis and ten verification operations, then stopped because the eleventh verification packet had 64,421 characters (limit 60,000). Exact reconstruction from the saved B0 state reproduced all ten completed inputs and the failure. Claims, including review records and quotations, occupied 54,430 characters; source excerpts occupied 6,235. The previous batching bounded sources but not the complete packet.

- Only oversized verification packets are partitioned. The planner sizes complete serialized input, including partition metadata, and splits context collections without truncating individual records. Each partition retains all review targets and endpoint nodes. An indivisible oversized record still stops explicitly rather than silently losing evidence.
- Every resulting partition is reviewed. Conservative support aggregation is unchanged: a positive review on one page cannot override a gap or contradiction on another.
- Packets already within budget are unchanged, preserving exact cache identity. No prompt, output schema, evidence, model or causal-generation change.
- The actual B0 packet plan changes from 24 to 25 operations. Only packet 11 changes: 28 claims become two groups of 14, with packet sizes 33,920 and 41,283. All original context records and targets are preserved; all ten prior verification calls remain exact matches. The largest planned packet is 55,282 characters.
- No preflight suite or new-model rehearsal. TypeScript compilation passed; a local application build and a single saved-work continuation provide runtime validation.

Live result: `qwen-b0-verification-packets-hnHgwz` committed exactly one V1 at **2026-09-16 21:02:26 UTC** and stopped. It reused 75 completed calls and made 15 new verification calls, all first-attempt successes. All 72 nodes/connections were reviewed. There are no stage errors; the investigation remains `awaiting-evidence`, with 8 model-accepted nodes, 0 accepted connections and 112 review findings (including 48 separately rejected proposals). This establishes completion/recovery for this case, not a proven root cause. No storyteller, later batch or corrective action was introduced. Local build passed; all 137 frozen source hashes match.

## 4.3.2 — local causal rejection, not a whole-stage stop

The resumed B0 passed claim review, then stopped at a self-link in the seventh causal-link operation. The same stage already had an item-level self-link rejection path, but its newly added provider validator stopped the batch before that path could run.

- Removed that batch-fatal semantic validator. Unusable schemas/provider failures still stop their operation; unsupported evidence and rejected connections are not execution failures.
- Self-links, backward links from the incident to pre-event conditions, and causal links missing their counterfactual/alternative are excluded from active edges and retained as `rejectedEdges`, including original proposal and rejection reasons.
- Each rejected proposal owns its blocking finding. A rejected arrow no longer blocks its destination node or unrelated supported branches.
- The dashboard and report expose rejected proposals. Saved uncommitted boards are inspectable read-only, clearly distinguished from committed versions; human approval actions remain disabled on previews.
- No prompt, schema, evidence, model, or node/link batching change in this pass. No automatic whole-run retries or storyteller. Earlier frozen experiments remain untouched. Compilation passed; live continuation is required to establish runtime behavior.

Live continuation `qwen-b0-local-rejections-etH9Rd` reused 57 calls and passed the previously failing operation despite Qwen again proposing self-links. At 20:31:55 UTC it saved a 40-node, 32-edge developing board with all 48 rejected proposals separately preserved. All 80 raw proposals are accounted for; no active self-links or rejection findings misassigned to retained targets. The browser exposes this as a read-only Pending V1. At 20:33:35 UTC two verification calls had completed with no new execution failures, but V1 was not yet committed. This verifies the specific recovery path, not RCA correctness or full-run completion.

## 4.3.1 — claim-review repair and explicit resume

The B0 experiment `qwen-b0-ClBDGA` stopped at claim review after 38 saved calls. Its repair response invented an incident-source suffix and simultaneously asserted support with failed checks. The original frozen run is unchanged.

- Claim review now selects application-owned passage IDs from exact, consecutive source slices. The app writes the actual source ID and quotation; the model no longer transcribes either. Required review properties are keyed by the supplied claim IDs.
- Proposed support with failed checks becomes **partial**, and a verdict without selected evidence becomes **unsupported**. The proposed verdict, checks and reasons for withholding support remain in the saved assessment. This is fail-closed at the claim level, not permission to infer missing evidence.
- The checkpoint input namespace remains compatible with 4.3.0. Full per-call prompt, schema, packet and media hashes still control reuse, and saved output must pass the current schema and validator. Changed claim-review calls are not reused. Provider/identity changes require a namespace bump.
- Reuse is recorded as `model-call-reused`. New calls also preserve their full request identity alongside raw responses.
- TypeScript compilation passed. No preflight suite was run. The explicitly resumed live experiment is `qwen-b0-resume-jJlucQ` on port 3004, a separate database snapshot of the failed B0 run, not a new independent evaluation. At dispatch it reused all 36 upstream model calls; claim-review completion and final RCA quality must be assessed from subsequent saved output.

That run completed all 12 new claim-review batches on their first attempt and saved 45 claims. All 61 stored citations resolved to exact original source text. Nine inconsistent proposed-support verdicts were withheld as partial, with explicit reasons. It later stopped at causal analysis because of the batch-fatal self-link validator addressed in 4.3.2; citation integrity and completed review do not establish final RCA correctness.

## 4.3.0 — original repair pass

The original pass changed the application, not historical runs or frozen experiment packages. No new model experiment, storyteller run, or preflight test suite was launched during that implementation pass. TypeScript compilation was checked; it did not establish RCA correctness or runtime recovery reliability.

## What changed

- **Recoverable work:** every validated model call is persisted in the existing checkpoint table before the next call. Reuse requires matching case inputs, prompt/schema, configuration and Ollama model digest. Resume restores the pending answer batch. Unknown model digest disables reuse. Old checkpoints without the new model-call records cannot be used as a cache.
- **Application-owned identities:** causal nodes are generated before connections. The application creates keys, then supplies permitted endpoints and claim references. The broker selects one owner for each fixed question property. Verification fills fixed target properties, not generated edge IDs or indexes. Raw outputs remain preserved.
- **Evidence handling:** complete source text remains stored. Source adjudication and extraction use batches; large document collections are read in full by source-reading operations, then explicitly labeled relevant excerpts are supplied to foundation/specialist stages. Retrieval is not an exhaustive absence check. Claim/source review and verification can access original text.
- **Claim review:** newly fetched, extracted and specialist claims are reviewed before entering the causal input. Exact quotations are checked against supplied text. Entity, location, time, meaning and qualification checks must all pass for full support. Claim review is model review, not human verification. Conflicting or unsupported claims remain visible as unresolved leads; they cannot support verified edges through a cited claim ID.
- **Visible states:** the dashboard shows pending work even before V1, provides Resume and Refresh actions, displays all claims with review reasons/quotations, and separates proposal status, evidence review and human decisions. A completed execution is not a completed RCA.
- **Smaller operations:** claim partitions, source batches, graph target partitions and per-target verification reduce the amount of output required in one response. A failed operation remains bounded to the provider's existing two attempts. Resume requires an explicit user action; there is no automatic full-cycle replay.

## Using the changed app

Create an incident normally. Its durable record opens on the dashboard before inference starts. If the pass stops, use **Resume investigation** on that model's dashboard. Successful matching model calls are reused; changed inputs are recalculated. A fresh model run is still needed to assess the quality of the new behavior.

The storyteller remains a separate, explicitly invoked feature. Nothing in this pass starts it or reconnects an autonomous four-version loop.

## Remaining limits — not claims of success

- Model evidence review can still make interpretation errors. No successful new Qwen RCA is claimed by these edits.
- Source-reading relevance selection is not lossless semantic compression; coverage is stated explicitly. Lexical retrieval can miss relevant passages.
- Since 4.3.4, application text-size guards no longer reject large packets. The configured model/provider still has a finite context; removing a character guard does not guarantee arbitrary-sized investigations fit or preserve provider-side context.
- Concurrent execution protection is local-process protection plus the existing unique version constraint, not a distributed production job scheduler.
- More small model calls can increase total inference work. The repair targets recoverability and evidential integrity, not a promised speedup.

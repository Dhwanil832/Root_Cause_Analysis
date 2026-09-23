# External story simulator

## Try 6 controlled release (current)

The older implementation notes below describe previous experiments. For a separated
Try 6 run, `generate` queues the selected existing question IDs and does not start
RCA. Optional `sourceIds` freezes a per-round allowlist of available private archive
records. The worker filters the scenario before constructing provider packets;
later archive records are not merely hidden by a prompt instruction.

With background storytelling disabled, explicit `POST action: "step"` on the
track's story endpoint executes one job from that track's specified round. It
refuses an unfinished RCA revision and never invokes the RCA queue. Story memory
includes earlier applied answers and completed sibling answers. Qwen uses the
existing non-thinking inference profile; its selected passages and provider
attempts are retained. There is no new token, context, question-count or runtime
quota.

After inspecting and freezing the output, `apply` can include a list of original
record attachments as `{sourceId, questionId}` pairs. Each must belong to that
round's question and release allowlist. These exact original records are preserved
as question-scope documents before the answers enqueue **one** new RCA revision.
The record selection is operator-controlled; it must not be scored as the
storyteller's autonomous document-selection success. Repeat application of a
queued/applied round returns that revision; it must not create another version.

An optional `approvedQuestionIds` selects an explicitly reviewed nonempty subset
without changing any generated answer. The full candidate is retained alongside
`releasedOutput` and `withheldQuestionIds`. Future story memory uses only the
released subset. The simulator displays withheld candidates separately from
released answers; a schema-valid response is not automatically a semantic pass.

An optional locked scenario `releaseFormat: "case-content"` omits the benchmark
boilerplate from delivered answers, retaining the answer, source IDs/titles, exact
quotations and substantive limitations. Scenario/provenance stays in the private
story workspace and operator receipts; no hidden answer key is appended. Existing
scenarios retain their previous benchmark format.

The IA-16036 V2 protocol and prewritten expectations are in
`evals/ia16036-v2-expectations.md`; `scripts/controlled-story-v2.mjs` provides explicit
prepare/create/generate/answer/freeze/apply commands. It has no automatic release
or next-version loop. These are delivery changes, not corrections to the RCA
model's conclusions.

Open an Ollama track on the investigation dashboard and select **Story simulator**.

1. Load the R3 starter or import a scenario JSON. Review its private facts and releasable source excerpts, then lock it. The model is inherited from the selected RCA track.
2. Generate a batch. A fresh request to the same Ollama model receives the fixed scenario, pending questions, prior released story answers, and existing user answers. It receives no causal board or RCA model messages.
3. Review proposed answers and exact source quotations. Nothing is sent back to RCA until you release the batch.
4. Release it to run one RCA cycle and save one new version. Repeat from the new version. Previous versions remain unchanged.

## Code map

- `app/story/`: evaluator workspace and styling.
- `app/api/tracks/[trackId]/story/route.ts`: create, generate, apply and read routing.
- `src/story-agent/contracts.ts`: scenario/output schemas, pending-question selection, citation checks and release formatting.
- `src/story-agent/run.ts`: isolated provider call and context guard.
- `src/story-agent/repository.ts`: scenario lock, durable memory and round lifecycle.
- `src/story-agent/r3-template.ts`: controlled R3 seed, derived from the benchmark fact registers. It is not a replacement for original partner evidence.
- `prompts/story-agent/system.md`: dedicated role instructions.
- `src/server/repository.ts`: `addTrackAnswers` batches evidence into a single RCA cycle.
- `db/schema.ts` and `drizzle/0002_slow_gauntlet.sql`: additive persistence. The generated migration excludes checkpoint definitions already covered by the existing `0002_stage_checkpoints.sql` migration.

## Boundaries and limitations

The two roles share model weights, but not conversation state. This reduces direct information leakage; it does not make their judgments statistically independent. The evaluator can see the hidden scenario in this local app. There is no access control or production isolation.

Only released answer text and cited excerpts enter the RCA evidence packet. Answers are labeled simulated, and source classes distinguish historical summaries from controlled derivatives. Unknown/partial responses are retained without automatically marking the question answered. Previously supplied exact question IDs are not automatically asked again; the RCA can raise new follow-up questions.

Validation checks exact quotations, source availability, unique question IDs and complete batch coverage. A rejected citation/coverage batch gets one correction attempt using the same model; structured-output repair may also occur inside the provider. Attempts that reach this validation are preserved with the round, including a final validation failure. These checks do not prove the prose is supported or free of hidden-truth leakage: review is still required. The scenario is locked, so the storyteller cannot improvise new physical facts to satisfy an investigator. Existing user answers are claims, not authority to rewrite that world.

The simulator supports text/excerpt sources and scenario JSON import—not automatic document generation, original-file ingestion, or scenario expansion. Large contexts fail explicitly instead of silently truncating memory. Generation now handles every pending question in a separate sequential same-model request; this is transport chunking, not a limit on the number of investigation questions. Each request sees the locked world, prior released answers and validated answers from the current batch. The model selects IDs from an exact-source passage catalog. The harness inserts the corresponding quotations and still validates coverage and source availability. This prevents quotation transcription errors, but does not prove that the answer's prose is entailed by the selected passages.

## Unattended four-version experiment

`node scripts/launch-qwen-story.mjs` starts a detached local runner and, if necessary, local Ollama/app services. Run this only when a new experiment is explicitly authorized. It creates a NEW incident, with Qwen 3.5 in both isolated roles, existing default references and the three R3 starter PDFs. It does not resume or overwrite older incidents.

The driver `scripts/autonomous-qwen-story.mjs` stores IDs before inference using deferred incident creation and `/api/tracks/[trackId]/initialize`. It commits V1, then automatically generates and releases three validated story batches to produce V2–V4. Strict commits require all executed stages to succeed, a model-produced causal board and completed causal verification. Causal certainty, accepted causes and corrective actions are NOT prerequisites: unknown and disputed findings must remain honest. Failed stages are retained as checkpoints, not counted as successful causal versions. Providers allow at most two attempts within the failed stage or broker batch. Strict runs stop immediately after an unrecovered stage failure; neither the repository nor the driver automatically replays a whole RCA cycle. Story generation retains its separately bounded two-request policy. Uncertain mutations are never blindly repeated. No model substitution or fabricated answers are permitted.

Artifacts live under `R3 Benchmark Package/06_run_records/qwen-story-autonomous-*`: frozen code/prompts and hashes, input/model manifest, old-version hashes, private scenario, request/response records, raw storyteller attempts, immutable version snapshots, `state.json`, and final `result.json` or `failure.json`. A code change, exhausted question set, unresolved execution failure or 24-hour deadline stops the run visibly; four versions are never manufactured by padding or forced conclusions. `caffeinate` prevents idle sleep for the runner's lifetime; the Mac must remain powered and available. The runner completes without a coordinating model answering questions or altering the story. A separate thread heartbeat reads completion/failure only and performs the post-run assessment after V4.

Causal prompts are versioned `try4.2.3-explicit-focal`. Type labels are kept out of titles; narrow prefix normalization is logged alongside raw model output in causal-analysis checkpoints. Previous-board input is labeled as interpretation, not evidence, and cleaned in a copy without changing historical snapshots. Evaluate raw compliance separately from normalized display quality.

The causal output requires an explicit `focalEvent` object instead of a model-generated `focalKey` pointer. The application materializes that object's reserved `focal` key and `focal-event` type; Qwen still authors its proposition, evidence status and citations. The other-node array excludes the focal event and retains the existing overall limit of 18 nodes (one focal plus up to 17 others). Edges must reference `focal` or a unique other-node key. Duplicate keys, blank propositions and dangling endpoints still fail validation, and the provider retains its two-attempt limit. No historical output is migrated, no old ID is guessed or repaired, and all original raw responses remain preserved. Schema validity does not imply causal truth or verification. The four-version automation remains paused until explicitly restarted.

## Stage recovery

`src/stages/causal-analysis/reference-contract.ts` checks focal references, unique node keys and edge endpoints before mapping the board. A defect returns to the same provider's bounded repair loop, with the exact validation error. The harness never guesses the intended focal event, silently drops a dangling reference, or changes causal claims to make an execution pass.

`src/stages/causal-verification/reference-contract.ts` resolves the board IDs actually sent to the verifier, also accepting valid legacy model-local aliases. Unknown targets and invalid edge indexes are rejected in the same stage's repair loop. An explicit blocking finding prevents the affected node/edge from being marked verified even if another output field contradicts that finding; raw output remains preserved for review.

`src/stages/causal-verification/output-schema.ts` constrains newly generated verification IDs to the exact board node/edge catalog and edge indexes to valid integer positions. An edgeless board permits only an empty verified-edge array. The harness never repairs a node/edge prefix by guessing its intended target. Successful verification checkpoints retain the raw model output and provider attempts alongside the mapped board, just as failures retain their attempts. This closes the free-form-reference gap observed in `qwen-story-autonomous-CDH6if` without changing the verification evidence standard.

`src/stages/question-broker/batches.ts` processes four candidates per request against pages of sixteen retained questions. These are transport bounds, not a cap on the overall question set. Compact keep/covered decisions retain the original questions and evidence boundaries. Every candidate is accounted for; the request-specific schema enumerates legal IDs, coverage owners must exist, cross-page chains resolve to a retained question, and answers route to all affected specialists. Partially overlapping questions stay separate. The broker cannot screen out a question because evidence is missing; answering and fact evaluation remain separate stages. Accepted batches and raw provider attempts remain available in checkpoints; an invalid batch retries locally and cannot silently disappear. Final deterministic deduplication requires the same wording, intent, branch, decision and evidence requests, not merely the same intent label.

The request schema also binds each candidate to its legal disposition/owner combinations: keep requires an empty owner; coverage excludes self and later candidates; answered candidates permit only keep. These are nested schema alternatives, not post-hoc rewrites of model decisions. Cross-row completeness and whether an earlier owner was actually kept remain runtime checks. This closes the schema/runtime gap observed during the first storyteller update in run `qwen-story-autonomous-A8rNaX`.

This separates schema conformance from application invariants and splits oversized work into smaller subtasks, following the [Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs#handling-mistakes). The implementation remains provider-neutral and uses the selected Qwen model unchanged.

Run regression checks with `node --experimental-strip-types --import ./scripts/register-test-loader.mjs --test scripts/stage-recovery.test.mjs`. The loader supports the existing app aliases and raw Markdown imports without changing production code or installing a new test framework. For an explicitly authorized, isolated live-stage check, use `node --experimental-strip-types --import ./scripts/register-test-loader.mjs scripts/verify-qwen-stage-recovery.mjs --live`. This reads the failed initial packet, calls only Qwen's broker/causal/verification stages, and saves separate diagnostics; it does not create an app incident or a committed version. It is not a substitute for the full four-version storyteller experiment.

Round states are generating, ready, applying, applied and failed. Failed generation can be retried. Duplicate application of an applied round returns the saved version. Stale batches cannot overwrite a newer RCA version. A crash during an active request can leave a generating/applying round requiring operator recovery; background job recovery is not yet implemented. Avoid restarting the server during a run.

## Checks

`node --experimental-strip-types --test scripts/story-agent.test.mjs`

`npx tsc --noEmit`

Build using the project's existing build command. The eight contract tests cover missing/duplicate responses, unknown outcomes, source restrictions, excerpt checks, release formatting, question selection and Ollama-compatible text bounds; they are not an end-to-end RCA-quality evaluation.

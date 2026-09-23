# Try 5.2 — reliable evidence-first execution

This revision keeps the existing UI, separate model tracks, specialist knowledge,
question routing, and board representation. It changes the execution boundaries.

## Storage and recovery

- `src/engine/tasks/artifacts.ts`: lossless, immutable content-addressed JSON chunks
  (at most 12,000 UTF-16 code units each); independent collection checkpoints.
- `engine_runs`: small input/state/snapshot references, lease, generation, status,
  and stop reason. A reference publishes only after its chunks are durable.
- `engine_calls`: exact prompt, selected evidence, local JSON grammar, output budget,
  response/result reference, and error. Streaming text is appended independently
  before parsing. Inspect it from the task's dashboard link.
- Saves use lease/generation guards. A manual pause revokes the lease. Its in-flight
  request is aborted on the next five-second heartbeat. An emergency small write
  pauses a run when its normal checkpoint fails. If even that fails, the polling
  process stops rather than repeatedly issuing inference.
- Old inline checkpoints remain readable. Resuming a different engine version is
  rejected: create a fresh experiment rather than mixing code identities.

Artifacts are not deleted automatically. Interrupted unpublished chunks can remain;
retention/garbage collection and production authentication are separate future work.

## Model tasks

- Evidence reading sees only its selected original passage, with preserved table
  headers and offsets. Original full documents remain in the archive.
- Exact per-call reference enums separate sources (S), findings (F), and duplicate
  questions (Q). Explanations cannot be appended to citation strings.
- Review names and echoes one exact target statement. Support for an observation
  is judged separately from knowledge of the root cause. A distinct causal-role
  assessment keeps pure document metadata out of physical causal scheduling.
- Dependencies represent actual target producers/reviewers, not all tasks sharing
  any retrieved passage. Failed read/understand/tag prerequisites pause the run.
  Independent local failures remain partial and cannot feed dependent causal work.
- Ollama streams with one attempt, no silent truncation/context shifting, and a
  three-minute *idle* watchdog instead of a total-runtime timeout. Managed calls
  receive the remaining configured context after conservative input/media/schema
  estimation and overhead. There is no fixed 3,200-token engine output ceiling.
  Context estimation is not exact tokenization; the real model context is finite.
  Context exhaustion stays a visible failure, never a completed partial JSON answer.
- Closed-source adapters retain complete returned responses too. Their live
  capabilities/limits are not established by the local Qwen evaluation.

## Controlled launch

Initialization accepts `{ "reviewAfterReading": true }` and acknowledges the frozen
setting in its response. The evaluation launcher verifies this acknowledgement.
`RCA_REVIEW_AFTER_READING=true` is an optional default, explicitly forwarded into
the development worker. After inspecting the notebook, use the dashboard
approval/resume control. `RCA_STORY_ENABLED` defaults off; the simulator does not run
unless deliberately enabled. No hidden evaluator material belongs in model inputs.

Automated regression tests establish execution invariants, not RCA scientific quality.
The fresh IA-16036 B0 Qwen run is the separate live model evaluation.

## Live-evaluation corrections

Try 5.2.1 includes the JSON output contract in Ollama's actual prompt, not only its
decoder grammar. The reading mission explicitly requires reference/requirement
knowledge even when a source describes no failure. Output examples are generic,
not an IA-16036 answer key.

After the first read round, optional question rejections were separated from primary
evidence failures. A malformed optional question remains quarantined and visible;
it does not invalidate successfully extracted findings. Resuming an unpublished
checkpoint produced by the old classification retains those findings without
resampling them and records the recovery in the change log. An actual extraction,
contract, source-reference, or storage failure still blocks dependent work.

Artifact chunking preserves Unicode surrogate pairs at boundaries. This was tested
with an intentionally boundary-crossing supplementary character and a payload over
the D1 limit. Existing ASCII/BMP artifacts remain readable; new artifacts use a
new content-address prefix. No original evaluation documents were rewritten.

## Repetition and single-task recovery

`src/providers/stream-repetition.ts` scans streamed JSON incrementally. Three
consecutive complete root-array records that have already occurred, without an
intervening new record, stop the provider request. Canonical key ordering permits
comparison without erasing differences in subjects, times, locations, qualifiers,
references or array order. This detects exact-record loops, including cycling
between several records; it does not claim semantic/paraphrase-loop detection.
It does not impose a question count or reduce the configured output allowance.

The triggering raw text is retained. Incomplete JSON is never silently repaired or
accepted, and this error is not automatically retried with the same prompt. The
worker pauses with the affected task recoverable and previous completed work intact.
Specialist instructions explicitly ask for distinct additions or substantive
revisions, allow empty findings/questions, and say to finish rather than fill the
token allowance. Assigned target references are distinct from nearby context.

For an inspected paused run, `POST /api/tracks/:trackId/resume` accepts an optional
body `{ "taskId": "...", "pauseAfterTask": true }`. It runs that task only and
pauses after its result is committed. Already completed tasks cannot be resampled
in place; unresolved prerequisites must be recovered first. Resuming without a
body continues normally. State changes and old call traces remain inspectable.

The compatible checkpoint format remains `try5.2.1`; each new Ollama request/cache
identity additionally records `streamPolicy: json-array-repetition-v1` and its
exact prompt. A run changed in place is a disclosed recovery evaluation, not a
frozen-policy performance comparison. After Markdown prompt changes, restart the
local server: live observation showed that raw prompt imports can remain stale
despite TypeScript hot reload. Confirm the actual prompt in the saved request.

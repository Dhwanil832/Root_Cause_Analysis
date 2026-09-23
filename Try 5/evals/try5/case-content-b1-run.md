# Fresh case-content-only V1 — 2026-09-20 UTC

## Identity

- Incident: `e99d24d6-753c-427a-9304-cdbd6726090f`
- Track: `3ef34107-57cc-4426-a284-aa600f37ce1a`
- Run: `4866969b-2dea-41ed-9b45-acb2de6fba9c`
- Dashboard: <http://localhost:3015/incident/e99d24d6-753c-427a-9304-cdbd6726090f>
- Launch artifacts and frozen code/input hashes: `outputs/case-content-b1-tXhczz/`
- Engine: `try5.2.3`; model: `ollama:qwen3.5:latest`, same frozen digest as the earlier run.

The user requested removal of simulation disclaimers and explicitly selected a
fresh V1 rather than continuing the existing track as V2. This is a new cumulative
B0+B1 investigation, not the original B0-to-B1 staged benchmark.

## Controlled input changes

Derived input view: `../IA-16036 Controlled Evidence Package/07_case_content_inputs/`.
All 18 package records have a prepared view; **only B0+B1** (incident and ten
documents) entered this run. Original labeled records are unchanged. The operator
manifest/provenance retain their synthetic status and exact text replacements,
but are not model input. No general-purpose evidence-stripping rule was added.

Removal is limited to the exact listed simulation metadata. Unverified testimony,
selected-sample coverage, missing photographs, documentary scope and all other
substantive qualifications are preserved. Table rows are byte-identical to the
originals. No causal answer or physical event was added.

Live immutable input inspection confirmed:

- No simulation-disclaimer terms in the incident or ten document texts.
- All document content hashes belong to the prepared B0+B1 set.
- Three reference, three starter and four question-scope documents.
- Zero supplied answers and no old findings, questions or board imported.
- Native starter/reference extraction trims the final newline; all content matches
  the prepared files after outer-whitespace normalization. B1 text matches exactly.
- No B2/B3, answer bank, ground truth, rubric, earlier outputs or storyteller input.

## Execution boundary

The previous run `657cb4b7-42e2-4ca0-8d74-0d62ff4c07f6` was paused through the
application API, with its saved board/findings retained and in-flight inference
cancelled. The older B0 run also stays paused. The launch receipt verifies both
paused run rows were unchanged by creation of the new test. Only the new run is
eligible for model execution.

The shared reference library remains unchanged. The application now supports
explicit incident-specific reference files and excludes them from the global
library list, preventing this experiment's cleaned reference copies from leaking
into unrelated incidents. No review/causal prompt or model profile was changed.

This run uses the current generic progressive-board scheduler from the start.
It is not a return to the original specialist-first scheduler. There is no manual
claim selection or operator verdict insertion. The reading-approval checkpoint
is disabled; manual pause and evidence-validity checks remain. No model preflight
was run. Type checking passed; lint reported no errors and one unused-variable
warning in the package-preparation script.

## Initial observed progress

At 2026-09-20 01:15 UTC the first reading task had completed, producing seven
proposed findings; the next reading task was running, with zero reused tasks.
This confirms execution, not evidence accuracy or causal acceptance. Inspect the
saved outputs before claiming the disclaimer change improved reasoning.

## Attribution

The previous first board was obtained after operator changes to execution limits
and scheduling. Its node and verdict were model-generated, but its emergence
does not prove that the original end-to-end workflow worked autonomously.
This fresh run tests the current engine with changed evidence presentation.
Record all further interventions here; do not silently modify saved outputs.

## Explicit formatting guardrail activation — 2026-09-20 06:20 UTC

The user explicitly approved activating the `None` guardrail for the remainder
of this V1, not only future runs. Policy: `explicit-no-missing-premises-v1`.
New revisions freeze this policy into input; this existing V1 keeps its original
input unchanged and records the activation separately in
`state.reviewFormattingMigrations`. Review cache identity includes the policy;
task identity does not change, so completed reviews are not scheduled again.

The guardrail removes exact whole-entry empty markers from `missingPremises`
(for example `None`), then runs all existing consistency, target and original
source-line checks. It does not coerce malformed structures, remove genuine
qualifications, turn unknown into supported, or repair an inconsistent verdict.
The recorded phrase `None for establishing the record observation itself` is
recognized only for a `record-observation` review. Raw model output is unchanged.

One saved review was revalidated without a model call:

- Task: `c9abbdd0329803fc98a3e04ffa0ad8be36744a4c3a422529f667dc0eb56d0948`
- Original failed call: `fbe7c433-9146-4c72-a413-423795cb5703`
- Claim: `Local indication returned to normal band.`
- Reviewer scope remains `record-observation`; this is not a new determination
  of physical recovery or causation.
- The formatting-only question
  `bf61b605-b8d4-4598-a5dd-6e4bed1a52a0` was retired from the active queue. The
  exact old question, failed review, and completed broker work remain preserved
  in the checkpoint/trace audit. No user answer or incident evidence was removed.
- The original response's two actual follow-up questions were restored through
  normal question ingestion. They are questions, not established facts.

The activation committed at `2026-09-20T06:20:13.061Z`, generation 540. Its audit
contains the full pre-activation row and content-addressed checkpoint pointers.
The old state pointer is
`json-u2:e8cca23ed8ae022e7933fadb2de7f21ecf9175299f4bc361b56096b57d85b5f0`.
Read-only verification confirmed the input and sources were unchanged, all 263
previously completed tasks were byte-for-byte unchanged, and the original failed
trace still contains the unmodified missing-premise text. The five unrelated
failed tasks were not repaired, hidden, or resampled. Older protected runs remain
paused at their prior generations (107 and 49).

Operational interruption: the first activation helper wrote through native SQLite
at an idle task boundary. Although activation committed, the application worker's
next claim returned `SQLITE_BUSY` and its existing fatal-HTTP policy stopped the
local app. The app/worker was restarted from the saved checkpoint; subsequent
causal and verification tasks completed. The reusable helper was then changed to
read-only SQLite inspection plus the application's D1-backed activation endpoint.
It no longer writes to the live SQLite database from another connection. No
in-flight inference was cancelled and no completed model work was rerun.

Validation: eight focused deterministic tests passed, including raw-response
preservation, genuine caveats, mixed empty/genuine entries, provenance failures,
legacy isolation, immutable backup, stale/active/published checkpoint rejection,
and no duplicate review scheduling. Type checking and scoped lint passed. This
is validation of the formatting guardrail, not proof of RCA quality or completion.
The proposed broader “defer and track failed items” mechanism was discussed, not
newly implemented by this change.

# Pinned causal-board comparison

The first card on `/history` opens the original investigation while its controlled
V2 is processing, and `/history/causal-comparison` once it publishes. The viewer
provides V1, V2, and side-by-side views of preserved outputs. Opening the viewer
does not run a model or modify a board. All other investigations remain below it.

- `src/history/featured-comparison.json`: case, model, source IDs, source hashes,
  counts, and provenance for the pinned card.
- `public/history/featured-causal-boards.json`: exact saved board objects for
  display and download; no prompts, provider credentials, or hidden answer keys.
- `app/history/causal-comparison/page.tsx`: read-only comparison viewer.
- `app/incident/causal-canvas.tsx`: existing canvas with optional read-only mode,
  independent arrow markers, compact archived layout, and fit-to-width controls.

Try 5 now pins the user-selected **IA-16036 · Clean-input B0+B1 · Qwen ·
2026-09-20T01:14:32.289Z** investigation. The prior diagnostic-only comparison is
backed up under `evals/clean-input-v2-controlled-2026-09-21/previous-pinned-*`.

Its V1 was operator-frozen as a partial checkpoint on 2026-09-21, preserving its
32-node, 8-edge board, original input, full state and unfinished queue exactly.
Only execution/publishing metadata changed; it is not a completed V1.

V2 receives four assistant-authored, source-grounded answers and three unchanged
B2 records (IA-P04, IA-P05 and IA-P06). It uses the same Qwen digest, production
task prompts, executor and evidence gates, with the disclosed `selected-answers-v1`
scheduling policy: answer selected questions, review relevant findings, map those
findings, verify retained nodes, then verify links. New questions stay visible for
later releases instead of restarting V1's broad queue. The result is partial by
design, not a full RCA or an unchanged-scheduler benchmark. No storyteller was
used. Private review criteria and B3 evidence are not model inputs.

The script `scripts/controlled-evidence-revision.mjs` prepares the guarded
transaction, can run this one revision, and offers a read-only `watch` mode when
the existing app worker already owns it. The watcher refreshes the comparison
from real saved snapshots and stops on completion or pause. Parent board/state/
input hashes are checked; no board wording or verdicts are fabricated.

The first-card ordering is independent of incident timestamps. A new incident
does not push the pinned comparison down. Archived layouts are saved per version
in the browser and do not alter the investigation. Original runs are accessible
through the viewer's link.

Verification from this app folder:

```sh
node --test scripts/featured-comparison.test.mjs
node_modules/.bin/tsc --noEmit --incremental false
```

The provenance test reads original artifacts from the enclosing RCA workspace,
compares SHA-256 values, and checks exact board equality. Browser checks cover
history navigation, both-board display, individual version switching, and the
absence of review actions. All three app viewers were checked on 2026-09-21.

# Pinned causal-board comparison

The first card on `/history` opens `/history/causal-comparison`. It provides
V1, V2, and side-by-side views of preserved outputs. It does not run the model,
insert new investigation versions, change history timestamps, or modify source
boards. All existing investigations remain below it.

- `src/history/featured-comparison.json`: case, model, source IDs, source hashes,
  counts, and provenance for the pinned card.
- `public/history/featured-causal-boards.json`: exact saved board objects for
  display and download; no prompts, provider credentials, or hidden answer keys.
- `app/history/causal-comparison/page.tsx`: read-only comparison viewer.
- `app/incident/causal-canvas.tsx`: existing canvas with optional read-only mode,
  independent arrow markers, compact archived layout, and fit-to-width controls.

Try 4 uses the R3 Qwen follow-up V1/V2. Try 6 uses the published IA-16036
partial V1/V2. Try 5 uses the corrected baseline and controlled-document pilot
snapshots. **Try 5's V1/V2 are explicitly display labels, not published app
versions.** No complete investigation or new model performance is claimed.

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


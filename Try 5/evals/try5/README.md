# Controlled Try 5 evaluation

No full-investigation benchmark score is recorded yet. Deterministic engine tests are operational checks, not benchmark results. The latest failure-containment and bounded-board record is `review-gap-board-results.md`; `literal-review-results.md` preserves the earlier semantic comparisons. The production investigation remains paused. The preceding two-stage candidate was rejected after 18 cases in `fixed-meaning-results.md`. Earlier checks remain in `claim-review-recovery-results.md` and `claim-parts-results.md`. None substitutes for a successful full RCA.

Use one incident and one Qwen track. Keep the recorded digest/context with the output. Attach only intended reference/starter records. Before V2, privately specify what its evidence should establish, contradict, leave unknown, and preserve from V1. The existing IA-16036 package is the proposed starting point; never upload its evaluator rubric as investigation evidence or storyteller context. Production logic has no IA/R3-specific rules.

Release the controlled answer/document into the same track. Preserve both version exports. The read-only export script prints selected-track data and operational metrics without inference or grading:

    node scripts/export-engine-run.mjs INCIDENT_ID TRACK_ID

Operational checks: execution state, failures/quarantine, source coverage, reuse, tokens/durations, valid original citations, stable IDs and stale-result prevention.

Scientific checks require original-source inspection: recover answerable facts; join instrument/location/time correctly; preserve procedure alternatives; distinguish absent records from absent controls; identify contradictions; justify mechanisms against alternatives; avoid inventions; retain useful unrelated branches. An empty/all-unknown board cannot pass when the package contains answerable facts. Same-model review is not independent corroboration.

After that gate, select a small question batch on the Story page, inspect its answers and release it. Score story-answer faithfulness separately from RCA use of those answers. Four versions and a held-out incident are subsequent demonstrations, not implied by passing code tests.

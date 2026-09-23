# Checkpoint restart and generalization boundary

## What is preserved

- Original source evidence, incident text, model configuration, 96 claim records
  and four prior answers; no new storyteller/evidence generation.
- Ten completed discovery calls, reused as **draft candidates**, not verified facts.
- Previous boards, failed attempts, source prompts and model responses for audit.
- Pre-change source/prompts/scripts: `../IA-16036 Controlled Evidence Package/
  06_run_records/preserved-before-4.3.6-3NEIXX/`.

## Active experiment

`../IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-consolidated-btG98n/`

The isolated replay writes `phases/`, checkpoints and model-capture records. It
does not update the app database. `result.json` means it completed; `failure.json`
records a terminal failure. Neither a running process nor a larger graph proves
RCA quality. Use the read-only `inspect_consolidated_restart.mjs` tool for status.

The preceding attempt `qwen-v2-consolidated-2c95T4` demonstrated an overly strict
cross-field validator: an unused proposition on a question could fail a batch.
That was corrected with disposition-based consumption and local quarantine.
Only valid matching completed calls are reusable. Failed outputs are not silently
reclassified as successful checkpoints.

## General system contract

IA-16036 is one fixed regression case, not a hard-coded causal template. Production
logic contains no expected cause, pressure value, plant-specific component rule,
benchmark document identifier or desired score from this case. Model/digest and
evidence-count assertions live in the isolated experiment runner, not the pipeline.

The reusable changes are typed evidence routing, proposition consolidation with
complete candidate accounting, non-Cartesian linking, stable relationship identity,
source-grounded verification, explicit unknowns and local failure isolation.
Prompts remain separated by responsibility and providers remain replaceable.

## What still needs demonstrating

1. The completed board's statements and arrows are justified, not merely valid JSON.
2. Relevant differences in a new evidence release cause substantive, traceable
   revisions while unresolved branches remain visible.
3. Unseen mechanical, electrical and human-injury cases work without case-specific
   prompt changes or expected answers supplied to the model.
4. Larger archives, conflicting documents, misleading labels, incomplete answers
   and malformed outputs do not silently drop evidence or halt unrelated work.
5. Other models/providers satisfy the same behavioral contract. A successful Qwen
   run is not proof of provider-wide robustness.

Known boundaries: lexical working-set selection can miss relevant records;
coverage reporting is not a recall guarantee. An indivisible request that cannot
fit is reported rather than silently truncated. Exact quotation checking proves
traceability, not entailment. Model-written consolidation and verification still
require quality evaluation. Training, provider combinations and new evidence
generation are not part of this restart.

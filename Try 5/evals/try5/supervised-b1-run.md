# Supervised cumulative B0+B1 investigation — 2026-09-19

## Identity and boundaries

- Incident: `de15cf4d-f68b-44f9-b674-f244e444a3b4`
- Model track: `409e23c6-7255-4b3f-bd7f-f537d864fedd`
- Engine run: `657cb4b7-42e2-4ca0-8d74-0d62ff4c07f6`
- Engine: `try5.2.2`; Qwen `ollama:qwen3.5:latest`, frozen digest in launch receipt.
- Dashboard: <http://localhost:3015/incident/de15cf4d-f68b-44f9-b674-f244e444a3b4>
- Artifacts: `outputs/supervised-b1-GuucnZ/` (launch receipt, source/code hashes, frozen operator review plan).

This is **V1 of a new supervised cumulative B0+B1 track**, not V2 of the original
B0 experiment. The old checkpoint uses an incompatible engine version and stays
paused, byte-for-byte unchanged. It has not been relabeled, migrated, or resumed.
This case is a historically anchored synthetic reconstruction, not original plant evidence.

The model receives the incident description and ten documents: three default
references, three starter records, and four scheduled B1 records. B1 attachments
retain the app's `question` evidence scope but have no invented question ID or
operator answer. Their original Markdown bytes are preserved in R2 and verified
against the package hashes. All four were attached before one revision was queued.
The desk message uses its neutral filename, without evaluator/challenge labeling.

B2, B3, answer banks, ground truth, review criteria, previous model outputs and
storyteller responses are **not** model inputs. The storyteller is disabled.

## Execution and attribution

The production planner, provider, prompts, schemas and evidence-review behavior
are frozen. This is the full existing pipeline, not a three-finding pilot or a
manually authored board. The launcher is an operator-only adapter; it is not a new
reasoning strategy and does not modify existing run rows.

The original-document reading checkpoint is enabled. Review findings against
their original documents before resuming. Resume does not mean accepting every
claim or providing additional incident facts. Do not silently repair returned
claims, inject evaluator answers, enable fallbacks, or count operator work as
Qwen's achievement. Record any further intervention here before making it.

No B2/B3 release until the first board is inspected. Task completion, semantic
accuracy, causal completeness and human approval are separate outcomes.

## Launch observations

- The first background shell launch exited before serving HTTP; no inference ran
  under it. Starting the app in a persistent terminal session succeeded.
- The first model call completed and subsequent reading calls progressed without
  a failed task. This is not a causal-analysis acceptance result.
- Browser verification confirmed the new incident, one Qwen track, the 3/3/4
  document scopes and live engine progress.
- UI caveat: a legacy line says `Execution: completed` beneath the live engine
  section while the run is still running. The engine status, pending canvas and
  task records are authoritative. Do not use that legacy line to claim completion.
  No UI patch was made during this frozen run.

## Original-document checkpoint review

At generation 23 the engine paused at its intended reading checkpoint: 11/11
read tasks completed, 88 proposed findings, no failed/blocked tasks, no causal
nodes or relationships yet. Three questions from the work-package reading were
quarantined because their required `decision` field was blank. The primary
readings were retained; no retries were issued to regenerate them.

The operator read all 88 statements and their time fields against the released
sources. The following issues are recorded **outside model input** for subsequent
review. This is not a clean semantic acceptance result.

| Finding | Observed issue | What the later review must not do |
| --- | --- | --- |
| `094ffee1-9452-4e31-b145-e5082ce4aa24` | Calls U-A and U-B “teams”; the records identify two individual operators. | Accept the invented entity type as an established fact. |
| `04e569b5-296a-4d04-9842-39c8d0e03370` | Says P-U was 6.9 through the sampled interval, omitting the 6.8 reading at 10:01:10. | Promote exact constant pressure or continuous coverage from those samples. |
| `bff76ee8-0d02-4bc6-ac74-e9645a556290` | Statement refers to notification time; structured time field instead contains the 09:31 folder-issue time. | Conflate document-issue time with the observed work-stage time. |
| `f9651deb-54a0-45b3-ae30-3eea9a2e844b` and other IA-C01 entries | Several structured time fields reuse the recalled 10:03 acknowledgment time for observations not separately timed. | Treat that recalled timestamp as independently established timing of every statement. |

Useful retained content: P-R drop/recovery, distinct alarm occurrence and
acknowledgment times, P-U/P-R point locations, C-11 RUN's non-flow scope, AL-44's
P-R input despite its display label, work-document index contents, and the desk
message's secondhand/unverified basis. Extraction is not exhaustive: for example,
some requirement qualifications are available in the original source but not
separate findings. Original spans remain available to downstream tasks.

**Operator decision:** resume the existing frozen pipeline to evaluate whether
its own review and causal stages handle the proposed findings appropriately.
This is permission to continue the supervised experiment, not human acceptance
of the 88 findings. No statement/status, source, answer, prompt or model setting
is edited. The review notes above are not passed to the model. No B2/B3 release.

## Inspection / recovery commands

## User-authorized continuous execution and faster V1 — 2026-09-20 UTC

The maintenance/outage call `4ab1ace9-e0d4-4208-9114-1ea1d5a4544b` triggered the
former three-duplicate-record abort. Its partial response was retained, not
applied. At generation 96 the investigation was paused with 46 completed tasks,
202 proposed findings, 26 questions, and no causal nodes/links.

The user explicitly requested removal of the stopping limits and faster V1
results. This ends the frozen execution-policy comparison; the same investigation
continues as an **audited, supervised harness-modified V1**, not a new V2 or an
unmodified acceptance run.

- Engine execution migrated explicitly from `try5.2.2` to `try5.2.3` on this run
  only. Immutable input JSON, findings, completed outputs and previous call traces
  were preserved; other runs were verified unchanged.
- Backup and receipt: `outputs/continuous-recovery-8OBju4/before.json`,
  `backup-manifest.json`, `receipt.json`.
- Pre-change checkpoint hash:
  `894881120d5f0993e5ab6d472e596a6bf44adb563ddb83f73e3f34f1fb422453`.
- Repetition is recorded as telemetry, not a generation abort. Ollama generation
  uses `num_predict=-1` for durable engine calls, with no default idle deadline.
  The real 32,768 context setting and no-truncation/no-shifting behavior remain.
- Removed the 1,800-character natural-language schema ceilings and the one-late-
  follow-up-pass cutoff. Exact source-ID and evidence-validity checks remain.
- Individual incomplete/invalid/over-context responses are failed locally; unrelated
  tasks continue. Provider/identity/storage failures and missing foundational
  evidence still cannot be treated as valid results.
- The migrated run no longer has an automatic reading/recovery approval checkpoint.
  Explicit user pause/cancellation still works.
- Original-source findings relevant to the focal event are now prioritized through
  independent claim review, causal mapping and node verification. No incident IDs,
  equipment identifiers, expected causal answers or private rubric enter the scheduler.
  Unfinished specialists/questions remain in the queue; the early board is provisional.
- No prompt text, model identity, sampling profile, source document or user answer
  was changed. The storyteller remains off; B2/B3 remain withheld.
- Fixed the contradictory dashboard `Execution: completed` line so a running
  checkpoint is visibly provisional, not presented as a completed RCA.

Ten focused deterministic checks passed (no LLM preflight calls), including
continued generation past 50 repeated records, local response failure isolation,
preservation of the same V1 during migration, progressive board scheduling and
manual recovery. Type checking passed. These verify implementation behavior,
not Qwen's RCA quality.

Live execution resumed: the first priority call reviews the original P-R
drop/recovery statement. Its trace records engine `try5.2.3`, unlimited application
output setting, the observation-only repetition policy and the unchanged native
Qwen review profile. No causal result was claimed at the time of this note.

## First live board output — 2026-09-20 01:04 UTC

The priority sequence completed: claim review
`8d993e50-bef5-4643-ba9e-8402d01a4d08`, causal proposal
`305eb7be-0f1f-4237-8d4f-9235644fec6f`, and node verification
`1929ef0f-57cc-4e71-8196-c8b2ffb8f303`. The canvas now displays the focal event,
one model-supported P-R drop/recovery node, and one proposed link. Browser
inspection confirmed this is visible, labeled Pending V1, with approvals disabled.
The worker proceeded to review the original P-U statement without intervention.

This is execution progress, not semantic acceptance. Operator concerns: the link
largely restates the focal pressure-loss event; the causal gap description
overlooks available selected P-U readings; the reviewer treats the synthetic
disclaimer as an unnecessary evidence conflict; its selected line citations omit
the 2.1-bar row even though the full source passage includes it. These observations
are not injected into model input. No model record was manually corrected.

Readable first-results snapshot:
`outputs/supervised-b1-GuucnZ/V1-first-results.md`.

## Superseded for active testing — 2026-09-20 UTC

The user requested disclaimer removal and chose a **fresh V1**. This existing run
was paused through the application API, preserving the original inputs, findings,
board and traces. Its in-flight call was cancelled, not treated as a completed
result. No disclaimer edits were applied retroactively to this run.

New run: `4866969b-2dea-41ed-9b45-acb2de6fba9c`.
See `evals/try5/case-content-b1-run.md` for the new input view and launch record.

## Inspection commands

From Try 5:

```sh
node scripts/inspect-engine-run.mjs 657cb4b7-42e2-4ca0-8d74-0d62ff4c07f6 --findings
node scripts/verify-pilot-checkpoint.mjs outputs/audited-board-pilot-BiUUCI
```

If the app is not running, start `RCA_STORY_ENABLED=false RCA_PORT=3015 node
scripts/local-app.mjs` in a persistent terminal. Do not run the launcher again;
it creates a new draft. Do not resume any other paused track.

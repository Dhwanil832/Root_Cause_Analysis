# RCA Fieldwork — Try 6

Try 6 builds an investigative position first, then does the work that position needs. It does not wait for every possible specialist finding and question to be exhausted before producing a board.

Try 5 and its paused experiment are unchanged. This folder has separate runtime storage, no copied investigations or uploaded evidence, and no copied credentials. Historical source files remain for comparison; the application routes exclusively through the new planner.

## Start

Use Node 24, then run `npm install` if dependencies are not already present, followed by `npm run dev`.

Open **http://127.0.0.1:3016/**. The launcher starts both the local web app and its authenticated worker. Installed Ollama models are discovered automatically. Select a model and submit an incident plus its starter documents. Default reference documents, starter documents, and later answer attachments remain separately attributed. Each model has its own evidence, versions and result cache.

Use `.env.example` for optional settings. Set a private `PROVIDER_VAULT_KEY` before saving hosted-model API keys. The storyteller is not automatically enabled; `RCA_STORY_ENABLED` defaults off. No model fallback or ensemble has been added.

## Capacity policy

Try 6 no longer imposes a shared 32,768-token context window, fractional input/output quotas, a generation-token cap, a hosted-inference deadline, or the old upload/visual-file size caps. Ollama context comes from the selected model's `/api/show` metadata. Installed `qwen3.5:latest` reports **262,144 tokens**; models reporting 32,768 keep that native capacity. Model cards display the reported capacity, and new tracks freeze it for reproducibility. Hosted models with unknown capacity use provider admission instead of a guessed application window.

There is no fixed total-question, claim, version, or whole-investigation duration quota. This does not turn the investigation-first planner into an endless loop: it still publishes a position and asks for concrete new evidence. Validation failures, unavailable prerequisites, provider errors and manual pauses are still meaningful states, not quotas to ignore.

Model context/output boundaries, available RAM/VRAM, provider rate limits and infrastructure request/storage limits cannot be removed by this app. Larger native windows can allocate substantially more memory. Context planning remains a conservative byte estimate including template, exact schema and media overhead; required evidence is never silently trimmed. Optional retrieved passages that cannot fit are recorded as omitted. Lossless storage chunks and serial model execution remain batching/ownership mechanisms, not limits on total evidence or work. Large extracted documents now use lossless artifact storage instead of a single oversized database row.

The storyteller uses the same uncapped generation policy without its old 3,200-token reserve or 80/20 context split. It remains disabled by default. Manual cancellation, renewable worker leases, provenance checks and no-truncation protections remain enabled. See [the capacity change record](docs/try6-capacity-policy.md) for exact changes and verification.

Qwen 3.5 uses explicit mode-specific sampling in `src/engine/review/inference-profile.ts`:
the documented general instruct profile for non-thinking stages, and the existing
thinking profile for literal claim review. This replaces the temperature-zero
default after a recorded exact-output loop. Mode and sampling are preserved in
each call's trace/cache identity; this does not cap generation or switch models.

Local data lives under this folder's `.wrangler/`. Do not delete it to reset an experiment. `npm start` also uses the local Cloudflare bindings; this is not a production deployment configuration.

## What generates V1

1. Read original passages into a source notebook. Preserve provenance, scope and uncertainty. Reuse unchanged passages in later versions.
2. Consider the notebook collectively. Establish the reported event, normal/incident conditions, relevant tags, initial map premises, possible explanations, and distinguishing evidence directions. A separate connection task then proposes arrows against the selected node catalog; it cannot invent endpoints.
3. Consult specialists on named branch ambiguities. A tag alone does not spawn work, and the notebook is not divided into specialist batches of five findings.
4. The common answer agent searches originals for those directions and merges equivalent questions, retaining all specialist owners. It reuses finding IDs; it cannot create another layer of extracted claims.
5. Consolidate the position and identify the next concrete evidence requests. Reconsider requested missing nodes, then separately update connections. Unknown equipment behavior stays unknown; a requested drawing or inspection is a legitimate result.
6. Review only the map's selected premises and verify proposed connections. One failed claim check does not block independent claims or connections.
7. Publish the version, including uncertainty and requests for what should happen next. A completed execution is **not** a completed RCA.

The provisional map is visible after step 2. There is no fixed question-count quota. New evidence creates V2, reuses the source notebook and useful prior work, and can revise or disfavor explanations. New source material conservatively rechecks selected map premises; it does not recheck the entire notebook. Retiring a node or withdrawing an arrow requires an explicit reason. Original observations and earlier versions remain preserved.

Invalid individual connections stay quarantined, without failing a usable frame.
Unusable foundations still pause. Publication with unresolved checks or rejected
proposals is labeled partial, not treated as a scientific acceptance pass.

## Navigate the code

| Responsibility | File or folder |
|---|---|
| Main application entry | `src/orchestrator/main-router.ts` |
| New workflow and work selection | `src/engine/investigation/planner.ts` |
| Stage output contracts | `src/engine/investigation/contracts.ts` |
| Compact notebook and task context | `src/engine/investigation/context.ts` |
| Apply maps, consultations, shared answers and withdrawals | `src/engine/investigation/apply.ts` |
| Branches, missions, directions and source-read state | `src/engine/investigation/types.ts` |
| Durable execution, traces, leases, provider calls | `src/engine/tasks/` |
| Original source registration and retrieval | `src/knowledge/` |
| Literal claim checking / formatting guardrail | `src/engine/review/` |
| Board projection and independent arrow checks | `src/engine/board/` |
| Model-local immutable revisions | `src/server/engine-repository.ts` |
| First map prompt | `prompts/investigation-map/task.md` |
| Connection proposal prompt / node request path | `prompts/connections/task.md` |
| Explicit saved partial-frame recovery | `src/server/frame-recovery.ts` |
| Specialist consultation prompt | `prompts/targeted-consultation/task.md` |
| Common answers and brokerage prompt | `prompts/evidence-resolution/task.md` |
| Consolidation prompt | `prompts/map-refinement/task.md` |
| Specialist domain missions and kickoff examples | `prompts/specialists/<tag>/system.md` |
| New dashboard position view | `app/incident/investigation-position.tsx` |
| Workflow and shared-component tests | `scripts/investigation.test.mjs`, `scripts/engine.test.mjs` |

`tasks/legacy-planner.ts` supplies the inherited ledger initialization helper, but its old scheduling function is never dispatched. Legacy experiment/migration launchers are not a way to run Try 6. Use a fresh dashboard investigation.

## Verification and limitations

Run `npm run test:engine`, `npm run test:regression`, `npm run test:capacity`, `npm run typecheck`, `npm run lint`, and `npm run build`.

The workflow tests use real in-memory SQLite and deterministic provider fixtures. They check V1→V2, provenance, branch retention, partial failures, deduplication, retirement, isolation and publication. They do not measure Qwen's causal reasoning. `test:regression` runs the applicable shared-component tests; old Try 5 scheduling/migration assertions are deliberately not the Try 6 acceptance criteria.

The real-model IA-16036 V1 experiment is recorded in `evals/ia16036-clean-v1-launch.md` and its saved-frame recovery in `evals/ia16036-v1-frame-recovery.md`. Inspect V1's groundedness and useful evidence directions before providing a controlled evidence update for V2. Publication alone does not demonstrate reasoning quality. `node scripts/inspect-run.mjs RUN_ID` reads local progress without native database writes.

Retrieval remains lexical. Context planning is conservative byte-based estimation, not exact tokenization. A notebook too large for the selected model fails explicitly instead of silently discarding evidence; automatic hierarchical notebook compression is not implemented. Question prioritization and hypothesis selection still require real-model evaluation. Same-model review is a separate checking task, not independent factual corroboration. This remains a local research prototype, not a production-authenticated or safety-certified system.

See `docs/try6-implementation.md` for the detailed implementation and verification record.

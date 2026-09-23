# RCA Fieldwork — Try 5

Try 5 replaces the whole-investigation loop with persistent, individually committed tasks. Try 4 and its runtime data are unchanged.

## Start locally

Use Node 24 (the regression tests use Node's SQLite and module-hook APIs).

    npm install
    npm run dev

Open http://127.0.0.1:3015/. The launcher applies local-only migrations, starts the web app and a separate worker, and supplies their shared authentication token. Closing the browser does not cancel queued work. Restarting the launcher recovers saved work after any outstanding lease expires.

Both npm run dev and npm start use the local Cloudflare runtime for D1/R2 bindings. This is not a production deployment setup. npm run build checks the bundle; bare vinext start does not supply this app's storage bindings.

Runtime data and uploads live under this folder's ignored .wrangler/ directory, not Try 4. Do not delete that directory if you want to preserve investigations.

Use .env.example for configuration. Set a private PROVIDER_VAULT_KEY (32+ characters) before saving hosted API keys. Ollama defaults to http://127.0.0.1:11434. Installed models are discovered without pulling another copy. The deterministic preview is not offered as a scientific RCA model.

## Implemented

- Immutable inputs and final snapshots per model track. New evidence queues a version even while the preceding version runs.
- Exact source offsets, content hashes, decimal-safe splitting, table-header context, and cached extraction.
- Durable leases, atomic commits, restart recovery, outage pause/resume, local failure quarantine, and track-scoped result reuse. No legacy-engine fallback.
- Bounded task inputs and local reference IDs, with explicit context estimates and omitted-evidence coverage.
- Baseline understanding, tagging, specialists, question brokerage, common answers, claim review, incremental causal proposals, separate verification, and gated corrective actions.
- Persistent finding/node identities, evidence-driven rechecks, competing mechanisms, and board-change records.
- Separate machine evidence status and human decisions. Partial answers stay partial; missing records are not proof of missing physical controls.
- Dashboard task progress, decision summaries, quarantine reasons, model/configuration metadata, source reading coverage, and version-specific exports.
- Original image/PDF reading when supported by the selected provider. Unsupported originals remain explicit local failures, with no model fallback.
- Independent storyteller jobs: select questions, save each answer, inspect the batch, then release it into a separate RCA revision. Hidden scenario truth and evaluator expectations never enter RCA prompts.

No fixed total question or branch quota is imposed. Each revision has one primary pass and one follow-up answer/review pass for later-generated questions. Further questions stay open for subsequent evidence; completion of an execution pass does not mean the investigation is complete.

## Code map

| Area | Entry point |
|---|---|
| Main routing | src/orchestrator/main-router.ts |
| Immutable revision API | src/server/engine-repository.ts |
| Durable tasks and inference | src/engine/tasks/ |
| Data and output contracts | src/engine/types.ts, src/engine/contracts.ts |
| Context planning | src/engine/context/planner.ts |
| Source registry and retrieval | src/knowledge/sources/, src/knowledge/retrieval/ |
| Record identities/ownership | src/engine/records.ts |
| Reading/tagging/specialist/review handling | src/stages/evidence-reading/task.ts |
| Broker/answer handling | src/stages/question-broker/task.ts |
| Causal changes and projection | src/engine/board/ |
| Independent simulation | src/story-agent/ |
| Prompt assembly | src/engine/prompts.ts |
| Role instructions | prompts/engine/shared.md, prompts/<role>/task.md |
| Specialist kickoff tables | prompts/specialists/<tag>/system.md |
| Local processes | scripts/local-app.mjs, scripts/task-worker.mjs |
| SQL schema/migrations | db/schema.ts, drizzle/ |
| Regression tests | scripts/engine.test.mjs |

Specialist assembly uses the agreed kickoff tables, not old output-contract instructions. Models provide proposals and concise decision summaries, not private chain-of-thought. Historical synchronous modules remain for reference but are not used by the application. Old experiment launchers targeting Try 4 are disabled in this copy.

## Validation

    npm run typecheck
    npm run test:engine
    npm run lint
    npm run build
    npm run db:generate

Tests use real SQLite transactions and a deterministic adapter. They verify execution/integrity/recovery, not Qwen's RCA quality. No new real-model RCA evaluation has been run as part of this implementation.

Retrieval remains lexical with source neighborhoods. Context accounting is an estimate, not an exact tokenizer. Essential evidence that cannot fit fails locally instead of being discarded. Same-model review is not independent corroboration. This is a local research prototype, not a production-authenticated or safety-certified system.

See docs/try5-implementation.md for the detailed verification record and evals/try5/README.md for the controlled evaluation gate.

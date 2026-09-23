# RCA Fieldwork — Try 2

A local-first investigation workbench for comparing how multiple models explore the same incident without sharing evidence between model runs.

## Run locally

1. Use Node 22.13 or newer.
2. Install dependencies with npm install.
3. Start the app with npm run dev.
4. Open the local URL printed by the development server.

The built-in Field Analyst works without a model server. If Ollama is running, installed models are discovered from http://127.0.0.1:11434 (or OLLAMA_BASE_URL). The model registry can request an Ollama pull by tag.

## Product invariant

The only object initially shared by selected models is an immutable copy of the original incident description. Every model receives its own track, evidence collection, uploaded documents, tags, questions, trace, and V1/V2/V3 sequence. An answer creates a new immutable version only in the track where it was entered.

## Code map

- app/page.tsx: incident entry and multi-model selection
- app/history/page.tsx: preserved incident list
- app/incident/investigation-dashboard.tsx: Incident → Model → Version dashboard
- app/settings/models/page.tsx: local/provider-neutral model registry
- app/api: validated public request boundaries
- src/orchestrator/main-router.ts: deterministic stage and adapter boundary
- src/orchestrator/deterministic-engine.ts: immediately testable preview engine
- src/server/repository.ts: D1 persistence and immutable version writes
- src/domain: stable tags, question intents, and data contracts
- prompts: inspectable, stage-separated prompt package
- db/schema.ts: durable entities
- evals: regression fixtures

## Storage

D1 stores incidents, isolated model tracks, immutable snapshots, and evidence metadata. R2 stores uploaded evidence files. API credentials are never placed in D1, R2, prompts, model outputs, or traces.

## Current adapter status

Try 2 ships with an inspectable deterministic analysis adapter so the complete interaction can be tested without external services. Ollama discovery and pull are functional. The provider boundary is intentionally isolated in main-router.ts; validated Ollama and closed-provider generation adapters can replace the preview adapter without changing the UI or persisted state model.

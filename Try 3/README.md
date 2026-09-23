# RCA Fieldwork — Try 3

Try 3 is a local-first, evidence-led root-cause investigation workbench. It turns an initial account into independent model tracks, evolving specialist knowledge bases, brokered questions, an evidence ledger, a testable causal board, verification findings, and cause-linked corrective actions.

## Run locally

1. Use Node 22.13 or newer.
2. Run `npm install`.
3. Apply `drizzle/0000_unusual_hercules.sql` to the local D1 database when the Sites control plane has not done so.
4. Run `npm run dev` and open the local URL.

The built-in Field Analyst works without a model server. Installed Ollama models are discovered from `http://127.0.0.1:11434` (or `OLLAMA_BASE_URL`) and can be selected without pulling them again. The model registry can pull additional Ollama tags.

Hosted OpenAI Responses or OpenAI-compatible Chat Completions providers can be added from the model registry. API keys are encrypted with AES-GCM using `PROVIDER_VAULT_KEY`; only a four-character hint is returned to the browser. The key is decrypted only while a provider request is being made and never enters an investigation snapshot or trace.

## Investigation loop

Incident account → document and image intelligence → incident understanding → structured entities and timeline → fixed taxonomy → dynamically selected specialists → question broker → dynamic answer fetchers → evidence and contradiction processing → causal analysis → causal verification → corrective actions.

New evidence repeats this loop only inside the model track where it was entered. V1 is never overwritten when V2 is created.

The causal board is a draggable, zoomable canvas. Accepting or rejecting a causal finding, closing a branch, or approving a corrective action creates another immutable human-review version. A report view exports Markdown, a complete JSON evidence package, and a print layout suitable for PDF.

## Evidence scopes

- `reference`: default plant layouts, handbooks, approved standards, and other standing context.
- `starter`: records uploaded with one incident account.
- `question`: records uploaded in response to one investigation question and attached only to that model track.

D1 stores metadata and immutable snapshots. R2 stores original files. Digital text is extracted directly. Images and scanned documents are routed to a compatible multimodal model, and its atomic observations remain proposed evidence until an investigator confirms or rejects them. OCR is a fallback and indexing aid rather than the source of causal conclusions.

## Code map

- `app/page.tsx`: incident intake, starter records, and multi-model selection.
- `app/references/page.tsx`: default reference library.
- `app/settings/models/page.tsx`: Ollama discovery plus encrypted hosted-provider management.
- `app/incident/investigation-dashboard.tsx`: Incident → Model → Version dashboard.
- `app/incident/causal-canvas.tsx`: interactive causal map and human review controls.
- `app/incident/[id]/report`: final report and evidence exports.
- `app/api`: validated request boundaries.
- `src/orchestrator/investigation-loop.ts`: main routing and stage order.
- `src/stages/*/run.ts`: one implementation section per reasoning responsibility.
- `src/providers`: validated Ollama and future API-compatible model adapters.
- `src/knowledge`: document extraction and evidence retrieval.
- `src/stages/document-intelligence`: model-specific image and scanned-document examination.
- `src/server/document-media.ts`: bounded retrieval of preserved originals for multimodal processing.
- `src/server/repository.ts`: D1/R2 persistence and track isolation.
- `src/server/provider-vault.ts`: encrypted hosted-provider configuration.
- `src/domain`: stable contracts, schemas, IDs, and tag catalog.
- `prompts/<stage>/system.md`: inspectable prompts separated by responsibility.
- `prompts/specialists/<tag>/system.md`: specialist goals and kickoff exemplars.
- `drizzle`: generated migration; schema is owned by migrations, not request handlers.
- `evals`: regression fixtures.

## Safety and auditability

Tags are routing decisions, not causal conclusions. The harness validates model output against stage-specific JSON schemas, retries one repair, records concise decision summaries rather than private chain-of-thought, and preserves fallback output when a stage fails. Claims retain source IDs and epistemic status; chronological order alone does not establish causation.

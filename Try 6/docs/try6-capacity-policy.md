# Try 6 capacity changes — 2026-09-20

The user requested removal of application-imposed limits. Changes apply to the active Try 6 engine and its shared provider, upload and storytelling paths; the historical Try 5 code/run remains unchanged.

| Previous behavior | Current behavior |
|---|---|
| Shared 32,768-token default | Ollama's native text-model context is read from `/api/show`; no app-wide context override. Hosted capacity is provider-managed if unknown. |
| Reserve half or a quarter of the context before selecting evidence | No fractional quota. Physical-window planning still counts exact output schema, source lines, prompt overhead and media. |
| Hosted `max_output_tokens` / `max_completion_tokens` from an application estimate | These fields are omitted for uncapped engine/story calls. Provider defaults and native ceilings still apply. Ollama continues using `num_predict: -1`. |
| Hosted inference aborted at three minutes | No application deadline. Operator/lease cancellation still aborts the request without a repair retry. |
| Story answer restricted to 3,200 output tokens for hosted models | No application output cap. |
| Story context split into 80% documents / 20% memory | Relevant released memory followed by ranked available source passages, subject only to the native-context estimate. |
| Uploads over 16 MB rejected | No application file-size cap. Platform, memory and provider request limits remain. |
| Visual originals over 12 MB or a 24 MB batch silently skipped | No size-based omission. Unsupported modalities and missing originals still fail explicitly. |
| Large extraction/cache text stored as a single database string | Reused lossless content-addressed artifact chunks; originals remain in the file bucket. Legacy plain-text document rows remain readable. |
| Model pull aborted at 20 minutes | No application pull deadline; caller cancellation is respected. |

## What stays

- Evidence integrity and schema checks, including no invented citations, no acceptance of incomplete responses, and no unsupported causal claims.
- Native context-aware retrieval. UTF-8 bytes/2 is an estimate, not a tokenizer; 2,048 tokens of template headroom and estimated media cost are still counted. Exact source-dependent schemas are counted during passage selection rather than added after a packet is full. Generation headroom is diagnostic, not sent as a token ceiling.
- Explicit context failures for required evidence or notebook metadata that cannot fit. Original content remains stored. There is no hidden lossy compression or promise of infinite context.
- One model task at a time, renewable leases, atomic commits and immutable versions. A lease is renewed while inference runs; its duration is not a task deadline.
- One inference attempt per normal engine task, with explicit recovery after a failed contract/service call. Unlimited blind retries are not enabled.
- Short discovery/provider-health-check timeouts, which do not interrupt an active investigation model call. The old `OLLAMA_STREAM_IDLE_MS` application idle cutoff is removed.
- The investigation-first phase order and publication boundary. No fixed question, claim or version count was introduced.

Historical `src/stages/` implementations and old schema files retain their legacy settings for comparison; the active Try 6 scheduler does not dispatch them. The legacy `context-budget.ts` guard is bypassed by all active engine/story calls (`noTruncation: true`).

## Verification

- 16 capacity tests pass: metadata parsing/caching, larger native windows, unknown hosted capacity, exact-schema accounting, uncapped Ollama and hosted payloads, cancellation, incomplete-output rejection, large extracted-text round trips, full 17 MB + 9 MB visual attachments, story behavior and frozen track configuration.
- 15 Try 6 workflow tests and 37 applicable inherited regressions pass (68 total).
- TypeScript and production build pass. Lint has no errors; one pre-existing unused-variable warning remains in the copied historical preparation script.
- Running `/api/models` returns the detected windows: Qwen 3.5 at 262,144; seven installed models at 131,072; Mistral 7B and Qwen 2.5 7B at 32,768.
- This is request-shape/storage/routing verification, **not** a maximum-context inference benchmark or a new RCA experiment. Higher-context memory viability and model reasoning quality still need a real run. No hosted API calls were made.

## Guidance used

The OpenAI Docs skill informed hosted-provider behavior: omit the optional generation ceiling and explicitly disable Responses input truncation, while retaining cancellation and incomplete-result rejection. See the official [Responses reference](https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create).

Ollama's [context guidance](https://docs.ollama.com/context-length) explains that larger windows require more memory. Its [Modelfile reference](https://docs.ollama.com/modelfile) documents `num_ctx` and `num_predict`. A reported native window is not a guarantee that it fits this machine's available RAM/VRAM.

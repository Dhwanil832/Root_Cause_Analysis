# Run observations — qwen-b0-ClBDGA

## Setup and dispatch

- Frozen application: `try4.3.0-resumable-evidence-review`; 134 source/configuration files recorded by hash in manifest.json.
- Seven sealed B0 inputs only. Six documents ingested, one incident description. No later batches, evaluator material, storyteller or external answering job supplied.
- First connection attempt failed before creating an incident or calling a model: vinext ignored `--host` and bound IPv6 localhost. Artifacts preserved in `setup-attempt-1/`. Restarted this isolated app using its documented `--hostname 127.0.0.1` option.
- Actual RCA dispatch: 2026-09-16T18:16:47Z, incident `b7c62bf9-604c-4312-9520-7b63b20b7363`, track `eebd569e-92a1-4b41-87c3-3f4953cfb2a6`.
- The local Cloudflare worker did not inherit the shell's OLLAMA_BASE_URL. Its `/api/models` reported `http://127.0.0.1:11434`, not the intended proxy at 11435. The installed model digest was checked before dispatch. Provider defaults specify the same 32768 context, temperature 0 and think:false as the intended run.
- Consequently, the transparent proxy has **no request/response capture for this run**. Do not describe it as a complete wire-level trace. The application's per-call checkpoints preserve validated output, raw attempts, timing and token usage; the frozen source and input package are available separately. No source or prompt was changed after dispatch.
- The analysis was allowed to continue against the same local Qwen instead of discarding successful work solely to add proxy capture. No automatic whole-cycle retries are enabled.

## Review criteria frozen before results

Judge only B0-testable targets T01–T03 plus factual restraint: receiving RHOB pressure must not become upstream pressure; the change-record requirement's alternative paths must retain their OR meaning; assignments, requested records, blank fields and pending releases must not become observed actions or physical absence. Root cause should remain unresolved at this release. Model-execution success is separate from RCA correctness.

The evaluator-frozen directory is operator-only and has not been supplied to the model.

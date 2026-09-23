# Fresh Try 6 V1 launch — 2026-09-20

## Receipt

- Queued: `2026-09-20T15:29:19.481Z`
- First worker claim: `2026-09-20T15:29:20.579Z`
- Incident: `9660f4f2-5fc0-4d0a-917e-8e48641956e3`
- Track: `a6647fe7-b418-4232-817f-b3c6d3a5325d`
- Run: `a20904da-8710-40df-8d58-fec78f451f2a`
- First call: `aa4eab72-6ff5-40c1-81c8-9d8571d46a0d`
- Dashboard: http://127.0.0.1:3016/incident/9660f4f2-5fc0-4d0a-917e-8e48641956e3
- Engine: `try6.0.0`, investigation-first planner with native-context/uncapped-output policy.
- Model: `ollama:qwen3.5:latest`
- Frozen model digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Context: `262144`, confirmed in the run input and Ollama `/api/ps`.

## Inputs and boundaries

This is a fresh cumulative B0+B1 V1, using the same case-content-only evidence
as the stopped Try 5 experiment. The package remains a historically anchored
synthetic evaluation, not authentic plant records. This operator record is not
model input.

Source: `../IA-16036 Controlled Evidence Package/07_case_content_inputs/`.
Uploaded the incident and ten individual documents only: IA-D01–D03 as
incident-local references, IA-S01–S03 as starter documents, IA-P01–P03 and
IA-C01 as additional question-scope evidence introduced at V1. No question IDs
or user answers were invented. Every uploaded file hash matched the prepared
manifest; extracted text matched after outer-whitespace normalization.

B2/B3, answer bank, ground truth, rubric, manifest/provenance files and earlier
model outputs are withheld. No old findings, board, cache or versions were
imported. The storyteller was not configured; the story-job table was empty at
launch. The shared reference library remains empty and unchanged. Try 5 was
not resumed or modified.

## Launch method

`scripts/launch-clean-v1.mjs` submits through the application's HTTP API only.
The incident upload route now exposes existing incident-local reference handling
and allows previously collected additional documents to be attached before
initialization. This preserves the original three document scopes without
creating a version per upload or writing directly to the live SQLite database.

The draft was checked for one model, zero versions, ten documents and matching
scopes/hashes before its single initialization call. The reading approval stop
is disabled. Integrity failures and manual pause remain effective.

## Initial observation

The run was observed in `running` state, reading the original incident account,
with ten subsequent document-read tasks queued, no recorded errors and no
reused tasks. Ollama reported the model loaded with its full native context.
This confirms dispatch/loading, not completed V1 or accepted causal reasoning.

After V1 publishes, inspect source fidelity, calibrated uncertainty, justified
connections, alternative mechanisms and concrete next evidence requests before
releasing a controlled V2 update. Do not declare a complete RCA from initial
publication alone.

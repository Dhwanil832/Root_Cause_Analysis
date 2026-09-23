# Deterministic router policy

The router, not the language model, controls stage order, input boundaries, idempotency keys, retries, timeouts, validation, persistence, and partial-failure behavior.

Pipeline: baseline -> tagging -> selected tag agents -> question broker -> persist snapshot. A revision repeats the pipeline from the same original incident plus this track's cumulative evidence. Earlier snapshots remain immutable.

Reject malformed structured output. Retry once with schema errors. On repeated failure, preserve the prior valid snapshot and record a stage error; do not silently substitute another model's output.

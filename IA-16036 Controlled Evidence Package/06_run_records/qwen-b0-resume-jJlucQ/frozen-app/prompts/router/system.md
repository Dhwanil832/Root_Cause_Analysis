# Deterministic router policy

The router, not a model prompt, controls stage order, input boundaries, stable IDs, idempotency, retries, timeouts, schema validation, persistence, and partial-failure behavior.

Pipeline: incident understanding -> incident structuring -> tagging -> selected specialists -> question broker -> answer fetching -> evidence processing -> causal analysis -> causal verification -> corrective actions -> persist snapshot.

A revision repeats one complete cycle from the original incident plus that track's cumulative evidence. Earlier snapshots remain immutable. The router creates no automatic recursive loop: one incident submission or evidence change produces one cycle and then waits for new evidence or human action.

Reject malformed structured output. Retry once with concise schema errors. On repeated failure, preserve usable stage results, record the failure, and never substitute another model's output.

# Architecture and harness contract

## State topology

Incident → Model track → Immutable version → Stage outputs

An incident owns the original description. Each selected model gets a new track. A track owns all later evidence and versions. There is no incident-wide evidence pool and no incident-wide version counter.

## Pipeline

1. Baseline context identifies site vocabulary, relationships, normal state, and chronology gaps.
2. Fixed-taxonomy tagging selects evidence-supported investigation entry points.
3. Selected specialists independently propose questions inside their tag boundary.
4. The broker keeps distinct material questions and records every overlap it suppresses.
5. A validated snapshot is written atomically as the track's next version.

Step 0 does not block later stages. The number of questions is evidence-driven and has no fixed maximum.

## Inspectability without chain-of-thought

The normal view shows questions. The decision trace shows stage conclusion, evidence used, unresolved facts, confidence, prompt version, engine, and duration. It deliberately does not request, persist, or reveal private chain-of-thought.

## Harness responsibilities

The deterministic router—not a model prompt—owns:

- track isolation and authorization boundaries;
- stage order and explicit state transitions;
- stable question IDs and intent IDs;
- prompt/version metadata;
- schema validation and repair/retry policy;
- idempotency and immutable persistence;
- timeout, partial-failure, and fallback behavior;
- evidence provenance and conflict preservation;
- prompt-injection resistance at evidence boundaries;
- secret and personal-data minimization.

## Provider contract

Every adapter receives only the original incident, the active track's cumulative evidence, model metadata, stage contract, and prompt manifest. It returns structured stage output. Invalid output never becomes a snapshot. Provider credentials remain server-side environment bindings and are excluded from history and traces.

## Revision semantics

An answer or upload is appended to one track. The pipeline re-runs with that track's evidence and creates V(n+1). Prior versions remain readable. Comparisons must name both model and version because two model tracks can be based on different evidence.

## Evaluation

Fixtures assert tag recall, false-positive guards, stable intents, baseline terminology questions, broker coverage records, isolation between tracks, and version immutability. Historical cases should be sampled across personal injury, near miss, and equipment damage rather than optimized against one event type.

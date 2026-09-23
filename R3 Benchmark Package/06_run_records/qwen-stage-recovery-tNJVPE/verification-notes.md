# Try 4 stage-recovery verification

Recorded September 14, 2026 (America/Chicago; the live check ran September 15 in UTC).

## Outcome

The targeted Qwen broker → causal-analysis → causal-verification check completed. All 33 regression tests, TypeScript checking, lint on changed files, and the production build passed after the final mapping fix.

This is an execution-reliability check, **not** a completed four-version storyteller investigation, a validated root cause, or a new model-quality score. No app incident or committed version was created. The earlier failed experiment and historical snapshots were not edited, and its monitoring automation remains paused.

## Implemented in Try 4

- Validate the focal-event pointer, unique node keys, and edge endpoints before constructing a board. Invalid references go back to the selected model with the exact error; the harness does not guess a focal node.
- Process broker candidates in small requests with an exact list of legal IDs and complete keep/covered decisions. Four candidates per request is a transport bound, not a total question limit. Preserve the original questions, specialist routing, accepted batches, and raw attempts.
- Remove the broker's model-driven screening disposition. Missing evidence must not itself discard an investigation question. Final deterministic deduplication requires matching wording and investigation intent, not merely a shared intent label.
- Retry only the failed stage or broker batch, with at most two provider attempts. Strict execution stops on exhausted recovery; the repository and unattended driver no longer automatically replay the entire RCA cycle.
- Resolve verification against the actual board IDs supplied to the verifier, with valid legacy local-key aliases accepted. Unknown targets fail validation. A blocking finding takes precedence over a conflicting verification flag.

## Live check evidence

Model: `ollama:qwen3.5:latest`; no substitution. The installed model metadata is preserved in `installed-model.json`.

Input: the first saved uncommitted packet from `qwen-story-autonomous-N9Y0lS`, including 26 baseline/specialist questions. Input snapshot SHA-256: `51b388c55328044df47e8cba96dd5c3f4a2088aaf5b4653d14acf124e7e5dbf3`. The script verified that the source snapshot was unchanged.

| Stage | Observed result |
| --- | --- |
| Broker | 7 batches, each valid on its first attempt; 11 questions retained and 15 marked covered; approximately 4m 10s. |
| Causal analysis | 11 nodes, 7 edges, valid focal node `node-1a4cas8`; approximately 8m 10s across two attempts. |
| Verification | Structurally valid output; approximately 1m 3s. The model described the board as developing, with important evidence still missing. |

The first causal attempt failed with `fetch failed`; the second succeeded. Although the generic trace calls this “repaired,” this live retry demonstrates transport recovery, **not** correction of a model-produced reference defect. Semantic-reference correction is covered separately by regression tests using the exact earlier failed drafts and controlled responses. The raw successful causal titles needed no category-prefix cleanup.

An earlier diagnostic, `qwen-stage-recovery-Qp0dQr`, failed when Qwen put multiple coverage-owner IDs into one string. Its raw failure remains preserved. Request-specific ID enums were added before this successful check.

## Post-live verification mapping correction

Inspection of `verification.json` exposed a mapping bug: Qwen returned seven actual board node IDs, but the mapper looked for earlier model-local keys, losing all seven node-verification decisions. The output also both verified edge index 6 and gave it a blocking finding.

The mapper was corrected after these live calls. A regression test replays this exact saved output through the production verification stage: seven node decisions are now retained, and only one edge remains verified because the explicit blocking finding overrides the conflicting flag on edge index 6. This was a deterministic replay, not another live model call. Original `verification.json` and `result.json` remain unchanged to preserve what actually happened during the live check.

## Model-quality concerns still open

- Some coverage decisions remain too broad. The saved broker output includes a partial-coverage rationale and merges a question about procedural requirements with one about whether verification occurred. Valid IDs and complete accounting do not prove semantic equivalence.
- The causal output refers to “backup roll balances removed,” whereas the incident description distinguishes removed rolls from a balance left raised. It also treats loss of hydraulic support too confidently while the hydraulic system's load-bearing role remains unestablished.
- Verification identifies unsupported causal edges and requests drawings, work logs, procedure text, and handoff evidence. However, it does not catch every problematic node claim. A structurally valid or model-verified board is not confirmed ground truth.

The full autonomous four-version storyteller experiment has not been restarted. Its next authorized run is still needed to test repeated evidence releases and board evolution end to end.

## Reproducible checks

From `Try 4`, using the project's Node 24 runtime:

```sh
node --experimental-strip-types --import ./scripts/register-test-loader.mjs --test --test-concurrency=1 scripts/stage-recovery.test.mjs scripts/reinforcement.test.mjs scripts/story-agent.test.mjs scripts/autonomous-runner.test.mjs
node node_modules/typescript/bin/tsc --noEmit --incremental false
```

The regression suite uses mock providers/loopback servers; it does not run real model inference. The live script is separately opt-in: `scripts/verify-qwen-stage-recovery.mjs --live`, with the same loader. See `Try 4/docs/story-agent.md` for the code map and recovery boundaries.

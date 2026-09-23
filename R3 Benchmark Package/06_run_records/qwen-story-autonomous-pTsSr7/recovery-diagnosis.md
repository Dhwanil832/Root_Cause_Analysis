# Recurrent focal-reference failure — automatic restarts paused

Checked on 2026-09-15 at approximately 17:42 UTC against the saved artifacts, live local incident API, and process list.

## Outcome

- Run: `qwen-story-autonomous-pTsSr7`, frozen version `try4.2.2-verification-contract`.
- Model: `ollama:qwen3.5:latest` in both isolated roles; no fallback model used.
- Incident: `f6388578-8905-44cb-a66e-75c06a2a21d5`.
- Track: `6e6a6dcd-e460-452f-a738-a7b640cefcce`.
- Started: 2026-09-15T15:33:42.742Z.
- Runner stopped with failure: 2026-09-15T15:57:19.972Z (about 23 minutes 37 seconds).
- Committed versions: **0 of 4**. No storyteller batch was generated or applied in this run.
- Fifteen completed checkpoints precede the failed causal-analysis checkpoint. These include incident understanding/structuring, tagging, specialist questions, question brokering, answer fetching and evidence processing.
- Causal verification was not reached. This run therefore cannot establish whether the latest verifier fix succeeds end to end.

## Exact failure and preserved attempts

Failed checkpoint: `a09be083-5f5d-4a9e-b6b9-86536bcc5de8`, sequence 16, target V1, run ID `a752a949-b0a9-45ac-917e-164e9bad21a7`, recorded 2026-09-15T15:57:19.687Z.

Both saved provider attempts are parseable JSON. Both set `focalKey` to `event-1794j8z`, but neither includes that key in its own nodes array. Both instead contain an event node keyed `event-fall`, titled “R3 Exit Carrier Beam falls from yoke into mill pit”.

| Attempt | Nodes | Edges | Focal reference | Result |
| --- | ---: | ---: | --- | --- |
| 1 | 18 | 11 | `event-1794j8z` does not resolve | Output contract rejected |
| 2 | 18 | 1 | Same unresolved reference | Output contract rejected |

The recorded error begins: `Output contract: focalKey "event-1794j8z" does not match any nodes[].key.` It lists the available keys and directs the model not to copy a timeline/entity ID. The corrective attempt changed substantive graph content, including dropping ten edges, but retained the reference defect. The saved output does not establish why the model ignored the correction.

Raw attempts and complete errors remain in `latest-incident.json`, at the failed checkpoint's `payload.providerAttempts`. Original snapshot SHA-256:

`ef248d03856f7fd0e6e2558c01aafddb442d14ec6cfa42ed02cd86dd64f5f1a9`

The live API independently confirmed zero versions, sixteen checkpoints and this same final failed checkpoint. Process inspection found the local application and Ollama server running, but no autonomous experiment runner or matching active experiment curl request. No processes were terminated and no mutation was retried.

## Why this is a recurrence

Earlier preserved run `qwen-story-autonomous-N9Y0lS` produced four uncommitted causal drafts with `focalKey: event-zfmjgq` and an empty mapped `focalNodeId`; its final failure included `Missing focal node`. The stage-recovery work added explicit graph-identity instructions, runtime validation and a bounded same-model corrective attempt. The focused check documented in `../qwen-stage-recovery-tNJVPE/verification-notes.md` passed a causal graph with a valid focal node.

The current run still fails the same reference relationship despite those measures. The current causal schema permits independent string values for node keys and `focalKey`; the runtime contract correctly rejects a mismatch, but the schema and prompt do not prevent its generation. This is a model-output/harness-contract reliability failure, not proof of a particular RCA finding or of insufficient incident evidence.

The subsequent broker fix completed successfully in this run. The verifier fix cannot be assessed here because execution stopped before verification. No claim of four-version completion, storyteller performance, or a full RCA score is warranted.

## Disposition and proposed next step

Preserve this failed run and all predecessors unchanged. Pause `monitor-qwen-rca-test` under its repeated-failure stop rule. Do not launch another replacement during this check, weaken the validation gate, silently choose a focal node, or supply invented evidence to force completion.

A proposed next iteration, subject to the user's direction, is to make graph identity valid by construction—for example, represent the focal event explicitly in the output structure and have the application assign its reference deterministically, then constrain references in later graph-building work. That changes the output protocol and should be separately versioned and regression-tested. The observed edge loss also warrants a test that corrective handling does not silently discard causal content. These changes have **not** been implemented in this check.

Dashboard: http://localhost:3000/incident/f6388578-8905-44cb-a66e-75c06a2a21d5

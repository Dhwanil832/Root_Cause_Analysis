# B0 local-rejection continuation — runtime evidence

Snapshot time: 2026-09-16 20:33:35 UTC. This is an explicitly resumed copy of `qwen-b0-resume-jJlucQ`, not an independent fresh evaluation.

## Scope

- Same IA-16036 B0 documents, original incident, Qwen digest, prompts, schemas, generation settings and node/link batching as the parent.
- Application release `try4.3.2-local-causal-rejections` changes semantic failure handling and review visibility only. The manifest lists exact changed files and frozen hashes.
- Previous frozen runs were not edited. SQLite snapshots were taken consistently; no later evidence, storyteller answers or evaluator oracle was added to the model input.
- One resume request was sent. No automatic whole-run retry and no preflight suite. TypeScript compilation passed before freezing.

## What actually happened

1. All 57 applicable completed calls were reused: 36 upstream, 12 claim-review, three causal-node and six causal-link calls. The parent database also contains two obsolete claim-review calls that were not reused.
2. The previously failing link operation was generated again, not copied from a failed response. It again proposed two self-links. Its raw response was saved and execution continued on the first attempt.
3. Eight new link operations completed. Causal analysis saved its board at **20:31:55 UTC**: 40 nodes, 32 retained edges, 48 rejected proposals, maturity `developing`.
4. All 80 raw edge proposals are accounted for as retained or rejected. Rejections comprise three self-links and 45 proposals rejected by the existing backward-from-focal-event policy. This is a policy outcome, not a human judgment that every rejection is semantically correct.
5. The retained board has no self-links and no causal edges missing the required counterfactual/alternative strings. Every rejected proposal has its own finding; none of those findings targets a retained node or edge. The original proposals and reasons remain available.
6. The actual browser displays the saved board as **Pending V1**, with the uncommitted/incomplete warning, rejected-proposal section and zero Accept buttons. The canvas uses horizontal scrolling; this is not a final layout review.
7. At the snapshot time, two causal-verification operations had also completed, with no new execution failures. **No V1 was committed yet.**

## Limits / next outcome

The specific batch-fatal self-link regression has been passed in a real continuation. This does not establish RCA correctness. Retained nodes/links remain proposals until evidence review, and model review itself is not human acceptance. Unsupported claims, duplication and weak causal reasoning still need substantive assessment; their existence is not a reason to discard all work.

The runner remains active and stops after the first committed V1 or an execution failure. It writes `result.json` and `version-1.json` on success, or `failure.json` and `failure-snapshot.json` on failure. There is no scheduled automatic retry or storyteller cycle.

Inspect persisted progress with `tools/inspect_local_rejections.mjs` from the parent run-record tools folder. Live dashboard: http://127.0.0.1:3005/incident/b7c62bf9-604c-4312-9520-7b63b20b7363

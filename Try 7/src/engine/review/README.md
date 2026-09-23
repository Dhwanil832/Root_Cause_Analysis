# Literal-claim review

This module reviews one complete saved assertion against original source passages. It does not reconstruct the investigation or certify a causal board.

## Active path

1. The scheduler creates a `review` task directly. The rejected free-form, evidence-blind meaning-tree stage is no longer a prerequisite.
2. `prompts/claim-review/literal.md` receives the exact target and original evidence, without producer labels, previous verdicts, or generated meanings.
3. `literal-contract.ts` binds the target literally and restricts citations to real nonblank source lines. It requires citations for definitive judgments. Partial support requires a specific missing premise.
4. `literal-decision.ts` preserves the complete target as one display unit. No noun/time fragments, generated acronym definitions, or speculative ambiguity vetoes determine its status.
5. Source conflict is independent of claim truth. A report's content may be supported while its description of reality is disputed. Same-time conflicting physical measurements cannot establish a unique true value. Both accounts and original citations remain available.
6. `stages/evidence-reading/task.ts` applies the result and removes obsolete interpretation metadata. Changed evidence, changed claims and incomplete execution invalidate stale support without deleting branch identities or rewriting prior immutable versions.
7. The durable worker still isolates independent task failures. Incomplete execution is not an epistemic unknown and cannot be promoted by the causal verifier.

Policy: `literal-claim-v5.5`. The contract uses one shared shape instead of four duplicated schema branches. Original-line grammar is enforced during generation; cross-field consistency is validated at application time. Failed, structurally authentic reviews may preserve proposed missing premises as questions; their verdict remains incomplete, never repaired. Forged citations and changed targets cannot supply recovered questions. The v5.4 generated citation-map requirement was removed after it rejected a valid finding and failed to prevent an overclaim. Generation uses the previous v5.3 prompt/shape; semantic citation coverage remains an audit obligation, not a solved guarantee. Prompt, schema, original packet, model digest, explicit thinking and sampling options participate in request/cache identity. Legacy `contract.ts`, `decision.ts`, `interpretation.ts` and interpretation prompts remain for historical compatibility and invalidation helpers; the active reviewer does not use their meaning-tree assessment.

`inference-profile.ts` declares the Qwen 3.5 review-only thinking/sampling profile. Other stages and models keep their previous settings. A missing required thinking capability is an explicit configuration error, not a silent weaker fallback. The policy invalidates earlier review approvals/caches; it does not claim full semantic qualification. The previous v5.2/v5.3 candidate had a seven-case regression pass; no new full gate is claimed. The original investigation remains paused while bounded diagnostics execute. See `evals/try5/review-gap-board-results.md` before running it unattended.

## Evaluation and boundaries

- `npm run test:engine` tests persistence, provenance, status handling and cache separation. It does not measure natural-language entailment.
- `scripts/review-saved-findings.mjs RUN_ID PRODUCER_TASK_ID` runs the production executor/provider/application logic on cloned state and a read-only app DB.
- `RUN_ID --fixtures=PATH` supplies isolated synthetic inputs. Answer keys and prior case outputs never enter requests.
- `--thinking=true` registers an explicit same-model native-thinking comparison. Historical diagnostic default mode remains false. `--runtime-defaults` instead uses the actual production stage profile with no test-only override. Request traces and manifests identify the mode; no fallback occurs.
- `--sampling=qwen-reasoning` explicitly selects the recorded model-card Quickstart profile with seed 42. `--only-finding=ID` limits a diagnostic to exactly one saved claim; `--skip-finding=ID` excludes an already-tested claim. Unknown options are rejected.
- Failed outputs are preserved. No hidden repair, uncertain-call retry, edited verdict, or application restart is used to claim acceptance.
- Criteria are in `evals/try5/literal-review-expectations.md`. Earlier failed v3/v4 experiments remain unchanged in their results files.
- The non-thinking candidates still approved a physical-absence overclaim. Native thinking alone at temperature zero exhausted its allowance; the documented thinking/sampling profile recovered the decisive distinction in one test, with an incomplete positive-listing quotation. This is not release acceptance. See `evals/try5/literal-review-results.md` for the complete evidence, including rejected candidates.

This is not an entailment prover. Authentic citations can be irrelevant; a model can still substitute a weaker claim or miss a conflict. Same-model evaluation is not independent corroboration. Passing this narrow gate is not a completed RCA.

The OpenAI Docs skill informed the distinction between [schema compliance and semantic correctness](https://developers.openai.com/api/docs/guides/structured-outputs) and the [frozen task-level evaluation](https://developers.openai.com/api/docs/guides/evaluation-best-practices). [Ollama's thinking documentation](https://docs.ollama.com/capabilities/thinking) informed the explicit provider-option experiment; it does not establish that this model will reason correctly.

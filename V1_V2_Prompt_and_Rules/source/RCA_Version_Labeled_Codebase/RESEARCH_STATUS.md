# Research status and limitations (October 2026)

## What is implemented

- Working code organized by major component, role, and hot-swappable policy.
- Model prompts in separate Markdown files, selected and SHA-256 fingerprinted by registry.
- Actual v2 `Kernel` and `Session` moved from the prior tested archive (not a rewrite). Includes lineage, alternatives/conjunctions, scoped retraction, need coverage, worker read-set validation, and snapshot persistence.
- Executable wet-floor model–tool loop: Intake → Specialist → Assessor → Controller → Lead → Evidence Worker → new source → repeat.
- Real HTTP interface for OpenAI-compatible completion endpoints (OpenRouter, OpenAI, Ollama), with explicit failure, optional JSON format and basic retries.
- Separate local-folder evidence host and synthetic six-document custodian; neither exposes future document text to the agent payload.
- Saved execution trace, model-call receipts, JSON checkpoint and interactive HTML viewer.
- 95 preserved v2 regression tests plus new architecture, provider, and end-to-end integration tests.

## What is NOT established

- No fresh independent live model call was made when building this repo. A configured OpenRouter key and outbound connectivity are still required.
- The authored fixture run is NOT autonomous LLM reasoning; the fake HTTP integration test only verifies the API protocol.
- New `causal_frontier` is a bounded prompt + deduplication strategy, not a learned/optimized missing-variable algorithm or reproduction of the IRIS paper.
- New `joint_route_planner` is an explicit heuristic over model-proposed options, not a calibrated information-gain planner or validated joint causal/access policy.
- `impact_aware` auto-flags hypotheses originating from corrected sources, but discovering *semantic* correction mappings still depends on model-supplied scoped targets. Exact-quote verification is not entailment verification.
- No independent industrial engineering evaluator, broad representative incident benchmark, semantic score, or operational safety validation has been run for this package.
- The current runtime is sequential. There is no parallel remote multi-agent executor, enterprise IAM connector, production human approval workflow or SQL database.
- PDF/scanned record parsing is outside the shipped built-in local-folder adapter; text files are required.

## Research priority

Compare a strong tool-equipped baseline against (A) missing-variable discovery, (B) joint causal-gap + evidence-route planning, and (C) impact reassessment under identical tool budgets and evidence distributions. Test across multiple independently reviewed incidents and blinded model operators, not just variations of one synthetic case.

## Prior-work inspiration (not direct implementations)

- IRIS, ACL 2025: https://aclanthology.org/2025.acl-long.463/
- MINT, ICML 2026: https://proceedings.mlr.press/v306/fang26i.html
- HARIS, ACL 2026: https://aclanthology.org/2026.acl-long.119/
- Original v2 source/test provenance: `tests/v2_regression/`, `revision/v2/` and the user's earlier `RCA_Revised_System_v2.zip`.


## Upgrade 01 — Agent implementation pass (2026-10-16)

Agent implementations now differ through executable algorithms, not only names/prompts. The adaptive Evidence Worker and impact-aware Assessor have independent model-call contracts; fixture doubles are authored, with no new external model inference. **155 passing tests**, original v2 engine preserved. See `AGENT_IMPLEMENTATION_UPGRADE.md`. More research-method and held-out validation remain outstanding.

## Upgrade 02 — Prompt/method/evaluation readiness (2026-10-16)

- **Implemented and tested:** distinct advanced Markdown prompts with role contracts, examples and source attribution; bounded contract/quote retry without oracle; one-step hypothesis-question coverage, budgeted source-route selection, conservative applicability/quarantine rules, and dependency-safe suppression of invalid gap resolutions.
- **Implemented and tested:** true five-role basic prompting baseline; independently hot-swappable prompt variants; four configurations separating prompts and methods. An offline `evaluation.run_matrix` and `evaluation.score_run` produce structural metrics, trace receipts, and blank independent-review instruments.
- **Not yet validated:** improvements to a real LLM's causal interpretation, generalization or physical correctness. No OpenRouter model request completed here; network/DNS and credentials absent. Human engineering reviewer and independently held-out industrial cases needed before research-performance claims. See `V2_COMPLETION_REPORT.md`.

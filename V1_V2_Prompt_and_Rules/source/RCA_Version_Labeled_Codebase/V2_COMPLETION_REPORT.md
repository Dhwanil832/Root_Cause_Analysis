# V2 remediation report — Prompts, bounded algorithms and evaluation

**Status as of 16 October 2026:** passes 2 and 3 are implemented and behaviorally tested. Pass 4 has a reproducible evaluation pipeline and offline adversarial tests; **independent LLM and engineer-reviewed validation remains BLOCKED** (no configured API key and no outgoing DNS in this execution environment). This is not a validated alternative to IRIS, MINT, or HARIS.

## What changed since Agent Upgrade 01

### Pass 2. Substantive Markdown prompts

The live V2 prompt files now contain: task-specific objectives and input-trust limits; explicit typed JSON response contracts; event/asset/configuration scope checks; reported versus measured versus conditional source modalities; bounded worklists; negative and positive *out-of-case* examples; evidence-attribution requirements; fallback to empty outputs; protection against prompt injection in source text; and final self-checks that do **not** request internal chain-of-thought.

Active files:

- `intake/agents/intake_agent/prompts/v2_structured_llm.md`
- `reasoning/specialist/prompts/{v2_causal_frontier,v2_iris_inspired}.md`
- `reasoning/lead/prompts/{v2_causal_guided,v2_joint_route_planner}.md`
- `reasoning/evidence_worker/prompts/v2_adaptive_routes.md`
- `reasoning/assessor/prompts/v2_impact_aware.md`

Every role also has a deliberate basic comparator. **Prompt variants are independently swappable** via `agents.<role>.prompt_implementation`, with SHA-256 hashes in run manifests. No Python edit is required to change prompts. The baseline non-generative files remain as documentation; the separate `prompt_only` implementations make actual model-interface calls for all five roles.

New `shared/contracts/task_validation.py` performs model-task-level validation, including exact current-document quote checks. `Investigator.ask_role` retries a malformed completion at most `contract_retries` times with only structural error feedback; it does not supply reference answers or fixture fallbacks. All attempts and rejection reasons are preserved.

**What is NOT proved:** better prompt reliability, reduced hallucination rate or model generalization. The same authored fixture answers were used regardless of prompt text; prompt performance must be measured with real model calls.

### Pass 3. Explicit V2 research-inspired processing

| Block | New computational procedure | Observable output | Not implemented / not claimed |
|---|---|---|---|
| Specialist | Compile a hypothesis ↔ missing-condition ↔ question coverage matrix; flag unasked conditions, shared-versus-distinguishing questions, and structural duplicate/self-causation proposals. | `_frontier_method_audit` and `gap.hypothesis_tests` / `discrimination_class` | No statistical causal discovery, no IRIS reproduction, no causal truth from lexical overlap. |
| Lead | One-step budgeted question/route coverage: compare candidate actions against open-gap scopes, candidate hypotheses, graph-frontier premises, visible custodian hints, repeat/burden penalties. | Ranked `score`, `breakdown` with features and cost penalties. | No expected information gain, simulated answers, optimality or V3 multi-step planning. |
| Evidence Worker | Build a visible gap–custodian graph and rank authorized routes by scope overlap, known/discovered status, directness, burden, attempted routes and multi-gap potential. | `ranked_public_route_candidates`, audited redirect/execute/hold. | No hidden source lookup, no truth about document existence, no learned route success probabilities. |
| Assessor | Pre-commit deterministic risk screen for conditional/later-test-to-incident misattributions, with conservative quarantine only for clear category errors; separate scoped model critique. Suppress dependent gap resolutions when their supporting claim is quarantined. | Scope audit, quarantine labels, suppressed resolution list. | No complete semantic entailment checker, expert physical reasoning or unsupervised reliable correction matching. |

The previously implemented v2 versioned source/AND-OR justification engine, scoped correction propagation and closure guards remain unchanged in `revision/v2/`. Only the controller commits findings; the new proposed questions and model-generated beliefs never create physical evidence by themselves.

The new procedures are more substantive than role prompts but remain **finite, single-step, heuristic modules**. That is intentional: a future V3 method will explore hypothetical action outcomes and multi-step information-acquisition consequences. We must not relabel these V2 procedures as our novel V3 algorithm.

### Pass 4. Better validation infrastructure, not yet live validation

The existing 95 v2 kernel regressions are preserved. New tests probe distinctions that the old 130-test suite did not, including:

- Two hypotheses sharing the accident outcome but requiring **different missing conditions** must not appear resolved by the same generic question.
- A route serving multiple open questions should receive a larger one-step coverage score than the same route serving one, all else equal.
- Higher request burden must lower the ranking; previously exhausted routes are ineligible.
- A later test must not automatically be treated as an incident-time measurement, but a correctly scoped later-test claim should remain admissible.
- If a claim is quarantined, the dependent request cannot be silently marked resolved, and the raw source is still available.
- Malformed task-specific outputs, invented current-document quotations, hidden reference fields, and unauthorized route IDs must be rejected.
- A bounded schema retry may correct formatting without injecting answer keys.
- Live-provider preflight failure cannot be relabeled a successful model run.

`evaluation/run_matrix.py` runs four fresh, isolated configurations. The offline evaluator produces `evaluation_report.json` and a blank `manual_review.csv` for a domain expert. An author-only fixture manifest supplies SIX behavioral invariants; these are NOT a model accuracy benchmark.

### Four-way reproducible ablation

| Experiment | Implementations | Prompts | What it isolates |
|---|---|---|---|
| `v1_prompt_only` | Five prompt-only roles | Basic | Stronger comparator than the previous non-generative Assessor/Evidence Worker baseline |
| `v2_prompts_only` | Same V1 algorithms | New V2 prompts | Effect of prompt engineering alone, **only with actual LLM inference** |
| `v2_methods_only` | New V2 modules | Basic prompts | Effect of processing methods alone |
| `v2_full` | New V2 modules | New V2 prompts | Joint integration; synergy requires model/expert evaluation |

All four synthetic reference runs preserved the reported slip/wet floor, withdrew the corrected camera claim, retained the unresolved upstream question and refused premature sign-off. This only shows that the author-supplied outputs and revision rules produced the required state. It does not show improved prompt quality or statistically meaningful model performance. The number of model-interface calls varies because different policies take different paths, which must be recorded in comparisons.

## Run the code

Install and test:

```bash
python -m pip install -e '.[test]'
python -m pytest -q
```

Run the complete offline factorial fixture comparison:

```bash
python -m evaluation.run_matrix --mode fixture --output outputs/v2_factorial
```

Score one run and create the expert review sheet:

```bash
python -m evaluation.score_run outputs/v2_factorial/v2_full --fixture-reference
```

**Independent API trial (only on a machine with network and a secret configured):**

```bash
export OPENROUTER_API_KEY='YOUR_LOCAL_SECRET'   # never paste into chats or a repository
python -m evaluation.run_matrix --mode live \
  --provider openrouter \
  --model 'nvidia/nemotron-3-super-120b-a12b:free' \
  --max-actions 6 \
  --output outputs/openrouter_pilot
```

For a later full comparison increase `--max-actions` and use held-out incident/evidence directories (`--incident`, `--evidence-dir`). Check endpoint availability, account quotas, budgets, and model options first. Each configuration is a fresh investigation with its own source state. Provider errors write partial traces; **no authored fallback occurs**.

## Scientific limitations and completion gate

1. **No independent real LLM evaluation was possible here.** The free OpenRouter endpoints require a reachable network and a configured account/key. Actual completed provider calls in this build: **zero**.
2. Only the authored six-source wet-floor fixture was used for the four-way connected comparison. Other historical v2 scenario replays and regression tests do not constitute independent industrial incidents.
3. Prompt improvements were not evaluated by the authored model double, which ignores prompts.
4. Domain-specific semantic correctness and physical causality need independent engineering review. An exact quote is not an entailment guarantee.
5. Methods are inspired by related research, not equivalent implementations of IRIS (statistical+LLM causal discovery), MINT (symbolic tree+learned planning) or HARIS (RL-trained joint search/reasoning).
6. A credible paper must control the underlying model and budget; report failures, rejected updates, missing routes and exposure differences; and evaluate on multiple independent held-out incidents.

**The V2 engineering and offline evaluation infrastructure are ready for model-based tests; V2's scientific validation is not complete.** Move to V3 design only with that limitation kept explicit, or perform live V2 trials first when an endpoint is available.

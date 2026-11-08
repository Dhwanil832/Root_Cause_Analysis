# Upgrade 01 — Substantive agent implementations (16 October 2026)

This is the **first** of four planned remediation passes. It addresses the former empty wrappers and agent policies that differed only by their names. It does **not** claim to complete advanced prompt engineering, formalize a research-novel planner, or validate an autonomous LLM on held-out cases.

## What changed, exactly

| Role | Deliberately simple comparator | Enhanced policy and concrete change | Main code |
|---|---|---|---|
| **Intake** | Model assertions go directly to mandatory v2 quote/identity validation | Additional normalization identifies duplicate scoped claims, blocks reused semantic labels assigned to different identities, rejects contradictory same-scope declarations in one extraction, and flags possibly inappropriate measurement/conditional modalities without manufacturing evidence. | `intake/agents/intake_agent/components/normalization.py` |
| **Specialist** | Retain all model-proposed candidate hypotheses, needs and inferences for later host validation | `causal_frontier` checks for self-causation and duplicate causal premises and connects each gap with hypotheses it could help discriminate. The distinct `iris_inspired` variant ALSO converts one untested hypothesis condition into a **question**, only with current-source grounding and previously visible route hints. Never promotes missing conditions to facts. | `reasoning/specialist/components/{frontier_policy,abductive_questions}.py` |
| **Lead** | Select first admissible action in model-supplied order | `causal_guided` scores direct tests for unresolved causal questions; `joint_route_planner` additionally builds a *gap → proposed custodian* reachability relation and credits discovery of a route that could serve multiple open gaps. Both provide numerical scoring breakdowns, including limitations. | `reasoning/lead/components/planning_features.py`, `reasoning/lead/implementations/` |
| **Evidence Worker** | Execute Lead's approved action with a discovered-before-request guard | Independent `plan_route` model call can execute, redirect to a permitted public route, or hold. A deterministic validator checks gap scope, route authorization, prior attempts and whether a route is discovered. Tracks failures and incomplete responses. | `reasoning/evidence_worker/components/route_decision.py`, `implementations/v2_adaptive_routes.py` |
| **Assessor** | Source-quote and v2 structural validation only | Independent `review_assessment` model call, before committing; can quarantine individual proposed assertions, hypotheses or causal inferences, but cannot invent sources, add claims, modify corrections, or commit state. Exclusions require a verbatim quote and explicit warning; original source is still admitted. Source-origin hypotheses are flagged for reassessment on scoped corrections, not declared false. | `reasoning/assessor/components/proposal_review.py`, `implementations/v2_impact_aware.py` |

All implementations are selected with `config/*.yaml` through the allowlisted registry. The existing `revision/v2/` trusted kernel and source/justification graph were **not rewritten**. Every model-visible payload passes a recursive private-field guard (`reasoning/context/context_builder.py`) and is deep-copied.

**Real LLM role calls in the enhanced configuration:** `extract` (Intake), `frontier` (Specialist), `review_assessment` (Assessor), `propose_actions` (Lead) and `plan_route` (Evidence Worker). The last two formerly had no independent model tasks. In baseline mode the Assessor and Evidence Worker deliberately omit these extra model calls, so ablations have real cost differences.

## Algorithmic distinction (not just different prompts)

- Specialist **baseline vs causal_frontier**: identical candidate models can yield different allowed inference proposals because the enhanced policy rejects self-causing effects and repeated premises.
- Specialist **causal_frontier vs iris_inspired**: only the latter attempts bounded, source-grounded conversion of an untested condition to an additional evidence question. This is *inspired* by missing-variable research, **not** a reproduction of IRIS.
- Lead **causal_guided vs joint_route_planner**: when the same unavailable custodian is proposed for three open questions, the joint planner can prioritize discovering it over requesting a single available but less broadly useful document; the causal-only planner prioritizes the direct question. This is an **ordinal heuristic**, not calibrated expected information gain or optimal planning.
- Evidence Worker **baseline vs adaptive_routes**: enhanced policy can make a separate model decision to reroute an approved information need, but cannot bypass discovery or use a custodian absent from the public set or the gap's candidate hints.
- Assessor **baseline vs impact_aware**: same proposed observation can be committed by baseline and quarantined by an enhanced assessor's explicit, source-grounded objection. This is an intentionally injected test, *not* measured spontaneous ability to catch hallucinations.

## What is actually tested

Commands from project root:

```bash
python -m pytest -q
python main.py --mode fixture --config config/experiments/ablation_no_llm.yaml --output outputs/check_baseline
python main.py --mode fixture --config config/experiments/v2_full.yaml --output outputs/check_enhanced
```

**Newly checked on 16 October 2026:** 155 Python tests passed, including the 95 historical v2 regression tests (older test count: 130). Agent-specific tests exercise scoped intake collisions, modality flags, circular inferences, bounded unanswered-condition question generation, distinct Lead selection, route authorization/redirection, model-review quarantine, nested-reference leakage prevention and distinct model-call interfaces. The fake HTTP model endpoint still tests transport, **not actual model intelligence**.

### Authored-fixture runs (not blind inference)

| Profile | Total model-interface calls | Actual remote model calls | Sources received | Assessor model tasks | Evidence-worker model tasks | Terminal status |
|---|---:|---:|---:|---:|---:|---|
| `baseline` | 21 | 0 | 6/6 | 0 | 0 | No admissible action |
| `full_system` | 33 | 0 | 6/6 | 6 | 7 | No admissible action |
| `iris_prompt` | 21 | 0 | 6/6 | 0 | 0 | No admissible action |

The enhanced fixture run retained the wet-floor/slip reports, withdrew camera-derived F-2 cleaning support after its correction, and left unresolved upstream information needs. The `iris_prompt` variant generated additional questions (8 instead of the baseline's 4); **number of generated questions is not a measure of usefulness, correctness or research gain**. All fixture decisions were scripted/author-supplied; the policy algorithms then operated on those outputs.

## Important limitations and risks

1. **No autonomous external-model validation occurred during this upgrade.** A fake HTTP responder and authored fixtures cannot establish Nemotron, GPT or Qwen reliability. Failure-free JSON transport is not semantic correctness.
2. **Reviewer correctness is not guaranteed.** The enhanced Assessor can quarantine a valid claim, miss a false one or be fooled by a quote that does not entail the interpretation. Reviewer exclusions and flags must be evaluated by an independent expert.
3. **Planning is heuristic.** No learned response-outcome model, probability calibration, empirical action values or proven causal discovery is implemented. Two-stage route value is an ordinal heuristic with bounded counts, not a formal solved POMDP.
4. **Source-route access remains a toy environment** for fixture runs; a production search worker needs permissioned connectors, identity resolution and realistic retrieval/availability handling.
5. **The implementations are hot-swappable between runs** under common contracts. Switching policies in the middle of a live session needs explicit task cancellation, event replay and state-compatible migrations; none is implemented.
6. **Adding a second reviewer and route model call increases the cost** (33 vs 21 authored interface calls for this fixture). This is an ablation variable, not free performance.
7. Exact-quote validity, document origin metadata, and versioned support protect evidence bookkeeping; **none independently proves a physical causal statement**.

## Directory guide

```text
intake/agents/intake_agent/{agent.py,implementations/,components/,prompts/}
reasoning/specialist/{agent.py,implementations/,components/,prompts/}
reasoning/lead/{agent.py,implementations/,components/,prompts/}
reasoning/evidence_worker/{agent.py,implementations/,components/,prompts/}
reasoning/assessor/{agent.py,implementations/,components/,prompts/}
reasoning/context/context_builder.py
revision/{controller.py,v2/}
orchestration/{orchestrator.py,scheduler.py,state.py}
shared/{registry.py,contracts/,llm/,prompt_loader.py}
config/{default.yaml,experiments/}
tests/agents/
```

Unused one-liner modules claiming to be components but not actually invoked were **removed**. Empty package markers (`__init__.py`) and small, genuine single-purpose contracts remain where needed. Do not measure implementation quality by lines of code alone.

## What comes next (passes 2–4)

**Pass 2: Prompt engineering** — design and test per-role prompts with grounded task decompositions, useful output schemas, uncertainty, explicit negative/contrastive examples, recovery instructions, model-specific formatting and versioned prompt ablations. The new Assessor and Evidence Worker prompts currently specify minimum usable contracts; they have not been empirically optimized.

**Pass 3: Research method** — replace the provisional frontier and route heuristics with a specified, falsifiable algorithm for coupled causal-frontier and evidence-access planning; compare it to strong equal-tool prompted-agent baselines and independent information-acquisition methods.

**Pass 4: Scientific evaluation** — blinded fresh-agent trajectories, held-out industrial cases, expert-reviewed causal correctness, precision/coverage, evidence-source route retrieval, cost, failure analysis and correction accuracy. Do not conflate the source count or unit-test count with independent industrial case count.

# RCA Project navigation: find one responsibility in one location

This guide reflects the **actual executable structure after Upgrade 01**, not a wish list. For technical caveats see `AGENT_IMPLEMENTATION_UPGRADE.md`.

## Run / select / inspect

| Task | Where |
|---|---|
| Execute investigation | `python main.py --mode fixture` or `--mode live` |
| Select models and components | `config/default.yaml`, `config/experiments/*.yaml` |
| Read the current investigative execution loop | `orchestration/scheduler.py` |
| See how five role interfaces are composed | `orchestration/orchestrator.py` |
| Inspect public state and saved logs | `orchestration/state.py` |
| Find a model/provider interface | `shared/llm/client.py` |
| Find the authored test double | `shared/llm/fixture.py` (never a live model) |
| Learn how policies are selected | `shared/registry.py` |
| Find prompt files and hashes | `shared/prompt_loader.py` |
| Audit whether a role sees private keys | `reasoning/context/context_builder.py` |

## Agent folders, including every active implementation

**Naming:** `v1_basic` is the five-agent prompt baseline; `v2_*` is a V2 enhancement; `ablation_no_llm` disables a second-stage LLM role to isolate its contribution.

```text
intake/agents/intake_agent/
  agent.py
  implementations/
    v1_basic.py               prompt-only extraction baseline
    v2_structured_llm.py      identity/modality screening
  components/                 normalization, quote/identity checks
  prompts/
    v1_basic.md
    v2_structured_llm.md

reasoning/specialist/
  agent.py
  implementations/
    v1_basic.py               model hypotheses passed to mandatory validation
    v2_causal_frontier.py     structural and duplicate checks, gap linking
    v2_iris_inspired.py       extra bounded missing-condition questions
  components/                 frontier/abduction/graph components
  prompts/
    v1_basic.md
    v2_causal_frontier.md
    v2_iris_inspired.md

reasoning/lead/
  agent.py
  implementations/
    v1_basic.py               first-admissible model-order selection
    v2_causal_guided.py       direct causal relevance scoring
    v2_joint_route_planner.py single-step causal/route coverage ranking
  components/                 admissibility, coverage scoring, action selection
  prompts/
    v1_basic.md
    v2_causal_guided.md
    v2_joint_route_planner.md

reasoning/evidence_worker/
  agent.py
  implementations/
    v1_basic.py               basic prompting for execute/redirect/hold
    v2_adaptive_routes.py     ranked public-route proposals and coverage tracking
    ablation_no_llm.py        direct dispatch with no worker LLM call
  components/                 access control, discovery, route validation
  prompts/
    v1_basic.md
    v2_adaptive_routes.md
    ablation_no_llm.md

reasoning/assessor/
  agent.py
  implementations/
    v1_basic.py               basic prompting for critique/quarantine
    v2_impact_aware.py        scoped critique and postcommit flags
    ablation_no_llm.py        structural validation only; no Assessor LLM call
  components/                 source scope, proposal review, correction checks
  prompts/
    v1_basic.md
    v2_impact_aware.md
    ablation_no_llm.md
```

For every `v1_basic` or `v2_*` implementation, the matching prompt lives under that role's `prompts/` directory. In ablation profiles, the implementation and prompt version can intentionally differ; inspect both YAML fields.

## Trust boundary

- `revision/controller.py` is the only writer of accepted v2 update transactions.
- `revision/v2/kernel.py`, `session.py`, `broker.py` retain the original versioned evidence/justification runtime; agent enhancements may propose updates but cannot bypass validation.
- `integrations/evidence_sources/` implements **restricted** local and synthetic custodians. The synthetic world's hidden inventory is not included in any model prompt.
- `evaluation/private_reference/` is **author-only**. Do not attach it, fixture response templates, answer keys, or prior completed RCA charts to an investigator-model prompt.
- `tests/agents/` contains tests showing actual behavioral differences. `tests/v2_regression/` protects historical revision semantics.

## Next stages not claimed as completed

The V2 Markdown prompts are upgraded. A scientifically validated novel planner, independent external-model investigations, and held-out engineering reviews remain future work. Passing fixture tests do not establish autonomous reasoning quality.

**Note:** For Evidence Worker and Assessor, the old non-generative `baseline.py` is now `ablation_no_llm.py`, while the old five-agent `prompt_only.py` is `v1_basic.py`. See `VERSION_GUIDE.md`.

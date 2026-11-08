# Which implementation belongs to V1 or V2?

**All agent folders use the same naming convention.**

- `v1_basic.py` / `v1_basic.md`: true **V1 five-agent prompt-only baseline**. The model is called in every role.
- `v2_<method>.py` / `v2_<method>.md`: **V2 research-inspired variant**. Descriptive method name follows the version.
- `ablation_no_llm.py` / `ablation_no_llm.md`: **non-generative control** for Evidence Worker or Assessor only. Not V1.
- `v3_*.py`: reserved for future V3 methods; **none exist yet**.

## Find the exact file

| Role | V1 prompt-only | V2 choice(s) | Non-generative control |
|---|---|---|---|
| Intake | `intake/agents/intake_agent/implementations/v1_basic.py` | `v2_structured_llm.py` | — |
| Specialist | `reasoning/specialist/implementations/v1_basic.py` | `v2_causal_frontier.py`, `v2_iris_inspired.py` | — |
| Lead | `reasoning/lead/implementations/v1_basic.py` | `v2_causal_guided.py`, `v2_joint_route_planner.py` | — |
| Evidence Worker | `reasoning/evidence_worker/implementations/v1_basic.py` | `v2_adaptive_routes.py` | `ablation_no_llm.py` |
| Assessor | `reasoning/assessor/implementations/v1_basic.py` | `v2_impact_aware.py` | `ablation_no_llm.py` |

Each agent has a **matching Markdown filename** under its `prompts/` directory. The old `baseline` implementation for Evidence Worker and Assessor had **no separate LLM call** and is deliberately named `ablation_no_llm`, not `v1_basic`.

## Profiles to run

| Profile | What it actually changes |
|---|---|
| `config/experiments/v1_basic.yaml` | Five agent roles use V1 basic prompting |
| `config/experiments/v2_full.yaml` | All selected V2 algorithms and their improved prompts |
| `config/experiments/v2_prompts_only.yaml` | V1 algorithms with V2 prompts |
| `config/experiments/v2_methods_only.yaml` | V2 algorithms with V1 prompts |
| `config/experiments/ablation_no_llm.yaml` | Historical minimal configuration; Evidence Worker and Assessor do not call LLMs |
| `config/experiments/ablation_v2_*.yaml` | Isolate one or two V2 components |

The default `config/default.yaml` selects the full V2 setup.

**Prompt and algorithm are independent for ablation tests.** A profile may deliberately use `implementation: v1_basic` and `prompt_implementation: v2_causal_frontier` to measure prompt engineering alone. This is intentional, not mislabeling.

## Version naming clarification

The directory `revision/v2/` is the previously tested **version 2 evidence-kernel implementation**. Its `v2` refers to the evidence engine, not to a particular agent experiment profile. That kernel is used by both the V1 and V2 agent configurations and has **not been renamed or modified**.

The old experiment outputs are preserved as historical records; their run manifests naturally contain the **old names**. Do not use archived manifests to identify the current file paths. For new runs, names in the manifests match the version-prefixed modules.

No autonomous external-model trial is implied by these file renames.

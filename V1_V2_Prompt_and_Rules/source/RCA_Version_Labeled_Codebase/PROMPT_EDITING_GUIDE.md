# Prompt editing, method switching, and avoiding fake ablations

Each active agent prompt lives at `intake/agents/intake_agent/prompts/*.md` or `reasoning/<role>/prompts/*.md`.

To change the **text only**, edit a `.md` file; restart the next run. The registry records the SHA-256 content hash in `component_manifest.json` and `summary.json`. Editing a prompt alone never changes `revision/v2/` or the algorithm code.

To compare the effect of **prompt text** while keeping the same processing algorithms, use `config/experiments/v1_basic.yaml` versus `config/experiments/v2_prompts_only.yaml`. To compare **methods** with basic prompts, use `methods_only.yaml`. The full V2 policy is `full_system.yaml`.

If you modify a prompt, update its example and contract consistently; task contracts are in `shared/contracts/task_validation.py` and stricter transactional checks in the agent components/v2 controller. JSON code fences in Markdown are **examples**, not a request to return fences. Always enforce exact source quote, source ID, context scope and correction dependencies.

For an independent LLM test, do not pass the repository's `evaluation/private_reference/` folder, designer-only source inventory, reference RCA chart, other model traces or rubric to the model. The tool-access host may keep a private inventory; the agent receives only released records. **FixtureModel completely ignores prompt text**, so a clean authored fixture execution is not evidence a prompt revision helped.

Avoid prompts that request hidden reasoning traces, unlimited speculation, fictitious probabilities, invented document IDs, fixed root-cause answers or unsupported evidence. A well-designed prompt provides choices to abstain or keep uncertainties open.

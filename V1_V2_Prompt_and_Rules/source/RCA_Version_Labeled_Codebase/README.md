# Version-labeled agent implementation layout

All agent implementations and Markdown prompts now use explicit `v1_`, `v2_`, or `ablation_` prefixes. See **[VERSION_GUIDE.md](VERSION_GUIDE.md)** for the exact agent-by-agent mapping and four comparison profiles. V3 is not implemented.

---

# Progressive RCA — modular investigation research system

> **Upgrade 01 (2026-10-16):** Former placeholder agent modules were replaced with distinct role policies; both Assessor and adaptive Evidence Worker now have their own model-call interfaces. The trusted v2 engine is unchanged. **155 tests passed**, but **0 genuine new LLM inference calls** were made in this upgrade. See [AGENT_IMPLEMENTATION_UPGRADE.md](AGENT_IMPLEMENTATION_UPGRADE.md) for precise code paths, evidence and limitations.


**Executable Python research prototype.** The folder structure follows the architecture we agreed on: **Intake → Reasoning (Specialist, Lead, Evidence Worker, Assessor) → Revision (v2 controller/ledger) → Orchestration**. Prompts live in **editable Markdown files** next to their agent. Every LLM agent has a stable `agent.py` entry point and an allowlisted, configuration-selectable `implementations/` directory.

**Read first:** [NAVIGATION.md](NAVIGATION.md) for a direct “where do I edit X?” map, [ARCHITECTURE.md](ARCHITECTURE.md) for interactions, and [RESEARCH_STATUS.md](RESEARCH_STATUS.md) for what is genuinely implemented versus proposed.

## Quick start

Requires **Python 3.10+**. From the project root:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python main.py --mode fixture --output outputs/demo
```

Open `outputs/demo/investigation_viewer.html` in a browser. Inspect `outputs/demo/trace.json`, `outputs/demo/session.json`, `outputs/demo/summary.json` and `outputs/demo/model_calls.json` for the actual executed state.

**Important:** `--mode fixture` uses **author-written test responses**, not an LLM. It is an integration / regression check and never demonstrates autonomous reasoning.

## Run Nemotron or GPT-OSS via OpenRouter

1. Create a separate API key at OpenRouter and keep it locally, never in chat or in a committed repository.
2. Set `OPENROUTER_API_KEY` in your OS environment (or create a local `.env` if you use the optional loader).
3. Run the appropriate command, with your chosen accessible model ID:

**macOS / Linux:**

```bash
export OPENROUTER_API_KEY="your-private-key"
python main.py --mode live \
  --provider openrouter \
  --model 'nvidia/nemotron-3-super-120b-a12b:free' \
  --max-actions 12 --output outputs/nemotron
```

**Windows PowerShell:**

```powershell
$env:OPENROUTER_API_KEY = 'your-private-key'
python main.py --mode live --provider openrouter --model 'openai/gpt-oss-120b:free' --max-actions 12 --output outputs/gptoss
```

A configured provider endpoint must actually be reachable. Free-model IDs, quotas, JSON-mode support and access can change; check your account's current OpenRouter model list. The default model is an **example**, not a guarantee of free inference. The default does **not** send the optional `response_format` field because some provider variants reject it. To enable JSON-object response mode on a supported provider, change `llm.response_format` to `json_object`.

**No LLM key or provider connection → no live run.** There is no silent mock fallback. HTTP transport retries malformed JSON or transient failures as configured; structurally invalid causal updates are rejected rather than silently committed.

## Run your own case

Convert the incident report and relevant evidence to `.md`, `.txt`, `.csv` or `.json`. Provide an incident file and a directory containing **custodian subfolders**. The agent initially receives **only the incident report** and learns route names via discovery, not filenames.

```text
your_case/
├── incident.md
└── evidence/
    ├── security/
    │   ├── route_description.md
    │   └── camera_note.md
    ├── maintenance/
    │   ├── route_description.md
    │   └── maintenance_log.md
    └── unsolicited/
        └── later_correction.md
```

Then run:

```bash
python main.py --mode live \
  --incident your_case/incident.md \
  --evidence-dir your_case/evidence \
  --output outputs/your_case
```

The included local-file custodian performs simple lexical retrieval and **does not represent enterprise integrations or trained semantic search**. Source identities are based on filenames without extensions, so use unique names across folders. PDFs and scanned documents require an actual extractor; this prototype **refuses** to parse binary files rather than pretending to understand them.

## Switch agent implementation without editing Python

Choose an experiment profile:

```bash
python main.py --mode fixture --config config/experiments/ablation_no_llm.yaml --output outputs/baseline
python main.py --mode fixture --config config/experiments/v2_full.yaml --output outputs/extended
```

Or modify `config/default.yaml`:

```yaml
agents:
  specialist:
    implementation: causal_frontier
  lead:
    implementation: joint_route_planner
  evidence_worker:
    implementation: adaptive_routes
  assessor:
    implementation: impact_aware
```

Every strategy implements a fixed role contract (e.g. `rank(runtime, actions, public_state)` for Lead). The allowlisted `shared/registry.py` selects the module and loads a matching `.md` prompt at startup. Modules can be switched **between runs**; in-flight work is not hot-patched mid-call. For a new strategy, create its Python file, `.md` prompt, registry allowlist entry, contract tests and an experiment profile. To route roles to different models, set `agents.<role>.provider` and/or `agents.<role>.model` in YAML.

## Where to edit each part

| Want to change... | Open this file/folder |
|---|---|
| Intake prompt | `intake/agents/intake_agent/prompts/v2_structured_llm.md` |
| Intake extraction and source-quote checks | `intake/agents/intake_agent/agent.py`, `components/assertion_validator.py` |
| Specialist causal/missing-variable prompt | `reasoning/specialist/prompts/v2_causal_frontier.md` |
| Specialist hypothesis/gap normalization | `reasoning/specialist/components/` |
| Lead's planning policy | `reasoning/lead/implementations/v2_joint_route_planner.py` |
| Lead prompt | `reasoning/lead/prompts/v2_joint_route_planner.md` |
| Evidence route discovery/request | `reasoning/evidence_worker/agent.py`, `components/`, `implementations/` |
| Assessor correction and coverage checking | `reasoning/assessor/agent.py`, `components/` |
| Tested evidence provenance and revision behavior | `revision/v2/kernel.py`, `revision/v2/session.py` |
| Run loop / next agent scheduling | `orchestration/orchestrator.py`, `orchestration/scheduler.py` |
| Model provider and JSON transport | `shared/llm/client.py` |
| Select implementations / load Markdown prompts | `shared/registry.py`, `shared/prompt_loader.py` |
| Synthetic wet-floor evidence environment | `integrations/evidence_sources/synthetic_world.py` |
| Full original v2 regression suite | `tests/v2_regression/` |

## Output interpretation and safety

- `source_assessed` means a model-produced interpretation was structurally accepted with exact-source-substring citations. It is **not** a certification that those excerpts entail the model's claim.
- A causal `qualified_partial_support` means a **qualified, controller-recorded model inference**, not a full industrial causal proof.
- The v2 ledger retains independent evidence on scoped corrections, separate causal proposals vs. evidence justifications, request partial/unavailable states, and provenance changes.
- The newer `causal_frontier`, `joint_route_planner`, `adaptive_routes`, `impact_aware` **are implementation candidates, not validated published algorithms**. The planner uses explicit heuristic scores, not calibrated expected information gain; the IRIS-inspired mode is a prompt variant, **not a faithful implementation of IRIS**.
- A fresh external autonomous model has not been tested in this delivery; real provider calls require credentials and networking. An HTTP mock is not an actual LLM.
- Private reference/rubric/model-fixture answer files in `evaluation/private_reference/` are **host-only**. Do not pass that folder (or the entire repository as a tool-accessible workspace) to a blinded candidate. The host should enforce file access isolation; this program only restricts what appears in model messages.
- **Not suitable for real industrial safety conclusions without human engineering review.**

## Tests and reproducibility

```bash
python -m pytest -q
python -m compileall -q intake reasoning revision orchestration integrations shared
```

Included: original **95 v2 regressions** migrated to new module locations, plus integration, contract, local-world, and provider tests (including a fake HTTP endpoint). Test outputs use authored synthetic labels or fake network responses. The local HTML replay is generated from the actual trace and requires no external service.

---

## Upgrade 02 — V2 prompts, bounded methods and evaluation (2026-10-16)

**Start here:** [`V2_COMPLETION_REPORT.md`](V2_COMPLETION_REPORT.md), [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md), [`PROMPT_EDITING_GUIDE.md`](PROMPT_EDITING_GUIDE.md), and [`METHODS_AND_CITATIONS.md`](METHODS_AND_CITATIONS.md).

The five role-facing enhanced Markdown prompts are substantive, distinct and contract-based. The Specialist compiles a hypothesis/condition/question coverage matrix; the Lead uses auditable one-step weighted question coverage; the Evidence Worker sees only a visible custodian-route ranking; and the Assessor performs conservative temporal/modal source-scope risk checking before its model critique. Every accepted revision continues through the original v2 kernel.

Two genuinely prompt-only role policies were added for fairer comparisons. `config/experiments/v1_basic.yaml` (V1), `prompts_only.yaml`, `methods_only.yaml`, and `full_system.yaml` (V2) form a four-way ablation; prompts are selectable separately from Python strategies through `prompt_implementation`.

**Reproduce offline:** `python -m pytest -q` then `python -m evaluation.run_matrix --mode fixture --output outputs/v2_factorial`. For a network-enabled real OpenRouter run, set `OPENROUTER_API_KEY` securely and use `python -m evaluation.run_matrix --mode live --provider openrouter --model '<MODEL_ID>' --max-actions 6 --output outputs/live_pilot`. No fixture response is substituted on a real-model error.

**Scientific qualification:** authored fixtures and tests establish software behavior, not LLM reasoning quality. External inference and independent industrial engineering review were unavailable during this build; live scientific validation remains pending.

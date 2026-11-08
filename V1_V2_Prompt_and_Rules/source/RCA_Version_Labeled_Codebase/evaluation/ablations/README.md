# Controlled ablations

Start all comparisons from a fresh case with the same initial visible evidence.

- `config/experiments/ablation_no_llm.yaml`: baseline policies for all roles.
- `config/experiments/ablation_v2_frontier_only.yaml`: replace only the Specialist.
- `config/experiments/ablation_v2_planner_only.yaml`: replace only the Lead.
- `config/experiments/ablation_v2_route_only.yaml`: replace only Evidence Worker.
- `config/experiments/ablation_v2_assessor_only.yaml`: replace only Assessor.
- `config/experiments/ablation_v2_planner_and_routes.yaml`: replace Lead and Evidence Worker together.
- `config/experiments/v2_full.yaml`: all candidate enhancements.

Every ablation profile explicitly lists all roles; the config loader deep-merges those selections over defaults without changing the fixed evidence engine or model settings.

Never compare model calls without controlling requested evidence, action budgets, provider changes, and stopped/error states. `metrics/basic.py` computes descriptive execution counts, not RCA quality.

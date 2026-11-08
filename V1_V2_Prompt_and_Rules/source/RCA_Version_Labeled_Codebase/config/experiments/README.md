# Choose an RCA configuration

| File | Purpose |
|---|---|
| `v1_basic.yaml` | **V1:** prompt-only policies for all five agents |
| `v2_full.yaml` | **V2:** current enhanced prompts and methods |
| `v2_prompts_only.yaml` | **Ablation:** upgraded V2 prompts, V1 methods |
| `v2_methods_only.yaml` | **Ablation:** V2 methods, V1 prompts |
| `ablation_no_llm.yaml` | **Historical minimalist control:** skips LLM calls for Worker and Assessor, unlike true V1 |
| `ablation_v2_*.yaml` | Isolate selected V2 reasoning/routing/assessment methods |
| `v2_openrouter_*.yaml` | Model/provider override; defaults remain V2 |

Example:

```bash
python main.py --mode fixture --config config/experiments/v1_basic.yaml --output outputs/v1
python main.py --mode fixture --config config/experiments/v2_full.yaml --output outputs/v2
```

Read `VERSION_GUIDE.md` for every implementation/prompt filename and the distinction between experiment versions and the separate versioned evidence kernel.

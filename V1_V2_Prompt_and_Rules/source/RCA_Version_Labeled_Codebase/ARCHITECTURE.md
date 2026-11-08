# Progressive RCA execution architecture — Upgrade 01

## Actual runtime loop

```text
Initial report / later requested record / unsolicited correction
      |
      v
  Intake (extract; optionally normalize and flag modality)
      |
      v
  Specialist (conditional hypotheses, gaps, graph/causal checks)
      |
      v
  Assessor (optional independent model critique, quarantine unsupported proposals)
      |
      v
  Controller + V2 kernel (validated raw source + versioned claim/support transaction)
      |
      v
  Lead (candidate actions, admissibility, causal or joint-route scoring)
      |
      v
  Evidence Worker (optional model route replan, public-route guard, tool execution)
      |
      +---- newly delivered document ---------------+
      |                                              |
      +---- next decision after state update <-------+
```

Every role has its own Markdown prompt and an explicit strategy interface selected through `shared/registry.py`; strategies can be changed **between runs** using YAML. Agents have no permission to directly modify the trusted v2 kernel. The Assessor stages model-produced corrections and causal proposals; the controller verifies and commits them.

## The five agent contracts

| Role | Executed policy interface | Model task(s), enhanced vs baseline | Main outputs |
|---|---|---|---|
| Intake | `normalize(raw)` | Both: `extract` | scoped source assertions, audit flags |
| Specialist | `transform(raw, public)` | Both: `frontier` | hypotheses, missing information, conditional inferences |
| Lead | `rank(runtime,actions,public)` | Both: `propose_actions` | filtered, ordered executable actions with score explanations |
| Evidence Worker | `execute(runtime,action)` | Enhanced only: `plan_route` | route decision, search/request, receipt or failure |
| Assessor | `review(runtime,source,state,extraction,frontier,new_claims)` | Enhanced only: `review_assessment` | quarantines/warnings and bounded proposed causal updates |

## Models and trust assumptions

- **Model responses are untrusted proposals.** Host validations check source IDs, allowed quote spans, identities, route authorization, updates, and reason codes. These validators cannot determine semantic truth or physical causality from text alone.
- The *same* model endpoint may serve all roles; separate calls are logically distinct agent tasks, **not five independently trained models**.
- The causal/route planner currently uses an **explainable ordinal heuristic**, not calibrated expected information gain or an optimal decision policy. The proposed joint missing-causal-variable and evidence-route research method still needs scientific development.
- The Assessor critique is a second source-grounded model judgment, **not** an external human or engineering verifier. A quote can be present but still fail to support a statement.
- The source's arrival timing is controlled by the evidence environment. Future documents and reference answers are never included in the model-visible JSON state.
- Stopping at a tool/evidence boundary does not equal completing industrial root-cause investigation.

All test results and invocation details are in `AGENT_IMPLEMENTATION_UPGRADE.md`. The diagram above describes executable software; any claims of model accuracy or research novelty require held-out trials and ablations.

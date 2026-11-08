# CFERP Lead Core

**Causal-Frontier and Evidence-Route Planning (CFERP)** is the standalone Lead
workflow for coordinating one investigation across parallel SAHS Specialists,
EWV3 Evidence Workers, HERA1 Assessors, and Intake. The package owns the shared
case state, routing, version checks, task lifecycle, queue, and outward request
control. It does not embed the reasoning performed by those roles.

## What is implemented

- **Case launch:** cue-map selection launches every matching Specialist profile
  and always includes the configured `Other` coverage profile. Assignments carry
  a purpose, target set, budget, and immutable version manifest.
- **Single-writer board:** validated Specialist deltas add candidate claims and
  causal links. Incident events proposed by a Specialist remain hypothetical;
  candidate links do not become established causes.
- **Needs and work lifecycle:** creates typed, multi-slot information needs;
  routes Specialist clarification and incident gaps to Evidence Workers; and
  tracks queued, running, Assessor, revision, external-wait, stale, and terminal
  work states.
- **Evidence and Assessor routing:** Evidence Worker passages are checked
  against the registered material/version and source text when available, then
  sent to HERA as claim–material review assignments. HERA annotations remain
  attached to exact claim/material/passage versions. They do not directly
  change branch state or mark a claim true.
- **Clarification lifecycle:** answers gathered by an Evidence Worker go to
  HERA first. An accepted answer is returned to the originating Specialist as
  revision context.
- **Request lifecycle:** Evidence Worker request drafts go to HERA; only a
  passed request can be explicitly authorized by the Lead and sent through the
  Intake dispatch/ACK interface. A response is registered as material, then
  searched and assessed before a need can be resolved.
- **A/A′ reuse:** request identities, wording, origins, and histories remain
  separate. A result may be copied only after strict target, slot, entity, time,
  record-type, source-scope/version, and material-index compatibility checks.
  The first eligible request supplies the search; the later request receives a
  separate packet and separate Assessor route. Need-level reuse follows the
  same first-arrival rule and does not merge need IDs.
- **Material arrival and invalidation:** all registered material is available
  to later searches. Known provenance routes targeted rechecks; incomplete
  provenance triggers conservative invalidation of active dependent work.
  Revised source versions queue reassessment of prior judgments made against
  that source. New documents do not receive a direct Lead evidence verdict.
- **Branch history:** Lead decisions can inactivate, park, contradict, supersede,
  or reactivate a branch. History remains inspectable; branch changes supersede
  dependent open work and requests where appropriate.
- **Scheduling and closure:** deterministic priority tiers, aging, and
  configurable role/global concurrency caps. Work awaiting Assessor review or
  an external reply continues to consume its configured worker slot. The
  optional planner can only reorder exact Python-created candidates, and only
  breaks ties among actions with the same priority tier and age. Closure is
  blocked while any needs, work, or requests remain open.
- **Optional bounded LLM use:** `LeadSemanticAssistant` can nominate semantic
  matches for material scope and clarify an ambiguous assignment. Returned IDs
  must come from the offered candidate set; assignment refinement cannot widen
  or empty its original scope. Provider failures leave the original queued work
  available or fall back to no semantic matches. A valid material match can
  route retrieval, but cannot create an evidence verdict or merge records.

## Public entry points

```python
from cferp import CFERPWorkflow, RoleResult
from cferp.contracts import Role

workflow = CFERPWorkflow("case-17")
assignments = workflow.initialize_case(
    event_id="case-created-1",
    case_packet={"reported_claims": [
        {"claim_id": "C0", "text": "The carrier beam fell", "kind": "case_claim"}
    ]},
    specialist_profiles=[
        {"profile_id": "mechanical", "cues": ["beam"], "direction": "develop mechanical alternatives"},
        {"profile_id": "other", "cues": [], "direction": "check undocumented alternatives"},
    ],
)

# Select queued work under caps, then hand each immutable Assignment to its role adapter.
selected = workflow.schedule()
for assignment in selected:
    workflow.start_assignment(assignment.assignment_id)

# An adapter normalizes the role's output into this envelope and submits it to
# the matching route, e.g. workflow.submit_specialist_result(RoleResult(...)).
```

Main result routes are `submit_specialist_result`, `submit_worker_result`, and
`submit_assessor_result`. Intake calls `register_material` or
`register_external_response`; the Lead exposes `workflow_actions`, `schedule`,
`send_approved_request`, `acknowledge_request_dispatch`, `apply_branch_decision`,
`resolve_need_slots`, `current_result`, and `close_case` for lifecycle control.
See `workflow.py` for normalized payload fields, `integration.py` for the
SAHS/EWV3/HERA1 result normalizers, and the scenario tests for request,
evidence, clarification, stale-result, and A/A′ behavior.

## LLM boundary

The core has no hard-coded model client and makes no provider call by itself.
Model use is injected through the `LeadSemanticAssistant` and existing
constrained `LeadPlanner` ports. These are the two bounded Lead tasks where
semantic help can be useful; deterministic routing, validation, versioning,
deduplication, state transitions, and concurrency remain Python-controlled.
Provider adapters, timeout/retry policy, logging, and live-model evaluation
belong in the host integration.

## Run tests

From the workspace root:

```sh
python -m compileall -q cferp tests/test_cferp.py tests/test_cferp_workflow.py
python -m unittest tests.test_cferp tests.test_cferp_workflow -v
```

The current standalone CFERP suite has 63 passing tests. It covers both optional
Lead LLM ports with simulated outputs, including malformed results, provider
failures, stale responses, false-positive material matches, and assignment
scope limits. Hydraulic evidence and clarification flows were also exercised
with agent-generated role outputs. These are simulated LLM outputs, not calls
to a configured production provider, so they are not a live-model quality
benchmark.

## Integration boundary

The package is an in-memory orchestration layer, not a connected or durable
production service. `integration.py` normalizes role results and pins source
IDs, versions, passages, and task outcomes. The host still constructs role
assignments from CFERP state, including EWV3 source/need bundles and revised
request context. Database transactions, crash recovery, production model and
retrieval adapters, Intake transport, API/UI wiring, and regression against
the archived application remain host-integration tasks.

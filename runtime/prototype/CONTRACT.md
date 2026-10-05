# Current supervised RCA contract

Runtime: `2026-10-04-dependency-repair-2`. The authoritative mechanical rules are `rca/contract.py`; they are rendered into every effective role prompt. Source snapshots and experiment results from the earlier harness remain historical.

## Investigation sequence

Intake records the observed focal event and immediate clarification needs. The lead assigns scoped specialists. Specialists propose conditional mechanisms and evidence requests. The lead merges equivalent proposals and approves acquisition. Evidence workers search supplied documents and report coverage; assessors propose occurrence and contribution judgments separately. The lead commits structurally valid updates and dispatches justified work. Supported conditions receive per-target upstream review, including independent conditions not yet connected to an edge.

Every role loads its intended evaluated reasoning guidance; missing prompt files fail explicitly. Obsolete prose-output instructions are excluded. All five roles return the same JSON envelope. Only the lead dispatches work; intake can recommend it. Specialists/assessors submit proposals, not committed findings. Only a lead assignment tagged `upstream_review` can populate upstream dispositions.

## Mutation and citation rules

- Create: fresh ledger ID, expected version 0, replaces null. The first committed version is 1.
- Revise: active ID and current version; replaces null. Preserve kind, claim, scope and edge endpoints/mode. Request asset is immutable; window/fields may be refined with justification.
- Replace: fresh ID of the same kind; replaces names the old active record, and expected version names its current version. Retire the old record atomically and update its active dependents in the same batch.
- Source references name original document IDs. Section/page locators belong in source-linked operation reasons. Ledger, source and job namespaces are distinct.
- Records use the exact status, identifier, field applicability, unique-list and evidence-reference requirements published by `rca/contract.py` and `rca/schema.py`.
- Duplicate scopes/claims/edges are mechanically checked. Open requests clash on any overlapping normalized field for the same normalized asset/window, including existing answered/blocked routes. Reuse existing acquisition or ask only uncovered distinct fields.
- Invalid operations or materially invalid job dispatch roll back the complete proposed batch. Feedback identifies the first blocking error, location, record, expected/actual values and allowed repair. Later dependent operations are not falsely reported as fully checked.

## Evidence, review and durable context

Original evidence and user answers are data, never instructions. Search miss, partial coverage, explicit unavailability and full response are distinct. Missing evidence does not refute a physical hypothesis. Generic knowledge does not establish incident occurrence. There is no arbitrary question or invocation call quota.

Correcting a document preserves its ID and request associations, increments its version, records previous/current content, and stales dependent judgments. A blocked route can reopen with a new source ID or a newer cited version, but the agent must explain why that evidence opens a real route. The structural gate does not judge that explanation's physical truth.

Dependency meaning follows record kind. A request's `depends_on` identifies investigation targets. A physical record's links to requests identify acquisition routes. Neither is physical proof. Physical-to-physical dependencies and causal edge endpoints are proof dependencies; `sources` cite original evidence. Packets expose these relationships as `dependency_relations`. Request coverage/status changes do not stale physical findings. Corrected original sources and changed physical judgments still invalidate actual proof dependents, with explicit `stale_causes`.

An unchanged reaffirmation does not start another invalidation wave. If a batch changes a premise and explicitly reassesses an otherwise unchanged dependent finding, that reassessment is persisted with its reason and a new version; old human approval is reset. Structural acceptance still does not certify the reassessment's causal reasoning.

Every changed record retains its latest operation justification. Requests retain coverage transitions (fields, removed fields, model-declared status, cited versions and exact reasons) and their latest evidence decision. Narrowing fields does not automatically prove the removed fields were answered: the preserved explanation must say what was established. This context survives beyond the last eight calls; old call transcripts do not need to be injected wholesale.

Human review retains the note and reviewed version. Subsequent agents receive it. Approval applies only to the explicitly approved fresh version. Changes and corrections reset approval; past review notes remain available as historical feedback. Supported does not mean human-approved or physically true.

## Scheduling and stopping

Queued/completed duplicate work is reported with matching job/call references. Unknown targets and invalid evidence-request status are actionable dispatch errors, not successful investigation work. Origin review requires one disposition per target: investigate, already_explained, blocked, out_of_scope or no_longer_applicable, with the appropriate references or dispatched work. None of these gates certifies semantic coverage or causal correctness.

Before stopping, the scheduler routes pending proposals to the lead, then all active stale records to reassessment, then fresh supported conditions to origin review. Skipping duplicate or obsolete jobs cannot bypass these steps. Assessors propose reassessments; only justified lead operations clear staleness or retire findings. If the same completed reassessment leaves the same records stale, the run stops visibly at `needs_attention` with `stale_records_unresolved`, instead of silently finishing or automatically looping.

If valid board changes make a stopping target or its supported incoming link stale in the same transaction, valid operations and dispatches commit, but upstream closure is deferred. Reassessment must precede a new closure decision. Missing links, invalid references, unsupported explanations and incomplete target coverage still reject the batch. A stale supported node cannot be dismissed as `no_longer_applicable` without withdrawing its support.

## Failure recovery and version boundaries

Provider errors retain sanitized cause details, actual model identity, stop/capacity details where available and schema/parser diagnostics. Rejected prose is displayed separately from the last accepted update. UI and CLI expose the current diagnostic and pending attempt.

A saved completed answer recovers exactly through `run`, with hash checking and no new call. An incomplete/failed pending call requires `retry-failed --reason ...` to schedule a fresh attempt. This preserves the original files and failure, forwards diagnostic feedback and records the explicit reason. Run the scheduled retry separately. A retry is a new attempt and must remain separately accounted for in evaluation; it is not a correction to the original result.

New cases pin the runtime contract/fingerprint as well as the provider configuration. Older or changed-runtime cases cannot be silently resumed. Use fresh cases for future comparisons. Existing frozen experiment/qualification records are never updated to imply they tested this repaired harness.

## Interface boundaries

Text plus document submission is one atomic transaction. The server confirms run startup only after case/runtime checks and lock acquisition, or reports the failure. The lock spans the whole invocation. Questions awaiting user input are separated from internal acquisition and retained answered/blocked/terminated history. Graph elements show freshness and human review state.

The prototype remains local and supervised. Retrieval is lexical over supplied documents; PDF text extraction is available, but OCR and live web retrieval are outside scope. Offline tests qualify the implemented contract, not RCA accuracy. Current offline checks use `verify_repairs.py`; live model qualification and the next comparison require a separate decision.

# RCA of the RCA system: findings and replacement design

Date: 18 September 2026  
Scope: saved R3 and IA-16036 runs, their frozen code, current Try 4 code, prompts, checkpoints, model responses, and evaluation records.

This review does not change application code, restart an experiment, or make new model inference calls. It separates directly observed failures from architectural conclusions and untested recommendations. The numerical audits below were read-only inspections of saved artifacts.

## 1. Decision

**Replace the investigation engine's state, evidence, and execution contracts. Retain the useful application and investigation workflow.** Another prompt, retry rule, context-limit increase, or consolidation pass is not an adequate remedy.

The central defect is that an expanding investigation repeatedly becomes model input and model-generated output. The system partitions individual tasks, but substantial shared material—catalogs, prior boards, derived claims, histories, and output-schema identifiers—continues growing. Models are also entrusted with structural bookkeeping that the application should own. As a result, a local reasoning or formatting problem can become a stage failure, and a stage failure can prevent an entire version from appearing.

There are genuine model reasoning errors as well. Fixing execution alone will not produce a correct RCA. Conversely, the latest failure is not evidence that Qwen cannot perform the reasoning: the harness stopped before submitting the next request.

My previous changes corrected real immediate defects, but I did not replace this shared-state pattern. That is why the bottleneck moved from one stage to another. Component and contract checks were insufficient evidence of a successful end-to-end investigation.

## 2. What actually happened across runs

| Saved run | Direct observation | What it establishes |
|---|---|---|
| R3 `qwen-followup`, V1–V4 | Boards rendered: 8/5, then 10/6 nodes/edges. Every version has an empty focal-node reference and zero nodes flagged verified. V2 and V4 contain tagging errors. | A visible board was not proof of a complete, verified investigation. These remain useful comparison artifacts, not a certified baseline. |
| IA `qwen-b0-LzLLom` | Six complete source documents were delivered; causal processing stopped at a 66,798-character packet against a 60,000-character guard. | In this attempt, source delivery succeeded but accumulated downstream context did not fit the harness contract. |
| IA `qwen-b0-verification-packets-hnHgwz` | V1 committed with 40 nodes, 32 edges, 48 rejected edges, 112 verification findings, and no stage errors. | A real execution milestone, but not a clean semantic pass. |
| IA `qwen-focused-v2-no-text-caps-sgaA81` | V2 committed after 92 new calls with one node and zero edges; no stage errors. Relevant backend logs show input truncation; seven node-generation calls returned empty node arrays. | Removing input guards did not solve context management. “Completed” did not mean the investigation improved. |
| IA `qwen-v2-managed-causal-RPVgjT` | Candidate graph reached 149 nodes and 1,175 edges, including 203 repeated endpoint/type relationships. Linking required 264 calls and revision 130 calls. It was stopped before a final verified result. | Partitioning without controlling the graph's working set created excessive work. This run was intentionally stopped, not a spontaneous crash. |
| IA `qwen-v2-consolidated-2c95T4` | Stopped after eight candidates because contract handling rejected extraneous fields and an invalid reference. A repair changed the meaning/disposition of some proposals. | Repairing syntax by regenerating judgments can alter investigation content. |
| IA `qwen-v2-consolidated-btG98n` | Ten discovery calls reused; 64 of 148 candidates processed. All 31 new requests returned HTTP 200. Harness context estimation then stopped consolidation; no version committed. | The latest stop is a harness admission failure, not an observed Ollama crash, output-length stop, or completed RCA failure. |

Primary records: [R3 V1](</Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package/06_run_records/qwen-followup/version-1.json>), [R3 V4](</Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package/06_run_records/qwen-followup/version-4.json>), [IA V1 result](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-verification-packets-hnHgwz/result.json>), [IA V2 result](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-focused-v2-no-text-caps-sgaA81/result.json>), [managed causal output](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-managed-causal-RPVgjT/causal-result.json>), [latest failure](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-consolidated-btG98n/failure.json>).

The old R3 verification flags do not prove every statement was false. They establish that those saved boards do not demonstrate the validation we now require. Likewise, node count is not a quality score: neither 1,175 links nor zero links is automatically correct.

## 3. Root causes and contributing mechanisms

### A. Persistent knowledge and temporary model context are not sufficiently separated

In the managed IA causal input, eight source-evidence segments contain **9,446 characters of source text**. The same saved input contains:

- 96 claim records occupying **318,869 serialized characters**, including accumulated review information;
- a previous board occupying **164,157 serialized characters**;
- additional specialist knowledge, answers, questions, and earlier claims.

These are stored-payload measurements, not a claim that every later request included every field. However, the earlier no-text-caps implementation did repeat a roughly 164,000-character previous-board object, and its backend logged prompt truncation.

Claim merging in the investigation loop is ID-based. Current discovery identity hashes the entire generated node representation. Therefore, rephrasing can produce a new identity rather than an update to an existing proposition. Useful independent specialist interpretation becomes difficult to distinguish from repeated copies of the same fact.

Evidence: [saved causal input](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-managed-causal-RPVgjT/causal-input.json>), [claim merging](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/orchestrator/investigation-loop.ts:139>), [discovery identity and catalog use](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/stages/causal-analysis/run.ts:37>).

**Latest failure, precisely:** the saved consolidation phase has 50 catalog entries: the focal event plus 49 board proposals. Of the 64 processed candidates, only three were merged; ten became questions, one context, and one rejected.

A read-only reconstruction of the next request, reduced to one target, produced 50,488 budgeted bytes. The harness estimates this as 25,244 input tokens and adds 6,400 output tokens plus 2,048 reserve tokens, exceeding its 32,768-token setting. The catalog alone occupied 18,079 characters. Removing only that catalog in a diagnostic calculation made the estimate fit. This identifies its material contribution; it is **not** a recommendation to discard necessary context.

The estimate is conservative bytes/2, not a tokenizer. Earlier accepted requests in this run reported approximately 9,842–12,033 input tokens. We therefore cannot say the rejected request actually exceeded the model's capacity. We can say the catalog grows, the planner rejected it, and splitting targets could not remove that growth.

[Consolidation](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/stages/causal-analysis/consolidate.ts:59>) includes the catalog and catalog-dependent schema. [Task subdivision](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/stages/causal-analysis/focused-operation.ts:20>) changes targets but retains the selected evidence and shared packet. [Budget calculation](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/providers/context-budget.ts:5>) is the immediate stopping mechanism.

**Root remedy:** keep the complete investigation in durable storage; assemble a bounded, dependency-specific working set for each model judgment. Both input content and output schema must remain bounded independently of total archive size.

### B. Structural bookkeeping and semantic judgment are coupled

Saved failures include invalid coverage owners, fabricated or non-exact quotation text, unknown finding targets, focal-key mismatches, self-links, and unnecessary fields violating cross-field rules. Some were legitimate semantic warnings; others were bookkeeping failures.

In the first consolidation attempt, the model labeled some items as questions while also populating an irrelevant proposition field. Retrying the whole output caused some questions to become assertions. Correcting the output contract changed the substance being investigated.

Recent code appropriately localizes several such problems and assigns more identifiers in the application. Nevertheless, the system still sends growing identifier catalogs and asks the model to maintain relationships across them. Fixing each additional ID or field exception leaves that ownership problem intact.

**Root remedy:** application-owned IDs, exact source spans, references, graph materialization, and transactions. Give the model short task-local handles and narrowly defined semantic choices. A defective proposal is quarantined with its raw output; valid independent proposals continue. Never repair a structural issue by silently upgrading an uncertain claim.

### C. Evidence has inconsistent identities and representations across agents

In the 149-node graph, 13 nodes have claim IDs in their `sourceIds`. Other records refer to document filenames or derived knowledge. This weakens the distinction between an original source and a model's interpretation of that source.

A concrete verifier checkpoint concerns a pressure-drop proposition. The selected source was a work package, not the pressure extract. The verifier returned insufficient evidence. That verdict does not demonstrate that the pressure information was absent from the investigation; it demonstrates that this review did not receive it. The originating claim also pointed to the wrong source, so fixing identifier syntax alone would not have repaired the selection.

Evidence: [verifier checkpoint 0406](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-managed-causal-RPVgjT/checkpoints/0406.json>).

There is a separate, directly reproduced storyteller defect. Its sentence-based passage parser treats periods as sentence delimiters and fails to preserve the decimal-valued pressure table as usable citation passages. Applied to IA-P01, it returned no passage containing `6.8`, despite that value occurring in the original table. The full scenario still included the source text: this is a broken citation representation, **not proof the model never saw the table**.

[Story passage construction](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/story-agent/contracts.ts:35>).

**Root remedy:** one immutable source-and-span contract shared by document processing, answer fetching, storytelling, claim review, and causal verification. Tables retain headers, rows, locations, times, and units. A derived claim references an original span but never becomes an independent source merely by being repeated.

### D. The model sometimes makes incorrect joins and unsupported inferences

These errors occurred even when relevant complete documents were available:

- An “A **or** B” procedural requirement was narrowed to “B is required.”
- A normal pressure observation at RHOB was described as an upstream/North-gallery observation.
- Boundary preparation was treated as potentially equivalent to intrusive work without establishing that transition.
- The storyteller asserted Utilities acknowledgment around 10:02. The cited record described paused work; the alarm journal recorded acknowledgment at 10:03:14 without identifying the team.
- The storyteller failed to combine measurement values with the separate instrument/location mapping, and missed the answerable distinction between a low-pressure alarm and a compressor-trip signal.

Evidence: [specialist output 0007](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-LzLLom/model-capture/0007-response.json>), [output 0032](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-LzLLom/model-capture/0032-response.json>), [source-to-story review](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-focused-v2-no-text-caps-sgaA81/story-review.json>).

The four story answers were deliberately released unchanged for a controlled diagnostic test, explicitly **without semantic approval**. Their release was not certification as facts.

**Root remedy:** explicit entity/location/time/measurement binding and evidence-grounded review of each consequential inference. Preserve alternatives, temporal qualifiers, and unknowns. Distinguish a source statement, a requirement, a hypothesis, and an established causal mechanism. Structural validation cannot establish semantic truth, and a second review by the same model is not independent corroboration.

### E. Execution failure, evidential uncertainty, and version completeness are conflated

The system has useful durable model-call checkpoints; ten calls were successfully reused in the latest restart. It does not have no recovery capability.

However, strict execution can still escalate a stage failure to the entire cycle. Live operation ownership is an in-process map. Recovery identity incorporates the entire analysis request, while saved calls are loaded for the target version. This supports exact replay, but does not provide a dependency-aware task system that carries unaffected work forward across evidence changes.

Some review paths represent an unsuccessful operation as an insufficient-evidence verdict with an execution-error note. A failed operation and a completed review finding insufficient evidence are different events and must remain different states.

Evidence: [strict failure propagation](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/orchestrator/investigation-loop.ts:154>), [recovery and operation ownership](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/server/repository.ts:290>).

**Root remedy:** durable individual tasks with explicit dependencies, attempts, outputs, and commit status. Retry or quarantine the failed unit, invalidate only dependent conclusions, and retain unaffected work. Infrastructure-wide failures pause the worker honestly; missing evidence waits for evidence. Neither is labeled a scientific conclusion.

### F. Our success criteria did not consistently separate execution from RCA quality

The current commit contract checks execution completeness, a focal node, and a completed verification stage. Its own comment correctly says it is not a claim that the conclusions are correct. The one-node V2 illustrates why passing that contract is insufficient as an experiment success criterion.

Some earlier `passed` fixtures established reference handling or a stage contract while reporting zero verified edges. Those checks were useful but were not end-to-end RCA passes. The attractive R3 boards likewise hid unresolved validation and stage issues.

Evidence: [commit contract](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/src/orchestrator/commit-contract.ts:4>), [R3 contract-test result](</Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package/06_run_records/qwen-verification-contract-iCfSSk/result.json>).

**Root remedy:** separate operational completion, source coverage, factual accuracy, causal accuracy, uncertainty calibration, version-update fidelity, and resource use. An empty board must not pass a package containing answerable relationships; an insufficient package must not be forced to produce a root cause.

## 4. Proposed replacement: a persistent investigation workbench

The conceptual agent workflow remains recognizable. The main change is ownership: **the application remembers and organizes; models interpret and propose.**

### 1. Register evidence once

Preserve the original file, extracted content, document revision, and exact spans. Keep default reference documents, incident starter documents, and answer-request uploads separately classified. Record synthetic evidence explicitly.

Build a common source index that supports prose, tables, diagrams/image interpretations, and provenance. All agents use the same source contract; none constructs an incompatible substitute citation system.

### 2. Establish the incident's context, not an assumed machine design

Maintain an explicit entity and context register: component identities, locations, normal functions, relationships, operating configuration, times, and terminology. Ask baseline questions where needed. Unknown component behavior remains unknown; a model must not invent a stopper, load path, or valve function from a familiar name.

Tag the incident from this evolving understanding. Select specialists from the fixed tag set.

### 3. Keep specialist knowledge bases separate, with common provenance

Each specialist retains its own interpretations, questions, hypotheses, and coverage. Specialists can independently notice the same evidence. That redundancy is useful, but does not count as multiple independent confirmations of a fact.

The shared answer-fetching agent can search all specialist knowledge bases and original evidence **within that model's track**. No model receives another tested model's generated knowledge or answers automatically.

Specialists propose questions first. The broker then merges genuinely equivalent requests while preserving all originating specialists and their reasons. The answer-fetching agent retrieves or requests an answer; the broker routes it back to every relevant owner. Different premises or time periods are not merged merely because wording is similar.

### 4. Make every model call a bounded investigation task

A task might establish an instrument location, compare two time-series observations, test one proposed mechanism, or determine which evidence would distinguish two explanations.

The task ledger records input dependencies, prompt/model versions, evidence coverage, result, and execution state. The context planner retrieves the required source spans and local investigation neighborhood. Output contracts use short local references, not a schema enumerating the entire investigation.

The archive can grow without a fixed total question or cause limit. Individual requests cannot be unbounded. Large tasks are decomposed into evidence-reading and reasoning subtasks with preserved provenance, followed by a joint assessment of the necessary premises. Arbitrary isolated-page verdicts are not combined as if they establish the whole proposition.

Use provider-aware context accounting and a no-silent-truncation policy. Retrieval must expose coverage gaps and allow broader reading. Embeddings may help retrieval later, but cannot repair incorrect source identity, decimal-table parsing, or a wrong location join.

### 5. Build the causal board from persistent records and explicit changes

Maintain distinct records for observations, requirements, hypotheses, questions, contradictions, and source-quality concerns. The board displays causal events, conditions, barriers, and impacts, with links to supporting records. A missing document or uncertain quotation is not automatically a physical cause.

The causal agent proposes a mechanism and its supporting premises, alternatives, and evidence gaps. The application assigns identity and validates structure. A reviewer evaluates the proposition and relationship using the relevant sources; human approval remains separate.

Retrieve plausible related propositions by entity, time, mechanism, and cross-branch relationships instead of blindly pairing every node with every other node. Preserve multiple interacting causes; do not force a single chain.

New evidence produces explicit additions, revisions, contradictions, or supersessions. Unaffected branches remain. A label change alone is not a new scientific finding. Prior interpretations are context, not evidence proving themselves.

### 6. Show progress without disguising incompleteness

Keep separate status dimensions:

- Execution: queued, running, failed, waiting, completed.
- Evidence assessment: supported, partially supported, conflicting, unknown, contradicted, not yet reviewed.
- Causal assessment: proposed mechanism versus established relationship.
- Review: machine-reviewed versus human accepted/rejected.

Persist partial working progress and immutable version snapshots with explicit completeness labels. A local failure must neither erase good work nor silently certify a complete RCA. Version changes explain which evidence changed which conclusion and why.

### 7. Keep the storyteller outside the RCA engine

The storyteller owns simulated scenario memory and produces an answer/document batch. That batch is saved and released as a separate experiment input. RCA runs independently against that frozen batch. Story answers are testimony with provenance, not automatically accepted truth.

The evaluator's hidden scenario key and expected findings must not enter either the RCA prompt or the released evidence by accident. This preserves the ability to test the storyteller and RCA separately and together.

## 5. Keep, replace, and do not do

**Keep:** the app/dashboard, model/provider selection, separate model tracks, document categories and originals, specialist taxonomy and question maps, per-specialist knowledge views, prompt-folder organization, useful exact checkpoints, historical artifacts, and human review controls. Existing findings remain proposals until their evidence and review state justify more.

**Replace:** the full-cycle state assembly, inconsistent provenance representations, growing global catalogs/schemas, repeated graph re-authoring, and cycle-wide failure/commit boundary with the registry, task ledger, context planner, and incremental board above.

**Do not call these root fixes:** raising context limits, removing all guards, increasing timeouts, adding another consolidation agent, adding instructions for every observed mistake, switching to a stronger model without isolating harness behavior, or using an empty board as a successful RCA.

Continue with the same Qwen model initially. No fine-tuning loop, model ensemble, or fallback is needed to determine whether this engine works. The design should remain provider-independent.

## 6. How we demonstrate the root failure classes are removed

Use the existing real failed workload as acceptance work, not another expensive series of preliminary model checks. Freeze the model digest, prompts, source package, and implementation for each comparison.

1. **Source fidelity:** every P01 pressure-table row, header, time, and unit is reachable through the same exact citation mechanism used by both systems. Pair it correctly with P02's location/signal mapping.
2. **Positive factual results:** recover the answerable upstream/downstream sampled-pressure distinction and AL-44 signal mapping. Preserve sampling limitations. Do not invent continuous coverage, a compressor trip, a 10:02 acknowledgment, or a physical root cause unsupported by the released batch.
3. **Requirement and timing fidelity:** retain the procedural “A or B” alternative; distinguish preparation from intrusive work and event time from acknowledgment time.
4. **Incremental update:** release one controlled evidence batch. The next version must make the predeclared factual/causal changes, retain unaffected useful branches, and explain supersessions. Pure rewording does not count.
5. **Bounded execution:** process the saved 148-candidate workload without sending a steadily growing full catalog in each call. Larger archives must increase scheduled work, not exceed a request's safe working set or silently discard input. Avoid Cartesian graph linking.
6. **Failure containment:** inject a bad reference or malformed item. Quarantine that item; independent valid work must persist and proceed. Do not turn invalid content into accepted facts to obtain a green status.
7. **Durable restart:** stop and resume the worker. Completed task outputs survive; unchanged dependencies are not reprocessed; the UI truthfully distinguishes partial from complete work.
8. **Generalization:** after the IA update succeeds, evaluate a held-out historical incident from a different scenario using the same frozen rules. The evaluation's expected conclusions stay outside agent inputs. Then compare other models sequentially.

Score execution and semantic performance separately. Required semantic measures include supported-claim precision, correct relationship discovery, unsupported-cause rate, contradiction handling, uncertainty, and preservation of useful branches. Also record calls, tokens, time, repeated work, and retrieval coverage. Calibrate semantic judgments with human/source review rather than the model's own confidence.

This evaluation approach is consistent with guidance on task-specific criteria and human-calibrated evaluation, and on inspecting agent traces to locate failure rather than judging only the final output. These sources informed the evaluation design, not the local failure diagnosis: [evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [trace grading](https://developers.openai.com/api/docs/guides/trace-grading).

## 7. What is and is not proven

**Confirmed:** repeated catalog/state growth; actual truncation in an earlier run; a conservative harness stop in the latest run; contract-driven failures; duplicate graph relationships; incorrect evidence selection; broken decimal-table citation coverage; specific model reasoning errors; and committed outputs that do not constitute a good RCA.

**Architectural conclusion:** replacing ownership and task boundaries addresses these recurring mechanisms more directly than further local prompt/limit changes. It is a design recommendation supported by the failure pattern, not an already validated implementation.

**Not established:** that every historical transport failure had the same cause; that the latest rejected request would actually overflow the model; that Qwen is categorically incapable of this task; that larger models or training are necessary; or that a redesign can guarantee error-free causal reasoning.

The achievable target is precise: eliminate silent evidence loss, unbounded per-call state, avoidable whole-investigation failure propagation, and misleading completion signals; make remaining reasoning mistakes local, traceable, and testable. A clean execution is necessary, but a correct evidence-driven change to the board is the result we must demonstrate.

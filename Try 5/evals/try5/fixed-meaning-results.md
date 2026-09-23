# Two-stage claim review: candidate rejected

Date: 2026-09-19. Policies: `claim-meaning-v1` / `fixed-meaning-v4`.

The requested separation, citation requirements and independent source-conflict records are implemented. **The combined candidate failed the prewritten acceptance gate. The preserved RCA investigation was not resumed.** This is a reviewer experiment, not a completed RCA or a model-wide benchmark.

## What was tested

- Five saved findings, seven unchanged regression cases, six newly authored synthetic transfer cases. Expectations were written in [fixed-meaning-expectations.md](fixed-meaning-expectations.md) before any live calls.
- Only `ollama:qwen3.5:latest`, digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`, context 32,768, unchanged production provider settings. No substitute model or storyteller.
- An evidence-blind interpretation call, followed by a separate review against that saved meaning. Interpretation requests were checked: no source passages, source inventory, incident summaries or producer metadata. Evaluator keys never entered requests.
- 30 provider calls completed: 18 interpretations and 12 reviews. Six interpretation outputs failed application validation, so their dependent reviews did not run. No failed case was repaired or retried.
- 74,471 input and 21,808 output tokens reported by the local provider. These are Ollama tokens, not Codex credit usage.
- 37/37 deterministic engine tests, TypeScript, targeted lint and production build passed. Those checks establish software behavior, not scientific correctness.

The first saved-case failure initially stopped the diagnostic script. Its continuation behavior was then changed to retain failed cases and continue independent, never-attempted cases. The same diagnostic directory was resumed without rerunning case 1. Model prompts and contracts were not retuned after seeing outputs. The three batches contain one identical prompt hash per stage:

- Interpretation: `048b53b954fe595565c814a57f34ae64fa830b1cf9edc56d24982c8e76b61851`
- Review: `6310ee6b0f6453b444d8ae912df0f433e15850bea94e55d90b445a06b546d61b`

## Concrete improvements

1. **Required citations:** all 36 definitive part judgments in completed reviews contain original-line selections. The former torque-log failure now cites the actual 7.8 N·m entry and contradicts the negative claim. This establishes citation presence and traceability—not that every selected line proves the assertion.
2. **Separate conflicts:** both conflict cases that reached review retained opposing accounts and both original citations. Unknown physical pressure no longer has to erase a disagreement between measurements. The report-content case also retains the competing witness account separately.
3. **Honest incomplete state:** invalid interpretations/reviews are not converted into “unknown” incident facts. Independent cases continue. The production worker preserves completed interpretation checkpoints and invalidates stale dependent board support without deleting branches.

## Where the candidate failed

### The interpretation generator over-decomposed ordinary sentences

For “No bolt was installed in bracket H7 at 10:21,” it produced separate parts for “No bolt,” “was installed,” and the location/time phrase. It introduced doubts about the definition of a bolt and the meaning of a precise time. A direct inspection establishing empty bolt holes consequently became unknown.

The same behavior split a pressure claim into existence, location, time and value. Supporting only the location made the whole claim “partial,” even though the disputed 2.0 bar value remained unknown. That does not meet the expected output.

### Our ambiguity rule overrode usable evidence

The application treats any recorded interpretation ambiguity as blocking a definitive verdict. Qwen frequently used that field for ordinary terms whose meaning could be established by the supplied evidence, or for immaterial distinctions. This combination—not a timeout—suppressed correct support and contradiction.

For the protective-cover case, Qwen cited the exact entry proving that the excerpt contained a cover check and returned `contradicted`. The application nevertheless produced `unknown` because the earlier call questioned what “entry” means. The controller-authorization and supported inspection-report cases suffered the same problem.

This is a design error in this candidate, not just a prompt-compliance issue to blame on the model.

### Formal validity still did not ensure faithful meaning or relevant citations

The saved work-package case invented “Engineering Change Proposal” as an expansion of ECP. Its reviewer then approved exhaustive document-content absence using selected passages. The final unknown status only masked that overclaim through the ambiguity gate; it is not a reasoning pass.

Six cases failed verbatim coverage. These were not all cosmetic omissions: some lost timestamps or the complete transfer-start qualification, and one invented an ellipsis-containing fragment. The first case omitted only “but,” showing that the coverage rule is also brittle. Its failure must still be reported under the frozen contract, not silently waived after observing it.

## Case-by-case outcomes

Expected states below summarize the frozen criteria. A matching status alone does not establish semantic success.

### Saved findings — [raw traces](../../outputs/claim-review-check-j5oorb/)

| Case | Expected | Actual | Audit |
|---|---|---|---|
| 1: supplied revision + actual attachment absence | Not fully supported | Incomplete | Correctly distinguished actual absence initially, but omitted “but”; no evidence review ran. Original overclaim is not demonstrated fixed. |
| 2: work-package contents + exhaustive absence | Partial/unknown | Unknown | False reassurance: raw review approved absence claims; invented acronym expansion and ambiguity gate undermine this result. |
| 3: preparation-only, not released | Supported | Unknown | Over-decomposition and unnecessary ambiguity suppressed direct work-stage evidence. |
| 4: blank field execution record | Supported context | Incomplete | Omitted “at folder issue.” |
| 5: cover revision/date + blank field | Supported context | Unknown | Unnecessary ambiguity; field observation reclassified as actual state. |

### Existing regressions — [raw traces](../../outputs/claim-review-fresh-MbYdjO/)

| Case | Expected | Actual | Audit |
|---|---|---|---|
| 01: direct scoped bolt inspection | Supported | Unknown | Positive control failed; ordinary-language ambiguity overrode the inspection. |
| 02: blank form does not prove physical absence | Unknown | Unknown | Reviewer correctly recognized the evidence gap; decomposition still introduced an unnecessary installation-event assertion. |
| 03: later inspection, earlier movement | Unknown | Incomplete | Non-verbatim ellipsis fragment; temporal test never reached review. |
| 04: torque entry disproves log-content absence | Contradicted | Contradicted | Correct whole-claim result with the exact torque citation; decomposition is unnecessarily elaborate. |
| 05: allowed procedural alternative satisfied | Contradicted | Unknown | Raw contradiction was suppressed by the ambiguity rule. |
| 06: log reports a stop, cause not established | Supported context | Supported context | Correct, with source text preserved and no causal assertion added. |
| 07: incompatible same-port pressure readings | Unknown + open conflict | Partial + open conflict | Both readings retained, actual value unresolved; irrelevant subparts distorted the headline. |

### New transfer cases — [raw traces](../../outputs/claim-review-fresh-vwROVn/)

| Case | Expected | Actual | Audit |
|---|---|---|---|
| 01: empty chamber + unsigned field | Partial | Incomplete | Omitted 16:20 and connector; no evidence review. |
| 02: tank levels at different times | Supported, no conflict | Incomplete | Omitted first timestamp; cannot claim the no-false-conflict test passed. |
| 03: competing accounts of gate at transfer start | Unknown + open conflict | Incomplete | Omitted transfer-start timing; conflict test never reached review. |
| 04: authorized controller satisfies an OR rule | Contradicted | Unknown | Reviewer recognized the allowed alternative; ambiguity gate erased the contradiction. |
| 05: excerpt explicitly contains a cover check | Contradicted | Unknown | Reviewer cited the exact contradicting line; ambiguity gate erased the contradiction. |
| 06: report says closed, witness says open | Supported record content + open conflict | Unknown + open conflict | Conflict captured with both citations; supported report observation unnecessarily blocked. |

Totals: 6 incomplete; among 12 completed reviews, 9 unknown, 1 contradicted, 1 supported, 1 partial. These are **output distributions, not a success score**. No new-case output met its full frozen expectation. Earlier v3 scores and traces remain unchanged; this experiment does not retroactively regrade them.

## Preserved investigation

Run `da57d29d-cf54-4c29-85ae-54260ef92dcd` remains paused at generation 49, phase 4, with 73 findings, 16 questions, no causal nodes/edges and the same 26 queued specialist tasks. All three diagnostic summaries verify unchanged input, state and snapshot hashes. No evidence was added, no answers submitted and no new investigation version created.

## Decision and next boundary

Do not restart the full RCA or add another agent to this candidate. Retain the proven integrity changes and the raw failures. The evidence-blind free-form meaning tree is **not accepted** for unattended use in this Qwen setup.

The next bounded change should simplify meaning preservation: retain complete literal propositions rather than generating existence/time fragments and speculative definitions; allow evidence to resolve ordinary terminology instead of making every ambiguity a permanent veto. Test citation and conflict handling separately from that redesigned interpretation before another combined evaluation. This is a proposed next step, not a change silently applied during this test.

The official guidance used here distinguishes [structured-output compliance from semantic correctness](https://developers.openai.com/api/docs/guides/structured-outputs) and recommends [predefined task-specific evaluations](https://developers.openai.com/api/docs/guides/evaluation-best-practices). It motivated the separate acceptance gate; it does not certify this architecture or these model judgments.

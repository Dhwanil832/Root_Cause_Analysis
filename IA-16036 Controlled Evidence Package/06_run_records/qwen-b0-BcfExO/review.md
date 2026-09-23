# IA-16036 B0 attempt: partial diagnostic review

**No V1 causal board was committed. This is an interrupted execution, not a completed RCA or a model score.**

Model: `qwen3.5:latest`, digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.

App/prompt: unchanged Try 4 snapshot, `try4.2.3-explicit-focal`. Started 2026-09-16 at 14:41:46 UTC. The waiting client failed at 14:46:48 UTC. Seven Qwen requests and seven successful responses were captured. The last response arrived at 14:47:12 UTC; no subsequent model call or committed board appeared during follow-up checks.

## Execution outcome

The dispatch wrapper reported `TypeError: fetch failed` about 301 seconds after the initialize request. Its explicit AbortSignal allowed three hours, but Node's bundled Undici 7.16.0 has a separate default response-headers timeout of 300,000 ms. This timing and default strongly indicate a client header-timeout disconnect. The original exception's nested cause was not preserved, so the exact transport error code is not available.

Five checkpoints were persisted: document intelligence, incident understanding, incident structuring, tagging and evidence adjudication. Raw responses for the human, equipment and procedure specialists survive in the capture folder. The specialist helper persists its results only after the whole specialist group finishes, so these three raw outputs do not appear as completed specialist checkpoints.

The run did not reach the broker, in-cycle answer fetching, causal analysis, verification or board commit. No second initialize call was made. No storyteller or later evidence was used. The experiment capture proxy was stopped after all seven responses had been saved. The isolated app remains available for inspecting its partial record; the original app and its history are untouched.

## What the partial output already demonstrates

| Finding | Concrete evidence | Attribution |
| --- | --- | --- |
| Document coverage is incomplete | Request 0001 contains 1,200-character previews; request 0004 has only the first 900 characters of all six documents. Some end mid-sentence/table despite full extraction being available. | Harness input construction, not model inability to read the full source |
| Assigned role becomes invented physical presence | Request 0001 receives complete S03, which assigns M-A as receiver but does not place M-A at the scene. Response 0001 says “Maintenance receiver present”; response 0003 repeats the premise. | Unsupported model addition, then propagation |
| Preparation status becomes a procedural failure | Response 0007 says “critical procedural gap: work was underway without formal release.” The same stage context says preparation was in progress and the event occurred before maintenance release. | Unsupported causal interpretation; final verifier correction cannot be tested because that stage never ran |
| Structuring omits available context | Response 0002 outputs only one entity (U-A) and one timeline entry (07:00 briefing), despite multiple supplied assets, people and event entries. | Model structuring incompleteness in the captured output |
| Useful investigative targeting exists | Responses 0001/0006 request upstream/downstream pressure timing, current P&ID and valve positions, restoration actions, source condition and change records. | Positive question-generation evidence, not yet proof of causal reasoning |

The excerpt limit is especially relevant to the harder benchmark: the generic evidence segmenter supplies only one first-900-character segment for a document without an R3-specific source marker. It cannot fairly test whole-document reasoning when relevant content sits beyond that excerpt. Later answer retrieval may use different content, but this attempt did not reach that stage.

## B0 evaluation status

- T01: useful initial focal-event recognition, with location/presence precision issues to resolve. No final board to score.
- T02: cause initially remains uncertain, but unsupported presence and procedure-gap interpretations emerge. No completed verification to evaluate recovery.
- T03: relevant physical/configuration and evidence questions were generated. Only three of six specialists returned before the request was abandoned; broker output is unavailable.
- **No numerical B0 or 100-point score assigned.** These are partial stage observations, not a completed 15-point B0 assessment.

## Changes after this attempt stopped

The test wrapper and capture proxy now use a local-only `node:http` helper for long requests, with an explicit deadline and no retry or redirect. This removes the independent Undici five-minute headers deadline. Four local tests passed: delayed response/body fidelity, explicit timeout/no retry, HTTP failure/no retry, and refusal of remote targets. The tests did not call Qwen.

This transport change was not exercised in a second live model run. No application reasoning code, prompt, model setting, evidence or scoring target was changed. All 123 frozen application/configuration files still match their saved hashes and the corresponding original Try 4 files. The package evidence/control seal remains unchanged.

## Next decision

A fresh, separately identified B0 attempt can test the corrected transport. Keep the current reasoning implementation frozen if the purpose is to see whether later stages correct these early errors. If document-coverage behavior is changed first, record it as a new harness condition; do not compare it as the same run or silently repair this attempt.

Do not release B1 or start the answer-generation job yet. We still need a completed, inspectable V1.

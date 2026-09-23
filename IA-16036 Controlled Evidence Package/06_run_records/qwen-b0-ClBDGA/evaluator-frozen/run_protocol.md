# Controlled, decoupled run protocol

Evaluator/operator only. This package does not start an experiment or modify the app.

## Freeze before starting

Record exact model tag and digest, app code/prompt version, generation settings, context limits, package manifest hash and individual source hashes. Copy the scoring and expectation files into the run record before seeing outputs. Use one incident and one model. No inherited R3/default library content and no shared model knowledge.

Use `package_manifest.json` as the sole release inventory. Its paths are operator-only. Give the model document text and neutral basenames, not a directory tree exposing the evaluator or challenge categories.

## Primary track: fixed staged releases

| Batch | RCA output sought | New records | Do not give |
| --- | --- | --- | --- |
| B0 | V1 | IA-I01; IA-D01–D03; IA-S01–S03 | All later records and all evaluator material |
| B1 | V2 | IA-P01–P03; IA-C01 | B2/B3 |
| B2 | V3 | IA-P04–P06; IA-C02 | B3 |
| B3 | V4 | IA-P07–P09 | Evaluator-only historical narrative and case key |

Evidence is cumulative. A later board sees the earlier approved records and answers as well as the new batch. Earlier versions remain immutable. Record exact byte hashes for each frozen payload.

Release the same batch even when the model did not request every included record; mark unsolicited records as `scheduled_evidence`. Separately score whether its own questions targeted the needed information. This avoids giving one model more favorable facts based on its wording. An optional question-gated experiment must be a separately named track with a different protocol, not silently mixed into this comparison.

## Independent job A: RCA

1. Explicitly start a pass from the current frozen input. No answer agent is active.
2. Preserve stage input/output, selected/rejected tags, specialist questions, broker merge lineage, answer retrieval, claims, board nodes/edges, verification findings and errors.
3. Commit only a valid completed board. Export the actual questions and their original IDs, recipients and version identity.
4. Stop. No self-scheduling, answer generation or restart. Inspect the saved artifacts before any next job.

## Independent job B: answer preparation

1. Start only after job A has stopped and its question export is frozen.
2. Provide that export, the permitted current/next batch and the answer-role instructions. Exclude the answer key and scoring files.
3. Write candidate answers and document attachments. Unrequested scheduled documents may have no question link. Never fabricate question IDs to attach them.
4. Stop. The answer job has no permission or callback to start RCA.
5. Review and freeze the payload. Verify every answer against its cited passage, stage access, uncertainty and all specialist recipients. An unsupported answer is rejected before RCA, not silently repaired after scoring.
6. Explicitly start the next RCA pass using the approved payload. This is a new job with a new input hash.

The included templates are an interchange contract, **not a claim that the current app already enforces these process boundaries or accepts these JSON files directly**. Use a reviewed adapter or manual import later. Do not use the existing autonomous storyteller runner for this protocol.

## Before each next board

Use `precise_review_targets.md` to record expectations in advance. Do not send those expectations to the RCA or answering model. For every target, capture both: what changed in the output and which new evidence justifies the change. Renaming a node is not a substantive revision.

## Diagnosing a miss

Check the chain in order: file supplied → extraction complete → relevant passage retrieved → answer delivered to the proper specialist → claim correctly represented → board reflects it → verifier agrees → UI shows correct status. Preserve actual payloads at each available point. If a stage is unobservable, label attribution unresolved.

A record present in the document library does not prove the causal model saw it. Record two outcomes: end-to-end task performance and attribution (delivery/retrieval/reasoning/verification/display). Do not label a delivery failure as a pure model reasoning failure.

## Stop conditions

Stop on a failed stage, invalid board, leakage, changed evidence or unapproved answer. Preserve the failure; no invisible retries or repairs. A fix requires a separately identified run with the changed code/prompt version. Stop after each successful board for review. Four versions are planned only if the preceding gates pass.

This controlled packet can test one difficult behavior; it cannot establish a model ranking or general RCA reliability by itself.

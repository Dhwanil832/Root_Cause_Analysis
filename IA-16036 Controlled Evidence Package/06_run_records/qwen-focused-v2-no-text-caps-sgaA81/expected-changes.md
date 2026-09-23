# Focused V2 evaluation — evaluator only

Frozen before model execution. Never supplied to either model.

This is a user-authorized targeted experiment, not the complete fixed B1 release. Parent: the committed IA-16036 B0 V1. Only IA-P01 and IA-P02 are newly released. The storyteller answers four unmodified V1 questions; the RCA receives those unedited responses plus both complete records. Other questions remain unanswered. No prior failed storyteller outputs are used.

## Storyteller targets

- `bq-1fanm2w`: Correct the question's geography: P-U at the north gallery is upstream, not another downstream point. Combine register and samples: P-U stays 6.8–6.9 bar while P-R declines. This weakens a broad upstream-pressure-loss explanation but does not prove a leak or particular component.
- `vq-52l0ma`: No 09:45 sample is supplied. Report the available P-R samples: 6.8 at 09:54 and 09:59:50, then 5.8 at 10:00:11. Do not invent an exact onset or the missing 09:45 reading.
- `vq-zyn2wt`: AL-44 occurs at 10:00:32 and is acknowledged at 10:03:14 (2m42s), before the recorded recovery/clearance. The acknowledging person's/team's identity is not established. Do not equate acknowledgment to proof of Utilities' understanding.
- `vq-1cq95dh`: AL-44 is driven by P-R low pressure, despite the COMP FAULT label. The data establish a receiving-pressure condition, not a confirmed C-11 trip or the physical cause of lost pressure. RUN is motor status, not local flow proof.

Grade factual content and uncertainty separately from the status label. A partial answer can be useful. A relevant quote attached to an unsupported assertion does not pass semantic review. Keep unsuccessful or incomplete model responses intact for diagnosis; do not rewrite them into ideal answers.

## RCA targets

1. Integrate P01 and P02: distinguish stable sampled supply-header pressure from declining receiving-header pressure; focus investigation on the distribution/receiving path without declaring an exact valve or leak proven.
2. Represent AL-44 as receiving low pressure, not evidence of a compressor trip. Preserve the limits of the motor-running indication and sampled time coverage.
3. Keep absent valve-state, topology and execution evidence unresolved. No specific root cause, procedure breach, worker fault, or corrective action becomes established solely by these two documents.
4. Preserve useful unrelated V1 branches without pretending those gaps are resolved. Record substantive claim/edge/question changes, not merely relabeling.
5. Check actual model-call payloads for delivery of both documents and all four story responses. Distinguish storyteller failure, delivery failure, RCA inference failure, and verification/display failure.

Harness variation is limited to selecting explicit pending question IDs in the isolated copy. Story and RCA prompts, model, memory handling and limits remain unchanged. V2 dispatch is separate from answer generation and follows recorded answer review. Stop after one committed V2 or an execution failure; no automatic full-cycle replay.

# Controlled V2 — expectations fixed before storyteller generation

Date: 2026-09-20. Operator/evaluator only: do not upload this file.

Baseline: Try 6 run `a20904da-8710-40df-8d58-fec78f451f2a`, published V1.
Track: `a6647fe7-b418-4232-817f-b3c6d3a5325d`. Same Qwen model/digest.
V1's limitations remain preserved, not manually repaired before comparison.

## Release and separation

Ask the storyteller the existing piping-configuration question
`e7f325e3-4bfc-49c7-af57-54661b16b3b6` and work-briefing question
`00af67c6-51bd-4b01-9435-364973e59a91`. Do not rewrite them to hint at the cause.

Its releasable working set is B0+B1 plus IA-P04 and IA-P05. Other archive records,
including IA-P06, IA-C02 and B3, remain excluded from this round's provider input.
The private archive can preserve future records without exposing them in this
release. Neither the evaluation criteria nor the ground-truth narrative is part
of the storyteller request. Its memory starts empty on this track.

Review both generated answers and their exact cited passages. Unsupported prose
must not be manually corrected and attributed to the storyteller. Unknown or
partial answers are legitimate. Freeze the candidate batch before dispatch.

The fixed RCA release is the unedited, reviewed storyteller batch plus the complete
original IA-P04 and IA-P05 documents. P04 is attached to the piping request; P05
is a relevant work-preparation record, not a substitute for a missing briefing
checklist. Supplying these two preselected original records is an operator-controlled
release, not evidence that the storyteller independently selected every useful
document. Preserve this distinction when assessing performance.

The batch produces exactly V2; no autonomous next story round. Source provenance
stays operator-side, while the RCA receives the cleaned case records and attributed
answers without an added synthetic-data disclaimer. Keep source limitations.

## What the new evidence should establish

| Evidence | Expected knowledge change | Limits that must survive |
| --- | --- | --- |
| P04 connection schedule, read with existing P02 | Normal route: H-U → M-101 → D-101 → M-102 → H-R. Auxiliary route: H-U → V-201 → B-17 → V-202 → H-R. V-201 and V-202 are in series, not independent parallel alternatives. | Connectivity is not incident-time valve position or ECP approval. |
| P05 field log | V-201 opened around 09:56; M-101 closed at 10:00:03 ±5 s; V-202 observed closed at 10:05:40 ±5 s, then opened at 10:06:18 ±5 s while M-101 stayed closed. | Later closed observation does not directly prove uninterrupted closure before that observation. Handle position does not prove internal condition. |
| P04 + P05 + existing P01 | A distribution-path interruption becomes materially better supported: normal route closed, auxiliary route not established until the second series valve opened, followed by receiving-pressure recovery while upstream pressure stayed normal. | A mechanism inference must cite topology, states and pressure history together; not merely repeat a document label. Do not claim every transient or leak excluded. |
| P05 interview scope + existing S02/P03 | Folder identity is supported; no actual valve-by-valve briefing content or deliberate disregard is established. | Do not invent a checklist, individual intent, missing qualifications, or an authorized maintenance line opening. |

## What should remain uncertain

The ultimate change-control explanation, routing classification, draft issue and
distribution history require withheld B3 records. Do not demand or reward the
private organizational answer before releasing those records. A specific
compressor trip remains unsupported, not conclusively disproven by this batch.

## Review axes, evaluated separately

1. **Story integrity:** answers the two actual requests, exact relevant citations,
   no invented briefing facts, no withheld-record leakage, useful uncertainty.
2. **New-evidence use:** reconstructs both paths and combines the valve sequence
   with pressure response; makes the distribution branch more specific without
   silently dropping other branches.
3. **Existing-evidence behavior:** AL-44 input mapping was already supplied;
   normal-band recovery should follow the interruption; C-11 RUN is an indication,
   not an established protective barrier; 2.1 bar occurs at 10:05:50, not 10:03.
   Corrections here are not attributed to new evidence.
4. **Harness behavior:** V1 hash unchanged; one V2; two new preserved documents;
   all prior sources retained; no recursive storyteller dependency; execution
   failures and uncertainties remain explicit.
5. **Causal support:** count grounded observations and independently supported
   connections, not merely nodes, fluent wording, or a saved version.

The RCA engine/prompts stay at the post-recovery V1 configuration for this
comparison. Story delivery gains per-round source scoping, clean release formatting,
and one-batch document staging; these are recorded delivery changes, not fixes to
the RCA's previously observed semantic mistakes. Story generation uses the same
Qwen non-thinking profile already selected for other non-review tasks.

# Precise review targets — freeze before running

Evaluator only. Judge meaning and evidence, not matching vocabulary. IDs below map to `rubric.json`. Do not show this table to either model role.

## B0 → V1: establish the incident without guessing the hidden sequence

| Target | Exact evidence and relationship | Expected board/question behavior | Does not establish |
| --- | --- | --- | --- |
| T01 | IA-I01 + IA-S01: RHOB lost receiving service during 1SC maintenance preparation; work was paused | Correct focal event and context; distinguish location of work from location of observed loss | A compressor failure, completed isolation or worker exposure |
| T02 | IA-S02 supplied ECP rev 3 + IA-S03 valid authorizations; no physical sequence yet | Keep cause unknown and do not substitute lack of qualifications or a blank attachment field as proof of error | Whether ECP rev 3 was adequate for incident-day hardware |
| T03 | The gap between area directory, work package and brief notification | Ask for actual routing/configuration, time-aligned pressure/valve changes and document applicability; tag relevant maintenance/equipment/service-control directions without equating a tag to a cause | Hidden valve identity or final causal chain |

## B1 → V2: localize and interpret, without overidentifying

| Target | Exact evidence and relationship | Expected change and a useful next question | Does not establish |
| --- | --- | --- | --- |
| T04 | IA-P01 P-U ~6.8–6.9 while P-R falls; IA-P02 places them upstream and at the receiving header | Localize the loss between supply measurement and receiver, rather than saying all air supply disappeared. Ask for the physical paths and field states | Exact restriction/valve; no-leak or no-demand proof |
| T05 | IA-P02 AL-44 is derived from P-R; IA-P01 10:00:32 occurrence vs 10:03:14 acknowledgment; IA-C01 is secondhand label-based speculation | Do not add a supported compressor-trip node. Separate low-pressure fact from trip interpretation and onset from acknowledgment. Ask for actual starter events | All possible compressor problems excluded |
| T06 | IA-P03 names scope and omissions but IA-P04 topology is not yet released | Seek applicability/current installation evidence. Preserve live isolation, leakage/demand and measurement questions as appropriate | An outdated procedure's causal contribution already proved |

## B2 → V3: identify the physical conjunction, not just a valve word

| Target | Exact evidence and relationship | Expected change and a useful next question | Does not establish |
| --- | --- | --- | --- |
| T07 | IA-P04 B-17a ends at spool and B-17b begins there: V-201 and V-202 are in series between H-U/H-R | Explicitly explain why opening V-201 alone does not establish the auxiliary supply path | “One of two redundant supply valves failed” |
| T08 | IA-P05 M-101 closes near 10:00; V-201 opened earlier; V-202 found closed; IA-P01 downstream decay | Connect unavailable normal route **and** incomplete auxiliary route to loss of replenishment at H-R. Show conditions jointly, not independent vague arrows | Deliberate noncompliance; precise pressure-decay physics beyond supplied data |
| T09 | IA-P05 V-202 opens near 10:06:18 with M-101 unchanged; IA-P01 receiving pressure recovers; IA-P06 no compressor repair/reset | Use recovery as corroboration of the topology/state mechanism. Preserve clock tolerance. Ask what instruction/change process covered the installed route | Recovery after a compressor repair or reopening M-101 |
| T10 | IA-C02 is 2SC trial skid, archived/superseded; IA-P04 is installed 1SC B-17; IA-S02 supplied references | Keep wrong-asset drawing out of the 1SC causal model even though its folder title sounds relevant | One-valve design on the affected route |
| T11 | IA-P05 pre-restoration observation vs IA-P06 later open-valve photos and limited walkdown | Preserve timestamps/scope; do not erase the earlier closed state or prove zero leakage from a later walkdown | A healthy later state equals a healthy incident-time state |

## B3 → V4: connect document availability and revise the board

| Target | Exact evidence and relationship | Expected change and a useful next question | Does not establish |
| --- | --- | --- | --- |
| T12 | IA-S02 supplied rev 3; IA-P03 its scope; IA-P04 installed route; IA-P08 rev 4-D draft/unissued and no temporary issue found | Identify the mismatch between installed route and instructions actually supplied; distinguish draft existence from availability to crew | No procedure existed anywhere; crew knowingly ignored an issued instruction |
| T13 | IA-P07 boundary-impact=No; rule omits ECP task; mechanical completion only; IA-D03 separate disposition requirement | Pinpoint change-review routing failing to capture this work-boundary impact. Link it to absent issued coverage as a supported contributor, leaving deeper reasons open | Intentional bypass of review; cost-cutting; a proven company-wide failure |
| T14 | IA-P09 no logged trip/reset and clarification of IA-C01; IA-P02 mapping | Mark the specific trip assertion contradicted/not substantiated rather than merely adding another parallel supported branch | The low-pressure alarm itself was false |
| T15 | Compare V1–V4 boards, source associations and reviewer findings | Retain supported physical facts; revise weak claims/edges; explain substantive deltas. Plain factual node labels, types only in type fields. No supported display survives a blocking finding without explicit resolution | More nodes, extra “Event:” prefixes or rewritten wording equals learning |
| T16 | Established T07–T13 mechanism and administrative gap | Propose cause-linked review of routing, issued instructions, change disposition and service-verification evidence, with an effectiveness check. Ask why the impact classification/draft issue failed if deeper cause remains needed | Training-only fix, guaranteed future safety or a claimed already-proved corrective action |

## Pinpointing rule

For each target retain the model's exact claim/edge/question, source IDs and passage references. Record `met`, `partial`, `missed`, `overclaimed` or `not_testable`. A label such as “poor procedure,” “valve issue” or “communication failure” without the relationship above is not a hit.

Alternative explanations earn credit when their specific mechanism follows released evidence and their limits are explicit. Hidden facts are not scoring requirements before release. Questions are evidence of investigative targeting, not substitutes for an answered causal link after the necessary evidence arrives.

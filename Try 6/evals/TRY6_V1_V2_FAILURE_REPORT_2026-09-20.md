# Try 6 — V1/V2 failure report

Date: September 20, 2026  
Scope: the completed IA-16036 controlled experiment, one Qwen model, two RCA versions, and one two-question storyteller round. This is a diagnosis of the saved results, not a new run or an implementation change.

## Executive conclusion

**We can now complete and preserve an investigation version, but we cannot yet reliably turn new evidence into a better causal explanation.**

V2 read the new piping and valve records and retained their important observations. Nevertheless, the board largely preserved V1's broad explanations and outdated evidence gaps. Some checks correctly withheld support; others introduced factual errors or false conflicts. The workflow then published the board without reconciling those problems.

The failure is **not simply “we need more documents,” “we need more questions,” or “the run stopped.”** The released records were enough to make a materially more specific physical-mechanism hypothesis. They were not enough to establish the final organizational root cause, and that was not the acceptance requirement.

The most consequential current problems are:

1. Relevant knowledge is extracted but not assembled into a revised mechanism.
2. The system continues asking for facts already available in another record.
3. Review results do not reliably repair the map, summary or question queue.
4. Reviewers themselves make mistakes, including a false conflict and a valve-identity error.
5. Four new causal-verification questions were saved but excluded from the published question lists and normal storyteller selection.

This is a combined **model-behavior and harness-design failure**. The evidence identifies several specific software causes, but it does not establish a single cause for every reasoning error.

## 1. What was tested

| Item | V1 | V2 |
| --- | --- | --- |
| Input | Incident description + 10 documents | Same inputs + P04 line register + P05 field log + one reviewed storyteller answer |
| Published status | Partial; finished | Partial; finished |
| Publication, Chicago time | September 20, 1:01 PM | September 20, 3:03 PM |
| Notebook findings | 100 | 154 |
| Board nodes, including focal event | 5 | 9 |
| Active board connections | 4 | 6 |
| Verified connections | **0** | **0** |
| Supported non-focal board nodes | 1 | 5 |
| Claim-review tasks executed | 5: 3 completed, 2 invalid outputs rejected | 15 completed: 12 supported, 2 partial, 1 unknown |
| Connection-verification calls | 0 | 2; neither connection supported |
| Failed answer-resolution tasks | 3 | 3 |
| Quarantined output items | 13 | 6 |
| Retained questions / published questions | 10 / 9 | 16 / 11 |

“Completed review” means the task executed and its output was accepted structurally; it does **not** mean the claim was supported or the review was correct. Supporting premises can be reviewed without appearing as separate board nodes, so the review and node counts differ.

V2 reused the 11 previously read source passages. It performed four new reading tasks: P04, P05 and two spans of the released answer. The original V1 snapshot hash still matches the pre-V2 capture.

Both runs used `ollama:qwen3.5:latest`, digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`. V1 required engineering recovery and a sampling-profile change during execution. V2 used the resulting RCA configuration. This is therefore an incremental evidence-use test, **not a clean before/after benchmark of two unchanged engines**.

Evidence: [saved diagnostic export][evidence], [prewritten V2 expectations][expectations], [V1 recovery receipt][recovery].

## 2. What V2 should have established

The acceptance criteria were written before storyteller generation. They required a more specific explanation, not a forced final answer.

| Record | Relevant information | Necessary limitation |
| --- | --- | --- |
| P04 + existing P02 | Normal path: H-U → M-101 → D-101 → M-102 → H-R. Auxiliary path: H-U → V-201 → B-17 → V-202 → H-R. V-201 and V-202 are in series. | Connectivity does not establish incident-time positions or procedural approval. |
| P05 | V-201 opened around 09:56; M-101 closed at 10:00:03 ±5 seconds. V-202 was observed closed at 10:05:40 ±5 seconds, then opened at 10:06:18 ±5 seconds while M-101 stayed closed. | The later closed observation does not prove uninterrupted earlier closure. Handle position does not prove internal condition. |
| Existing P01 | Receiving pressure fell after approximately 10:00, reached the sampled low of 2.1 bar at 10:05:50, and recovered to 6.8 bar by 10:06:50. Upstream samples remained 6.8–6.9 bar. | Samples are not continuous coverage; timing uncertainty and other possible disturbances remain. |

Together these records strengthen an explanation involving **interruption of the distribution path, with recovery associated with opening the second valve in the auxiliary path**. The system should assemble and test that inference, distinguish it from the compressor-trip hypothesis, and identify its remaining uncertainty.

It should not claim that every leak or transient is excluded, that V-202's internal condition is proven, or that an employee deliberately ignored an instruction. The organizational explanation depends on withheld evidence.

Primary evidence: [P01 pressure/alarm record][p01], [P02 point register][p02], [P04 connection schedule][p04], [P05 field log][p05].

## 3. Confirmed failures

### F01 — New observations do not become a better mechanism

**Severity: critical. Location: map selection and synthesis.**

The reader extracted all four connection-schedule segments, the inline relationship between V-201 and V-202, M-101's closure, V-202's closed observation and subsequent opening. These facts appear in the saved 154-finding notebook.

However, the final selected premise set omits the four topology segments, the inline-valve finding, V-202's closed observation and V-202's opening. M-101's closure is reviewed as a supporting premise, but the board does not assemble the full path-and-sequence explanation. Its three broad branches remain compressor/control fault, supply-side disturbance and maintenance-preparation interference.

**Why this matters:** downstream reviewers can inspect only the proposed claims and connections; they cannot validate a useful mechanism the mapper never constructs. More extracted facts and more nodes did not produce the intended causal advance.

**What is established:** extraction succeeded for these facts; selection and integration did not. The internal reason the model overlooked them—attention, anchoring, prompt framing or another factor—has not been isolated experimentally.

There is also a confirmed context-selection weakness: the frame saw all 154 notebook entries but not original P04 text; refinement again saw the notebook but neither original P04 nor P05. Answer-resolution and connection calls did receive the original records. Thus this is not a missing-upload problem, but raw-source coverage at the synthesis stages was incomplete. A zero “omitted” count only means no ranked passages were dropped for capacity; it does not mean every source was selected.

Trace anchors: frame `b0053b1c-3674-425f-86a7-5df44258e742`; refinement `7f1777d6-e056-4bae-9da9-792e08aadbe9`; `runs[1].findings`, `position` and `calls` in the [diagnostic export][evidence].

### F02 — Local document limitations become global “missing evidence” claims

**Severity: high. Location: answer fetching, branches and questions.**

The piping resolver says the full schematic is absent and leaves the connectivity request awaiting the user, even though its first cited source, P04, provides the physical connection schedule. An approved graphical drawing and a connection table are not identical artifacts, but the table already answers the functional connectivity question.

Similarly, P01 says its export does not include alarm mapping. P02 explicitly supplies that mapping. Yet the final answer and branch gaps continue requesting whether AL-44 comes from P-R or a compressor-trip contact. The final map also retains “No evidence of field operation logged” after receiving P05's field operations.

**Why this matters:** the user is asked to resupply established information, while useful new evidence fails to close or narrow a question. A limitation in one document is being treated as a limitation of the whole evidence set.

The exact compressor-trip log remains genuinely unavailable. The failure is not keeping that uncertainty; it is bundling it with mapping and connectivity facts already supplied.

Trace: piping resolver `3e67c51c-9928-4b9c-8c6c-3a566141c830`, its assigned Q2 answer and evidence catalog; final branches B-02/B-03.

### F03 — Graph structure and causal roles are not consistently meaningful

**Severity: high. Location: connection generation and graph validation.**

The published V2 contains both:

- recovery **preceded** the incident; and
- the incident **preceded** recovery.

The reversed arrow's own rationale says recovery happened *after* the interruption. This is a direct mismatch between relation direction and explanation, not a subtle RCA disagreement.

C-11 RUN remains a **barrier** node although the evidence establishes a running indication, not a protective function. The earlier C-11 `failed-to-prevent` arrow was withdrawn, which is an improvement. However, a `failed-to-prevent` arrow from stable upstream pressure remains, without establishing an actual protective barrier.

**Confirmed harness gap:** connection validation checks selected endpoints, self-links, references and required text, but does not reject contradictory temporal arrows. Literal claim review updates the evidence status without validating the assigned node type. A supported reading is therefore not proof of a supported barrier role.

Sources: final board in the [export][evidence]; [connection application][apply]; [board projection][projection].

### F04 — A non-conflict is admitted as a conflict and blocks progress

**Severity: high. Location: claim reviewer and conflict interpretation.**

For the AL-44 timestamps, the V2 reviewer says the journal directly establishes the claim, returns `entailed`, and states:

> “The difference reflects precision level, not contradiction of record observation.”

But it also inserts that difference into `evidenceConflicts` with `impact: claim-truth`. The harness consequently marks the claim unknown. An approximate operator entry and a precise journal entry were not shown to contradict each other.

**Confirmed software behavior:** any accepted claim-truth conflict forces an unknown verdict. The existing consistency guard rejects `entailed` with necessary missing premises, but does not catch this contradiction between the conflict flag and its explanation. Three current connections depend on the alarm-timestamp premise; their verification is gated by unresolved premises, including this one.

A separate status translation loses information: the two connection verifiers returned `partial`; because each supplied both supporting and opposing references, application code stored `conflicting`, and the board rendered both as `unknown`. Missing information and genuine contradictory evidence are not interchangeable.

Trace: review `60b7aea1-8d44-45bd-8700-68055befdfdb`; [literal decision logic][literal]; [verification status application][changes]; [projection][projection].

### F05 — The reviewer can introduce new factual and causal errors

**Severity: high. Location: causal verification.**

One verifier writes that P05 shows “V-201 was opened and later closed.” P05 records V-201 opening and **M-101** closing. It does not record V-201 subsequently closing. The verifier has confused two different valves.

The same call asks whether **V-202 opening caused the pressure drop**. The supplied chronology places the opening around recovery, after the drop. Asking what caused the earlier loss is valid; framing the later recovery-associated action as the initiating action is not grounded in this sequence.

Another review says P05 states incomplete isolation “enabled the pressure drop.” P05 states incomplete isolation as a condition; the causal conclusion is the model's inference, not a quoted source finding.

**Why this matters:** a second model call is not automatically an independent factual authority. Source IDs and valid JSON cannot guarantee that the review accurately represents those sources.

Trace: verifiers `da20381b-14ca-490d-80a1-0207ca1dfe94` and `29e44c00-0bb1-4122-b3d9-ac632c396e41`, compared with [P05][p05]. Neither connection was promoted to supported, which appropriately limited the damage.

### F06 — Review detects an overstatement but does not repair the investigation

**Severity: high. Location: claim revision and publication sequence.**

The final summary and pressure node still say P-R reached 2.1 bar between 09:54 and 10:03. P01 places the 2.1 reading at **10:05:50**, with 2.6 at 10:03:10. The reviewer identifies the unsupported earlier timing, but the published statement remains unchanged.

Worse, the system asks for evidence that could prove 2.1 bar by 10:03, rather than proposing a corrected, source-faithful statement. The original claim should remain in history; a corrected claim should be explicit and reviewed—not silently rewritten or indefinitely defended.

The P-U claim has a related scope problem. “Throughout the window” overstates what discrete samples establish. The review's caution about unobserved transients is legitimate. What is missing is a usable narrower statement: **all supplied upstream samples are 6.8–6.9 bar**, without pretending that continuous stability is proven.

**Confirmed architectural cause:** map refinement runs before premise review and causal verification. Publication subsequently synchronizes statuses and questions; it does not reconcile the summary, branch explanations and overbroad claims with those review results.

Trace: pressure review `9fd94d68-7925-475d-9711-58936d336b98`; [planner phase order][planner]; `syncBoardEvidence` in [application code][apply].

### F07 — The question lifecycle loses new requests and retains obsolete ones

**Severity: high. Location: question routing and storyteller handoff.**

All **four** questions generated by V2's two causal-verification calls exist in saved state but are absent from the published question lists. They have neither an investigation-direction link nor a `reviewTargets` association that passes the current projection filter. The normal storyteller selector reads the published lists, so these requests are unavailable through that route.

This is a confirmed handoff defect, not an assertion that all four questions deserved to be asked. F05 shows that at least one first needed factual correction. Each should receive an explicit routing, correction, merge or rejection decision rather than silently disappearing.

Conversely, older questions remain visible after their parent claims become supported. Examples include the V1 demand for an independent “Turn 2” definition and three gaps about C-11 sampling. V2 accepts the report and sampled-bit claims, but those requests still await the user.

**Why this matters:** the next round can pursue stale questions while missing newly generated ones. This undermines the intended question → answer → revised-board loop even if the model generates a useful request.

Evidence: the export's per-question `displayed` flags; [projection filter][projection]; [question ingestion][records]; [storyteller selection][storycontracts].

### F08 — Answer-task scope is inconsistent between the schema and the runtime

**Severity: medium. Location: answer-resolution contract.**

In both versions, each of three resolution tasks was assigned one question but returned answers to all three visible questions. V2 retained the three assigned answers, quarantined six extra rows and recorded all three tasks as failed. Independent work continued.

**Confirmed software mismatch:** the packet identifies `assignedQuestions`, but the generated answer-ID enum includes all visible question IDs. Runtime application then rejects IDs outside the assignment. The schema allows output the commit logic refuses.

This is avoidable contract friction. Correcting it would remove these scope failures; it would **not** by itself fix the incorrect content of the assigned answers.

Trace: resolver calls `798eeff2-8319-402a-9bb5-0eb9a508d4c6`, `3e67c51c-9928-4b9c-8c6c-3a566141c830`, `87455879-e676-4544-a01b-a9cc7a608d29`; [executor schema construction][executor]; [resolve schema][contracts]; [assignment validation][apply].

### F09 — The storyteller is operational, but not an autonomous evidence authority

**Severity: high for unattended use. Location: storyteller evidence use and answer status.**

Both jobs completed once without a retry. The briefing answer preserved the missing-checklist limitation and was released unchanged. However, its `answered` label overstated completion of a request for briefing content that was not actually available.

The piping answer overlooked P04 despite that document appearing in its actual input catalog. It cited other records accurately but incorrectly treated connectivity as unestablished. The operator withheld it; it was **not fed into V2**. It therefore cannot explain V2's independent recurrence of the same omission.

This round demonstrated transport, source scoping and a reviewed partial release—not unattended storyteller success. P04/P05 were operator-selected before generation, and human review prevented the flawed piping answer from becoming evidence.

The released answer also repeats S02/S03 rather than adding independent testimony. Its reuse must not count as a second independent witness. A reviewer calls the repeated material “corroboration”; confidence inflation was not quantified in this test, so that remains a provenance risk rather than a proven scoring effect.

Evidence: [raw storyteller candidates][candidate], [release review][storyreview], [round notes][notes].

### F10 — Verification consumes most of the run without resolving the main mechanism

**Severity: high for practical usability. Location: review scheduling and task cost.**

V2 took **78 minutes 39 seconds**. Recorded task durations account for approximately 78 minutes 31 seconds, so almost all elapsed time is represented by task work, not an unexplained scheduling pause.

| V2 stage | Tasks | Recorded duration |
| --- | ---: | ---: |
| Read changed evidence | 4 | 4.21 min |
| Frame + refine | 2 | 5.26 min |
| Generate connections | 2 | 3.35 min |
| Resolve questions | 3 | 4.28 min |
| Review premises | 15 | **60.25 min** |
| Verify connections | 2 | 1.17 min |

Premise review used **76.6% of total elapsed time**. The planner invalidates previously selected claims whenever any source changes and rechecks current board dependencies. That is conservative, but it is not a dependency-sensitive assessment of which new evidence could affect which verdict.

This run did not have an infinite queue or more than 100 specialist agents: **154 is the finding count**, and no specialist-consultation tasks were scheduled. Nor did an application output cap stop V2: saved requests show the native 262,144-token context and uncapped generation (`-1`).

The practical failure is spending most of an approximately 79-minute cycle on checking selected premises while the useful mechanism remains unassembled. Removing checks would conceal errors; adding more time or token allowance alone would not address the observed defects.

Evidence: `stageTiming` and task/call records in the [export][evidence]; invalidation and scheduling in the [planner][planner]. V1's approximately 152-minute elapsed duration includes pauses and operator recovery and is not a fair uninterrupted-speed comparison.

## 4. What worked, and what should not be called a current failure

- Both versions are preserved and inspectable; V1 was not overwritten by V2.
- New documents were received and read. Relevant topology and valve observations were extracted.
- Previously read source passages were reused.
- Invalid answer siblings did not stop the entire V2 investigation.
- Unsupported connections were not promoted merely because they had citations or well-formed output.
- Five non-focal V2 nodes became supported, compared with one in V1. That is a real improvement in statement-level support, although not sufficient causal progress.
- Source limitations remain: sampled data, approximate times, text descriptions instead of original photographs, and missing briefing content.
- No final organizational root cause or corrective-action approval was required from this evidence batch.

Earlier V1 defects were addressed during recovery: invalid sibling edges no longer invalidate an otherwise usable frame; node selection and connection generation are separated; obsolete queued reviews can be superseded. A repetitive generation call was cancelled and one retry completed under the revised sampling profile. These are documented improvements, not proof that repetition or every execution failure is universally eliminated.

## 5. Root-level diagnosis: established versus unproven

| Finding | Confidence / basis |
| --- | --- |
| Useful facts reached the notebook but not the revised mechanism | Confirmed by source-reader findings and final map. |
| Review is downstream of the last map-refinement stage | Confirmed in planner code and execution order. |
| New verification questions are excluded from normal handoff | Confirmed by saved-state/published-list comparison and selector code. |
| Answer schema and assignment validation disagree | Confirmed in saved requests, outputs and code. |
| Conflict/status handling conflates several meanings | Confirmed by raw review outputs, applied states and projection code. |
| Review dominates runtime | Measured from saved task durations. |
| Prior-board anchoring or context presentation caused the synthesis failure | Plausible, not isolated. Requires a controlled comparison. |
| Larger models, embeddings, fine-tuning or more agents will solve it | Not established by these two versions. |

The structural issue is that **extracting, selecting, reviewing and publishing are implemented as separate tasks, but correction and question reconciliation are not reliably closed around them**. Meanwhile, formally valid model outputs can still misread evidence. Both layers need attention; blaming only the model or only the harness would overstate this experiment.

## 6. Repair priorities and observable acceptance criteria

These are recommendations, **not changes implemented by this report**. They must remain general-purpose; no incident-specific answer or preferred valve sequence should be embedded in production prompts.

| Priority | Required improvement | What would demonstrate success |
| --- | --- | --- |
| 1 | Close review-to-map and review-to-question feedback | Correctable claims receive explicit revised versions; stale gaps retire; every new verifier question is routed or explicitly rejected. No silent support promotion. |
| 2 | Make new-evidence integration explicit | Explain which branches change and why; include joint source evidence needed for the mechanism. Distinguish lack of a document format from lack of the information. |
| 3 | Separate observation, mechanism and graph-role checks | Do not accept opposite temporal arrows for the same ordered events; require evidence for a barrier role; validate entity/action/time consistency. |
| 4 | Align contracts and preserve verdict meanings | Resolver accepts exactly assigned answer IDs; false conflicts trigger an explicit review problem; partial support is not automatically flattened into conflict. |
| 5 | Make incremental verification selective | Preserve valid unchanged work where justified; recheck claims affected by new evidence or contradictions, with the dependency decision visible. Measure runtime and missed-conflict risk together. |
| 6 | Reassess unattended storyteller use | It uses the available relevant source, accurately labels partial answers, preserves source lineage and cannot silently pass incomplete evidence use as success. |

For this controlled V2, a defensible pass would reconstruct the two physical paths, integrate valve states with the pressure sequence, narrow the distribution explanation, and retain the stated uncertainties. It would not invent a compressor-trip proof, a deliberate instruction violation or a final management-system cause. The same checks should then be exercised on different incidents before claiming general robustness.

## 7. Audit trail and limits

- Incident: `9660f4f2-5fc0-4d0a-917e-8e48641956e3`
- Model track: `a6647fe7-b418-4232-817f-b3c6d3a5325d`
- V1: `a20904da-8710-40df-8d58-fec78f451f2a`
- V2: `3d44374c-888e-465a-8870-99d11eaa8c12`
- Story round: `c5bdbc70-37bd-42f3-9acc-00912637f096`
- [Open the investigation dashboard](http://127.0.0.1:3016/incident/9660f4f2-5fc0-4d0a-917e-8e48641956e3).
- [Diagnostic evidence JSON][evidence] contains saved sources, findings, final boards, public structured call outputs, task metrics and question-visibility flags. It excludes private model reasoning and credentials.
- [Read-only export script][exportscript] makes the measurement reproducible without launching inference or writing to the live database.

This report is based on one controlled case and one model configuration. It establishes concrete failures in these saved runs; it does not establish a cross-model failure rate. No arbitrary 100-point score has been invented. The expected physical mechanism is assessed against released records and the prewritten criteria, not against withheld organizational evidence. No app code, evidence inputs or saved verdicts were changed for this report.

[evidence]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/failure-report-evidence.json>
[expectations]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-expectations.md>
[recovery]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v1-frame-recovery.md>
[notes]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/run-notes.md>
[candidate]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/story-candidate.json>
[storyreview]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/story-review.json>
[p01]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B1/IA-P01_pressure_and_alarm_extract.md>
[p02]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B1/IA-P02_point_register.md>
[p04]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B2/IA-P04_installation_and_line_register.md>
[p05]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B2/IA-P05_field_execution_and_observation_log.md>
[planner]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/planner.ts>
[apply]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/apply.ts>
[contracts]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/contracts.ts>
[executor]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/tasks/executor.ts>
[literal]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/review/literal-decision.ts>
[changes]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/board/changes.ts>
[projection]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/board/projection.ts>
[records]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/records.ts>
[storycontracts]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/story-agent/contracts.ts>
[exportscript]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/scripts/export-v1-v2-failure-evidence.mjs>

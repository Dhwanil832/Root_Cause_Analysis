# Try 6 RCA — V1 review and V1 → V2 progression

**Review date:** 20 September 2026  
**Case:** IA-16036 instrument-air interruption  
**Model:** `ollama:qwen3.5:latest`  
**Purpose:** presentation-ready diagnosis of saved results, not a new experiment or an implementation change.

## Executive finding

**The system produced two preserved investigation versions, but V2 did not turn the new evidence into the expected improvement in the physical-mechanism explanation.**

V1 was not expected to solve the incident. It was expected to describe the known event accurately, distinguish observations from hypotheses, build a logically consistent preliminary board, and ask for genuinely missing information. It did some of this, but already contained a reversed recovery arrow, an incorrect pressure timestamp, redundant evidence requests and an unjustified barrier classification.

V2 read the new records, extracted useful topology and valve observations, and supported more individual statements. However, it preserved V1's three broad branch explanations and their outdated gaps. It also exposed defects in review interpretation and question handoff. The board grew from **5 to 9 nodes**, but **verified connections remained 0**.

This is not evidence that a complete root cause should have been identified in V1, or that every unknown connection is a failure. The failure is more specific: available facts were misrepresented, useful evidence did not narrow the mechanism, and review feedback did not consistently correct what was published.

The strongest confirmed software causes are inconsistent task contracts, missing graph-semantic validation, loss of verdict meaning, an incomplete review-to-publication feedback loop, and a question projection filter that excludes new verifier questions. The exact internal cause of the model's omissions and misreadings is **not established**. This report does not substitute guesses about attention, anchoring or model capacity for evidence.

## 1. Scope, method and evidence boundary

The review uses the frozen [diagnostic export][evidence], released source documents, public structured outputs, task records, final boards, published question lists, and the code that applies those outputs. It does not rely on private model reasoning. The original V1 hash matches its pre-V2 capture.

| Measurement | V1 | V2 |
| --- | ---: | ---: |
| Uploaded documents, excluding incident description | 10 | 12 |
| Released storyteller answers | 0 | 1 |
| Notebook findings | 100 | 154 |
| Board nodes, including focal event | 5 | 9 |
| Active connections / verified connections | 4 / 0 | 6 / 0 |
| Supported non-focal nodes | 1 | 5 |
| Executed premise-review tasks | 5: 3 completed, 2 failed | 15 completed |
| Connection-verification calls | 0 | 2; neither supported |
| Failed answer-resolution tasks | 3 | 3 |
| Saved questions / published questions, including baseline | 10 / 9 | 16 / 11 |
| Published status | Partial; finished | Partial; finished |

“Completed” means a task's output passed its execution contract; it does not mean the statement or review was correct. Supporting premises can be reviewed without becoming separate nodes. Finding counts are not agent counts. Publication is not RCA acceptance.

V1 took approximately 152 minutes including pauses and engineering recovery. V2 took 78 minutes 39 seconds. V1's recovery changed execution behavior and a sampling profile; these durations are **not a controlled speed comparison**. See the [V1 launch receipt][launch] and [recovery receipt][recovery]. Both versions used the same saved model digest, recorded in §10.

V1 expectations below are a retrospective rubric reconstructed from the frozen V1 inputs and launch objectives. They were not all written as detailed acceptance tests beforehand. The [V2 expectations][expectations] were written before the storyteller round. Neither version is assessed against withheld organizational evidence. This is one case and one model configuration, not a cross-model benchmark.

## 2. V1 reviewed on its own

### 2.1 What V1 knew — and what it should establish

V1 had the incident description, three default references, three starter records, P01–P03 and the unverified C01 desk message. It did **not** have P04's connection schedule or P05's field valve chronology.

| Released evidence | Expected V1 understanding | Boundary that must remain |
| --- | --- | --- |
| Incident description and S01 shift log | Pressure interruption around 10:00; later recovery; no reported injury | Reported observations are not a complete reconstruction of the physical event |
| P01 measurements | P-R falls while supplied P-U samples remain 6.8–6.9 bar; C-11 RUN samples remain 1 | Discrete readings do not establish continuous conditions; a running contact is not flow |
| P02 point register | AL-44 is driven by low P-R pressure; “COMP FAULT” is a legacy display label | This alarm is not direct proof of a compressor trip; a separate trip is not conclusively excluded |
| S02/P03 work records | Work was preparation-only; an older procedure and drawing were identified | Blank fields and an old revision alone do not establish a violation or why someone acted |
| S03 authorization record | Listed personnel held the recorded qualifications and authorization | Attendance does not establish valve-by-valve briefing content or actual actions |
| D01 area directory | Broad equipment locations and responsibilities | Current physical routing and incident-time valve positions remain genuinely missing |
| C01 desk message | A second-hand compressor-trip suggestion exists | It is not witnessed trip evidence and does not override the point register |

**Fair V1 target:** an accurate, provisional event model with open alternatives and focused requests for routing, valve actions and actual briefing content. No final physical or organizational root cause was required.

### 2.2 Audit of every V1 board node

| V1 node | Published status/type | Review assessment |
| --- | --- | --- |
| Focal pressure-loss event | Proposed focal event | Useful incident anchor. Keep the alarm's legacy label distinct from its actual low-pressure input. |
| Incident reported around 10:00, Turn 2 | Partially supported event | The description directly reports this. Corroborating the underlying event is different from requiring independent proof of the report's “Turn 2” wording. |
| AL-44 occurrence, acknowledgment and clearance | Proposed event | The three timestamps are present in P01. A reviewer returned both entailment and necessary missing premises; the consistency guard rejected that output. |
| Local indication returned to normal band | Supported condition | Grounded in the shift log. P01 also supplies numerical recovery readings that the edge explanations overlook. |
| C-11 RUN = 1 at supplied samples | Proposed **barrier** | The sampled statement is grounded. The barrier role is not: a running indication is not an established protective function. Its reviewer also returned an invalid entailment-plus-missing-premises combination. |

The important distinction is **statement truth versus causal role**. Even a fully supported RUN observation would not establish a barrier.

### 2.3 Audit of every V1 connection

| Saved connection | Assessment | Exact problem or limitation |
| --- | --- | --- |
| Pressure loss → AL-44, `caused` | Plausible mechanism, not verified | P02 supplies the low-pressure mapping, yet the edge still says alarm mapping is unavailable. A timestamp premise remained unresolved. |
| Recovery → pressure loss, `preceded` | Incorrect direction | The edge's own rationale says recovery occurred **after** the interruption. |
| Pressure loss → recovery, `preceded` | Reasonable temporal ordering, not causal proof | It coexists with the opposite arrow and incorrectly treats numerical recovery confirmation as missing. |
| Pressure loss → C-11 RUN, `failed-to-prevent` | Unsupported relation/role | A pressure-loss event is not a protective barrier; the RUN indication is not shown to be one either. The record does not establish the trip assumed in the rationale. |

All four were displayed as unknown; none was verified. The **absence of verified edges alone is not the failure**. A provisional board may legitimately contain unknown edges. The observable failures are the inconsistent direction, unsupported role and false evidence gaps.

### 2.4 V1 factual accuracy and question quality

**Pressure timing:** finding `22dc870b-4cb9-4384-8d38-f5b2e59bffa5` and the V1 summary say P-R reached 2.1 bar between 09:54 and 10:03. P01 instead records **2.6 at 10:03:10** and **2.1 at 10:05:50**. The error therefore predates V2. In V1 it is a notebook/summary error; V2 also selects it as a board node.

**Recovery evidence:** P01 records 6.0 at 10:06:20 and 6.8 at 10:06:50. The board's assertion that a numerical recovery value is missing is false for the available evidence set.

**Reviewer misreading:** the failed V1 alarm review asks about a threshold crossing at 10:00:11. P01's P-R value then is 5.8; P02's low threshold is below 4.5. This is an error in a rejected review output, **not a supported published fact**.

**Useful questions:** ask for actual piping connectivity, valve-by-valve field actions and briefing content. Those details genuinely were missing in V1. A compressor trip log could also distinguish a remaining alternative.

**Redundant components:** AL-44 source mapping and the measurement-point identities were already provided in P02. Requests bundling these with legitimately missing trip or routing records should have separated known and unknown parts. The three primary directions were defensible only after that narrowing.

**V1 conclusion:** a useful preliminary investigation exists, but it is not yet a reliable baseline board. Its problem is not incompleteness; it is avoidable factual and structural inconsistency within the evidence already supplied.

## 3. What V2 added and what progress was expected

P04 supplies two physical routes:

- Normal: H-U → M-101 → D-101 → M-102 → H-R.
- Auxiliary: H-U → V-201 → B-17 → V-202 → H-R. V-201 and V-202 are in series.

| Time / order | Record | Observation |
| --- | --- | --- |
| About 09:56 | P05 | V-201 opened |
| 10:00:03 ±5 s | P05 | M-101 closed |
| 10:00:11 onward | P01 | P-R readings fall; P-U samples remain near their earlier range |
| 10:05:40 ±5 s | P05 | V-202 observed closed; M-102 open |
| 10:05:50 | P01 | Lowest supplied P-R sample: 2.1 bar |
| 10:06:18 ±5 s | P05 | V-202 opened; M-101 stayed closed |
| 10:06:20 / 10:06:50 | P01 | P-R = 6.0 / 6.8 bar |

These records should strengthen a **distribution-path interruption hypothesis**, with recovery associated with opening the second valve in the auxiliary route. That is an evidence-based inference, not a proven final root cause. A late closed-valve observation does not prove uninterrupted earlier closure, handle positions do not prove internal valve condition, and the sources do not establish every possible transient or the organizational reason for the configuration.

The released storyteller answer repeats briefing/work-record information. It is not an independent witness. P04/P05 were operator-selected; the storyteller did not autonomously discover the required release.

## 4. V1 → V2: genuine progress versus persistence

| Dimension | V1 | V2 | Assessment |
| --- | --- | --- | --- |
| Evidence extraction | 100 findings | 154; relevant new topology and valve observations retained | Improved ingestion |
| Statement support | 1 supported non-focal node | 5 supported non-focal nodes | Real statement-level improvement |
| Mechanism branches | Compressor/control fault; supply disturbance; maintenance interference | Same three titles, mechanisms and gap texts; version markers updated | No substantive branch revision |
| C-11 prevention edge | Present | Withdrawn | Genuine correction |
| C-11 node role | Barrier | Still barrier, now supported as a statement | Role error persists |
| Temporal direction | Both recovery-before-loss and loss-before-recovery | Both remain | Persistent structural failure |
| P-R timing | Wrong in notebook/summary | Wrong in summary and new pressure node, despite partial review | Error propagated; correction not applied |
| Piping/field gaps | Routing and actions genuinely missing | P04/P05 supplied, but old gaps persist | Missed evidence integration |
| Verified links | 0 | 0 | No verified causal advance; not an automatic demand to force support |
| Question handoff | 9 published questions | 11 published; all 4 new verifier questions hidden | New requests do not reach normal answering route |

V2 retained three V1 edges, withdrew the C-11 prevention edge, and added three edges: stable P-U `failed-to-prevent` the loss, preparation status `enabled` it, and incomplete isolation `enabled` it. These do not assemble the route-and-valve sequence. Stable pressure is also not an established protective barrier. The two `enabled` connections were reviewed but neither supported.

The V2 reader extracted the four connection segments, inline-valve relationship, M-101 closure, V-202 closed observation and subsequent opening. The final selected premise set omitted the topology segments and V-202 observations. This locates the missed integration **after successful extraction**, not at upload.

## 5. Confirmed failure register: expected, observed, cause and repair

These severity labels prioritize investigation reliability; they are not a numerical performance score. Proposed repairs have not been implemented or validated by this review.

### F01 — Extracted facts do not become an updated mechanism · Critical

**Expected:** new route and valve records narrow the physical hypothesis while retaining uncertainty.  
**Observed:** facts exist in the notebook; final branch content remains unchanged and key topology/state premises are not selected.  
**Established cause boundary:** synthesis/selection failed. Frame had all 154 notebook entries but no original P04 text; refinement had all findings but neither original P04 nor P05. Other calls did receive those original records. Lexical selection therefore did not guarantee original changed-source coverage at synthesis. The internal reason for overlooking facts already in the notebook is unknown.  
**Proposed repair:** build a source-linked entity/state/time representation, supply joint evidence bundles, and require a version-delta decision for every affected branch. Test coverage and use separately; more context alone is not the acceptance criterion.

### F02 — Available information remains “missing” · High

**Expected:** distinguish a missing document format from missing information.  
**Observed:** piping resolver cites P04 yet leaves connectivity unanswered; P02 mapping is repeatedly requested; V2 still says no field operation is logged despite P05.  
**Established cause boundary:** retrieval alone does not explain this: the piping resolver had the relevant record. The result demonstrates failure to use/combine available evidence.  
**Proposed repair:** answer each requested fact separately with supporting spans; mark the residual gap, not the whole request, unanswered. Treat a diagram, table or prose description as alternative carriers of the required information.

### F03 — Structurally valid graph, semantically invalid relations · High

**Expected:** source/target direction and causal roles match evidence.  
**Observed:** opposite temporal arrows coexist; RUN remains a barrier; stable upstream pressure receives a prevention relation.  
**Confirmed harness cause:** connection application validates IDs, endpoints and required fields, but not contradictory temporal order. Literal support synchronization does not validate node role.  
**Proposed repair:** separate observation support, role validity and link validity. Check ordering for the same event instances; require an identified protective function for barrier/prevention labels. Do not prohibit legitimate feedback in every graph—validate the particular temporal relation and event identity.

### F04 — Review status loses its meaning · High

**Expected:** distinguish insufficient evidence, contradiction, partial support and invalid review.  
**Observed:** V2 AL-44 reviewer returns entailment, says timing precision is not a contradiction, but sets a claim-truth conflict. The harness assigns unknown. Three edges depend on this premise. Both causal verifiers return partial; support-plus-opposition references become stored `conflicting`, then displayed `unknown`.  
**Confirmed harness cause:** flag-based conflict handling does not reconcile the contradictory review explanation; status application and projection flatten different meanings.  
**Proposed repair:** explicit verdict algebra. A conflict must identify incompatible propositions about the same entity/time/scope. Reject or repair inconsistent review output; never silently promote a questionable claim to supported.

### F05 — Review introduces source misreadings · High

**Expected:** reviewers accurately check entities, values and chronology.  
**Observed:** a V2 verifier says V-201 was opened and later closed. P05 says V-201 opened and **M-101** closed. It also asks whether V-202 opening caused the drop, although that action is associated with later recovery. Another verifier attributes the causal conclusion “enabled the pressure drop” to a record that states a condition.  
**Established cause boundary:** these are demonstrable output/source mismatches. Their model-internal cause is not established. Neither link was promoted to supported.  
**Proposed repair:** source-span checks on typed entity/action/time records; distinguish quoted observation from inferred mechanism. A second LLM call is not a factual authority merely because it is called a reviewer.

### F06 — Detected errors are not repaired before publication · High

**Expected:** corrected claims, map and summary agree with review results.  
**Observed:** V2 pressure review detects the wrong 2.1-bar timing, but the original wording survives and a question asks for evidence to support it. P-U wording also remains broader than the discrete samples justify.  
**Confirmed architecture cause:** final map refinement precedes premise review and connection verification. Later synchronization updates statuses/questions, not a reconciled mechanism and corrected statement set.  
**Proposed repair:** explicit, versioned claim amendments followed by affected-link reassessment and publication consistency checks. Preserve the rejected wording in history; do not defend it indefinitely or rewrite history silently.

### F07 — Question lifecycle loses new work and retains stale work · High

**Expected:** each question is answered, pending, merged, superseded or explicitly rejected, with a reason.  
**Observed:** all four new V2 verifier questions are saved but absent from published lists and normal storyteller selection. Old Turn-2 and RUN-sampling requests remain after parent claims become supported.  
**Confirmed harness cause:** new verifier questions lack the direction/review-target associations required by the projection filter. The storyteller reads those projected lists. Question state is not fully reconciled with revised findings.  
**Proposed repair:** a canonical question registry with explicit routing/disposition and lineage to the originating issue. Not every new question should be sent to the user: factually wrong questions must be corrected or rejected, visibly.

### F08 — Resolver schema permits output the runtime rejects · Medium

**Expected:** one assigned question permits answers for that assignment only.  
**Observed:** in each version, three resolver calls each answer all three visible questions. Assigned answers survive; six extra rows are quarantined and all three tasks are marked failed.  
**Confirmed code cause:** schema answer-ID enum includes all visible questions, while commit checks assignment IDs.  
**Proposed repair:** build schema and validator from the same assignment object. Keep valid-sibling salvage and explicit rejected-row reporting. This fixes scope friction, not wrong answer content.

### F09 — Storyteller still needs human evidence-use review · High for unattended use

**Expected:** use supplied sources, accurately label partial answers, preserve lineage.  
**Observed:** both jobs completed once. Briefing answer was released unchanged but its “answered” status overstated missing briefing content. Piping answer overlooked P04 present in its input; human review withheld it. It was **not fed into V2**, so it did not cause V2's independent piping omission.  
**Established limit:** transport and a reviewed partial release worked; unattended semantic reliability was not demonstrated. Memory consistency across multiple later rounds was not tested here.  
**Proposed repair:** assess source coverage and answer completeness separately; retain source ancestry so repeated document excerpts do not become independent corroboration. Confidence inflation from duplication is a risk, not a measured effect in this test.

### F10 — Review cost dominates without the intended causal gain · High for usability

**Expected:** new evidence triggers relevant reassessment with useful progress.  
**Observed:** 15 premise-review tasks account for 60.25 minutes, **76.6%** of V2 elapsed time.  
**Confirmed scheduling behavior:** any changed source invalidates selected claims and current dependencies are rechecked. This is not dependency-sensitive invalidation.  
**Proposed repair:** track source/claim/link dependencies and explicit contradiction triggers; reuse reviews only when their assumptions remain valid. Measure missed-conflict risk alongside latency. No speedup percentage is promised.

| V2 stage | Tasks | Recorded minutes |
| --- | ---: | ---: |
| Read changed evidence | 4 | 4.21 |
| Frame + refine | 2 | 5.26 |
| Generate connections | 2 | 3.35 |
| Resolve answers | 3 | 4.28 |
| Review premises | 15 | 60.25 |
| Verify connections | 2 | 1.17 |

Recorded task durations total about 78 minutes 31 seconds versus 78 minutes 39 seconds elapsed. There is no unexplained long scheduling pause here. No specialist-consultation tasks were scheduled. The saved requests use the native 262,144-token context and uncapped generation (`-1`); this V2 did not stop because of an application output cap.

## 6. Research-backed direction — not claims of proven local fixes

Research checked online on 20 September 2026. The following are primary publications. The implementation suggestions are adaptations to our observed failures, not results already demonstrated on this RCA system.

| Research | Relevant idea and limitation | Proposed local application |
| --- | --- | --- |
| **Sufficient Context**, Joren et al., ICLR 2025 | Separates inadequate context from failure to use adequate context in RAG. Its QA experiments do not establish industrial RCA reliability. | Measure whether a packet contains the facts needed for its exact task; then evaluate answer use independently. Do not diagnose every omission as retrieval failure. [Paper page](https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems-2/) |
| **ChainRAG**, Zhu et al., ACL 2025 | Addresses entity loss in multi-hop question decomposition using progressive retrieval and rewriting. Evaluated on multi-hop QA, not incident causation. | Retrieve related topology, component identity, state and timing together; preserve entity IDs across subtasks. [Paper](https://aclanthology.org/2025.acl-long.1089/) |
| **Graph-constrained Reasoning**, Luo et al., ICML 2025 | Constrains reasoning paths to a knowledge graph. Graph faithfulness is not proof that the graph is correct or causal; the paper's full approach includes a specialized model. | Borrow the constraint principle for source-linked entities, relation roles and temporal direction. This recommendation does not require adopting its full training architecture. [Paper](https://proceedings.mlr.press/v267/luo25t.html) |
| **ProgCo**, Song et al., ACL 2025 | Studies program-driven verification and refinement; evaluated on instruction-following and mathematics. It is not a guarantee that self-review is correct. | Use executable checks for IDs, numbers and order, and feed failures into explicit claim revision. Semantic judgment still requires evidence review. [Paper](https://aclanthology.org/2025.acl-short.73/) |
| **TraceElephant**, Chen et al., ACL 2026 | Failure attribution uses complete execution inputs/context as well as outputs and reproducible environments. Results are not a measured improvement for our system. | Retain packet → output → applied state → published view traces; replay the exact failing boundary instead of rerunning the whole incident. [Paper](https://aclanthology.org/2026.acl-long.912/) |
| **DeltaLogic**, Dhanda, April 2026 **preprint** | Uses controlled premise edits to measure belief revision. Small logical classification experiments, not free-form industrial RCA or this Qwen configuration. | Test supporting, defeating, removed and irrelevant evidence separately; score required changes and required stability. This is an evaluation design, not an explanation of Qwen's internal failure. [Preprint](https://arxiv.org/abs/2604.02733) |

The research supports a direction: **source-grounded state representation, constrained checks, explicit revision, and controlled delta evaluation**. It does not justify promises that embeddings, a larger context, fine-tuning, extra agents or a different model will solve these failures.

## 7. Proposed root-level repair sequence

1. **Make the contracts internally consistent.** One task assignment drives schema and validation. Preserve partial versus unknown versus conflicting. Give every question a durable origin and explicit disposition. These are deterministic software issues.
2. **Represent observations separately from interpretations.** Record source, entity, action/state, time interval, value/unit and uncertainty. Preserve ordinary prose too; the representation should support checking, not erase context. Bind pressure rows and valve actions to their actual component IDs.
3. **Make each new evidence batch produce an explicit investigation delta.** For every affected branch, state strengthened/weakened/unchanged/newly unresolved and cite the contributing records. Require information-level coverage, not a particular document title or format.
4. **Close review back into publication.** Review can propose a narrower or corrected claim; the amended claim and affected links are checked. The final summary, branch gaps, board and question queue must refer to that same versioned state.
5. **Reuse only demonstrably unaffected checks.** Record dependency reasons and invalidate on relevant new evidence or contradictions. Do not trade silent uncertainty for speed.
6. **Re-evaluate on frozen inputs before another autonomous round.** Replay the known software failures; then rerun clean V1 and the controlled V2 delta under one fixed configuration. After that, test changed and unrelated incidents before claiming generality. Keep storyteller evaluation separate from RCA evaluation.

This is a proposed architecture correction, not incident-specific prompt patching. Production prompts should not contain a preferred valve or the expected answer for this case. No model combination or fine-tuning is required for the first implementation of these changes.

## 8. Observable acceptance tests

| Test | Pass condition |
| --- | --- |
| V1 source accuracy | Preserve exact P01 time/value pairs; AL-44 described as P-R low-pressure input; sampled RUN not treated as proven flow or barrier |
| V1 provisional graph | No recovery-before-loss relation for the same ordered events; uncertainty allowed without contradictory arrows |
| V2 integration | Assemble both paths, M-101 closure and V-202 recovery-associated opening into a qualified distribution-path hypothesis, or explicitly explain contrary source evidence |
| Evidence gaps | Stop requesting mapping/connectivity already supplied; retain only real residual uncertainties such as earlier continuous valve state and actual briefing content |
| Review consistency | A reviewer that says “not a contradiction” cannot silently create a claim-truth conflict; partial is not converted to conflict just because both reference lists exist |
| Claim repair | Incorrect timestamp claim is explicitly superseded; summary, board and dependent questions agree with the corrected record |
| Question conservation | Every saved verifier question has a published route or explicit merge/rejection/supersession; no silent disappearance |
| Task scope | Exact assigned answer IDs accepted; out-of-assignment IDs fail a matching schema/validator contract; valid siblings preserved |
| Storyteller | Uses relevant P04/P05 information, labels residual gaps as partial, and preserves original source lineage; no human rewrite needed for acceptance |
| Cost and generalization | Compare on a fixed model/configuration; report latency plus factual/causal accuracy and missed conflicts, then repeat on unseen incidents and irrelevant/contradictory deltas |

The controlled V2 pass is not “force a supported causal arrow.” It is **a justified, more specific mechanism or a source-grounded reason it cannot be supported**, with accurate uncertainty and a functioning next-question loop.

## 9. What can be said confidently in a presentation

**Established:** ingestion and version preservation work in this test; V1 already had factual/graph defects; V2 improves statement support but not the expected causal mechanism; identified code paths explain several propagation and handoff failures; review dominates measured V2 cost.

**Not established:** a universal Qwen limitation, prior-board anchoring as the cause, context overload as the cause, a guaranteed remedy from embeddings or fine-tuning, an autonomous storyteller pass, a final organizational root cause, or a general success/failure rate across incidents.

**Recommended headline:** “We have progressed from execution failure to an inspectable two-version investigation. The remaining bottleneck is evidence integration and correction: the system can collect and check facts without reliably revising its causal model.”

## 10. Reproducibility and trace index

- Incident: `9660f4f2-5fc0-4d0a-917e-8e48641956e3`
- Track: `a6647fe7-b418-4232-817f-b3c6d3a5325d`
- V1: `a20904da-8710-40df-8d58-fec78f451f2a`
- V2: `3d44374c-888e-465a-8870-99d11eaa8c12`
- Story round: `c5bdbc70-37bd-42f3-9acc-00912637f096`
- Model digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- V1 alarm review: `f7db8787-5ba9-431d-9129-1f83bed4d96f`; RUN review: `cc9428a7-f9e7-41b4-bb8f-b4c7eefdb736`
- V2 frame: `b0053b1c-3674-425f-86a7-5df44258e742`; refinement: `7f1777d6-e056-4bae-9da9-792e08aadbe9`
- V2 piping resolver: `3e67c51c-9928-4b9c-8c6c-3a566141c830`
- V2 false-conflict review: `60b7aea1-8d44-45bd-8700-68055befdfdb`; pressure review: `9fd94d68-7925-475d-9711-58936d336b98`
- V2 link reviews: `da20381b-14ca-490d-80a1-0207ca1dfe94`, `29e44c00-0bb1-4122-b3d9-ac632c396e41`

| Failure | Evidence / code to inspect |
| --- | --- |
| F01/F02 | Export `runs[].findings`, `position`, `calls`; [retrieval][retrieval], [context][context] |
| F03/F06 | Export `board`; [application][apply], [planner][planner] |
| F04 | Raw review verdicts versus board statuses; [literal decision][literal], [literal contract][literalcontract], [changes][changes], [projection][projection] |
| F05 | Public verifier outputs versus [P01][p01], [P02][p02], [P05][p05] |
| F07 | Export question `displayed` flags; [projection][projection], [records][records], [story selector][storycontracts] |
| F08 | Resolve task assignment/output; [executor][executor], [contract][contracts], [application][apply] |
| F09 | [Story candidates][candidate], [release review][storyreview], export `story` |
| F10 | Export `stageTiming`, `tasks`, `calls`; [planner][planner] |

No app code, run verdicts or evidence inputs were changed for this review. The earlier report remains preserved. The editable slide deck summarizes this report; its speaker notes link to the evidence and research.

[evidence]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/failure-report-evidence.json>
[expectations]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-expectations.md>
[launch]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-clean-v1-launch.md>
[recovery]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v1-frame-recovery.md>
[p01]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B1/IA-P01_pressure_and_alarm_extract.md>
[p02]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B1/IA-P02_point_register.md>
[p04]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B2/IA-P04_installation_and_line_register.md>
[p05]: </Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible/03_progressive_evidence/B2/IA-P05_field_execution_and_observation_log.md>
[candidate]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/story-candidate.json>
[storyreview]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/story-review.json>
[retrieval]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/knowledge/retrieval/index.ts>
[context]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/context.ts>
[apply]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/apply.ts>
[planner]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/planner.ts>
[literal]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/review/literal-decision.ts>
[literalcontract]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/review/literal-contract.ts>
[changes]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/board/changes.ts>
[projection]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/board/projection.ts>
[records]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/records.ts>
[storycontracts]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/story-agent/contracts.ts>
[executor]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/tasks/executor.ts>
[contracts]: </Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/src/engine/investigation/contracts.ts>

# RCA research brief: Try 4–6, existing research, and two paper directions

**Prepared for:** discussion with the professor  
**Date:** 20 September 2026  
**Current preference:** an RCA-method paper focused on the investigation as a whole. The previously dropped evaluation/failure-analysis direction is included as an alternative for discussion, not as an adopted change of direction.

## Executive summary

Our objective is to support an industrial incident investigation from the initial account through evidence gathering, competing explanations, causal reconstruction, and prevention-oriented findings. The application and its agents are the means of conducting that investigation.

- **Try 4** developed an evidence-led, multi-specialist investigation pipeline. It produced useful questions and visible causal boards, but relevant facts did not consistently become a complete, supported mechanism. Later attempts also exposed context growth and excessive graph-processing work.
- **Try 5** replaced much of the execution engine with persistent tasks, stable evidence references, local failure handling, and a separate storyteller. This improved recoverability and some claim checks, but investigation work still expanded before a useful version could finish, and several semantic checks remained unreliable.
- **Try 6** changed the investigation strategy: establish an initial position first, then consult specialists and review the premises that position actually needs. Two versions were preserved in the reviewed experiment. However, new evidence improved individual statements more than the causal explanation.
- **Existing research** includes fault-localization systems, interactive benchmarks, graph-guided diagnosis, industrial report-to-causal-graph extraction, and diagnostic-process evaluation. Our contribution cannot simply be “using agents” or “drawing a causal graph.”
- **Two possible papers:** (1) a method for evidence-grounded, progressive industrial RCA; or (2) a controlled study of causal investigation and revision in single- and multi-agent systems, potentially with a targeted improvement.

The present results motivate these directions. They do not yet demonstrate a generally reliable end-to-end RCA method or a general limitation of language models.

## Reading and evidence boundaries

1. **Try 4/5/6 are application generations. V1/V2/etc. are evidence versions within an individual model track.** They are not interchangeable.
2. A completed run, a displayed board, a supported statement, a verified causal connection, and an expert-accepted RCA are different achievements.
3. These development runs used different evidence packages and included documented interventions. They are not a controlled Try 4-versus-5-versus-6 performance benchmark.
4. Historical files copied into a later folder are not new results for that later implementation. In particular, Try 5's copied R3 scorecards remain Try 4 or earlier records.
5. Section A reports recorded observations and implemented designs. Sections B and C distinguish published claims, our interpretation, and proposed work. No new experiment was run to prepare this brief.

# A. What Try 4, Try 5, and Try 6 were about

## A1. Try 4 — evidence-led specialist investigation and causal-board construction

### Purpose and approach

Try 4 extended the earlier workbench into an evidence-led RCA workflow. It was provider-independent, not a Qwen-only application; several of the detailed experiments used Qwen alone to isolate its behavior.

The intended progression was:

**Incident and documents → context and entities → incident tags → selected specialists → questions → brokerage and answer fetching → evidence assessment → causal board → causal verification → corrective-action proposals.**

The design retained separate model tracks and immutable evidence versions. Default references, incident starter documents, and later question-response uploads remained separately attributed. Specialist knowledge, evidence provenance, contradictions, decision summaries, and human review were exposed in the workbench. Corrective actions were gated behind verified causes. [L1]

### What changed relative to the earlier implementation

- Source-quality assessment before downstream reasoning, including weak or misleading evidence.
- More explicit provenance, causal-link direction, alternative explanations, and verification requirements.
- Stage and later model-call checkpoints so successful work could survive interruptions.
- Further 4.3-series changes: exact source spans, application-assigned identifiers, separate node/link generation, local rejection of invalid proposals, and smaller causal operations.
- Separate storyteller experiments, eventually with frozen answer batches so storyteller behavior and RCA behavior could be examined independently. [L1–L4]

These changes accumulated over several revisions; “Try 4” was not one unchanging configuration.

### What worked

An early synthetic R3 test completed its model-driven stages and produced 13 nodes and 7 links. It asked relevant questions and withheld corrective actions when causes were not verified. Its local scorecard was **68/100**, an internal rubric score rather than a public benchmark result. [L2]

A separate ground-truth-derived R3 experiment also scored **68/100**. It recovered important elements of the mechanism in its facts and chronology, including wedging, yoke movement, off-center release, and gravity exposure. It did not receive the withheld original answer-key documents. [L3]

### What failed, and what the records establish

| Observed limitation | Concrete recorded result | Meaning for RCA |
| --- | --- | --- |
| Incomplete evidence assessment | The early R3 run assessed 5 of 32 supplied segments; the separate ground-truth-derived run assessed 1 of 32. | Receiving evidence did not ensure systematic assessment of its relevance and reliability. |
| Incomplete causal integration | The ground-truth-derived run captured hydraulic bleed-through/yoke drift in narrative records but did not complete the corresponding physical causal chain on the board. | Knowing individual facts was not equivalent to explaining how the incident occurred. |
| Unverified conclusions | Corrective actions remained blocked because causal targets were not verified. | The action gate behaved cautiously, but the investigation had not reached a completed RCA. |
| Misleading appearance of maturity | The audited R3 V1–V4 sequence displayed boards but retained empty focal-node references and zero nodes flagged verified. | A visually developed board was not evidence of a validated investigation. |
| Context loss in a later IA-16036 continuation | A saved V2 ended with one node and no links after 92 new calls; backend logs recorded input truncation. | Removing application size guards did not preserve effective use of all evidence. |
| Excessive candidate/link expansion | Another continuation reached 149 nodes and 1,175 candidate links, including 203 repeated endpoint/type relationships; linking required 264 calls and revision 130 calls. | More processing did not demonstrate better causal understanding. |
| Consolidation still blocked by growing shared input | A later restart reused ten discovery calls but stopped during consolidation under the harness's context estimate. | Splitting individual tasks did not remove the growing shared catalog. |

Sources: the two separate R3 scorecards, the 4.3 repair record, and the cross-run audit. The IA-16036 rows concern different continuations, not one run containing every failure. [L2–L4]

**Assessment:** Try 4 established the workflow and produced meaningful investigative material. Its recurring weakness was converting accumulated information into a coherent, traceable mechanism without losing evidence or expanding the workload excessively. The exact internal reason for every model error was not established.

## A2. Try 5 — a persistent investigation engine with smaller responsibilities

### Why we changed the design

The September 18 audit recommended replacing the ownership and execution boundaries rather than continuing to add retries or larger context allowances. The guiding principle was: **the application stores and organizes the investigation; models interpret evidence and propose judgments.** [L4]

### What changed

- A durable task ledger replaced dependence on one long-running investigation cycle. Tasks had explicit inputs, dependencies, leases, outputs, and recovery states.
- Original evidence used stable source spans; generated findings and causal proposals had separate identities.
- Task-specific contexts replaced routine inclusion of the whole prior board.
- Invalid items could be quarantined while valid independent work survived.
- Questions retained their originating owners, and reviewed answers could be returned to all relevant specialists.
- Storyteller jobs, scenario material, and release history stayed outside the RCA evidence state until an answer batch was explicitly released.
- Later Try 5 revisions added lossless artifact chunks, streamed response preservation, stronger prerequisite handling, and distinct statement-versus-relationship review.
- Claim review evolved from a complex meaning-decomposition candidate to a simpler literal-claim check after the former failed its semantic tests. [L5–L7]

### What improved

The new engine made individual failures and preserved outputs inspectable. Exact original-line citations were retained, and some isolated reviewer controls improved. A later literal-review configuration matched seven frozen semantic regression controls, including the distinction between a blank field and physical absence. This was a limited component result, not a complete RCA pass. [L7]

A controlled board pilot preserved an initial investigation after an added pressure/alarm document. Later progressive scheduling also made an early provisional board visible before all queued work finished. [L8–L9]

### What failed

| Failure area | Observed evidence | Interpretation |
| --- | --- | --- |
| Continuing after foundational failure | An early Try 5 snapshot recorded 116 completed tasks, 102 failed tasks, 1 running and 17 queued, with four proposed nodes and no links. These were snapshot counts, not final stop-time counts. | Local failure tolerance was insufficiently distinguished from a missing prerequisite needed by downstream work. |
| Incomplete initial understanding | In Try 5.2, two reference readers returned no findings because their documents did not describe a failure. | Normal-operation knowledge and reference conventions were being overlooked. |
| Repetitive specialist generation | A Try 5.2.1 equipment-specialist response reached 83,856 raw characters and its output allowance without completing valid JSON. | Removing small output caps alone did not make exploration productive. |
| Incorrect claim assessment | Some reviewers treated blank fields as proof that an attachment was absent, or treated excerpts as a complete inventory. | Source references could be valid while the inference was wrong. |
| Overcomplicated review | An evidence-blind interpreter fragmented ordinary statements and introduced unnecessary ambiguities; a harness rule then suppressed otherwise usable judgments. | Additional reasoning stages introduced their own failure mechanism. This candidate was rejected. |
| Weak progress after new evidence | The controlled board pilot produced no causal links and made little use of the upstream/downstream pressure contrast. | Extra corroboration did not translate into a materially better investigation. |
| Work generation still expanded | A supervised B1 snapshot had 202 proposed findings, 26 questions, and no causal nodes before progressive-board scheduling was applied. | Persistent tasks solved storage/recovery problems, not which work deserved priority. |

Sources: launch and diagnostic receipts, claim-review experiments, and the controlled board comparison. These observations come from different Try 5 revisions and should not be merged into a single fixed-system score. [L6–L9]

The later fresh, disclaimer-cleaned B0+B1 experiment was paused and retained before the Try 6 redesign. Its input preparation removed specified simulation metadata, not factual uncertainties, table values, or hidden-answer boundaries. Counts of findings or queued tasks should not be described as counts of independently instantiated specialist personalities. [L10–L11]

**Assessment:** Try 5 improved execution ownership and the visibility of evidence judgments. It did not yet deliver reliable, efficient causal synthesis. The remaining problem included both semantic accuracy and an investigation policy that generated too much work before establishing a useful position.

## A3. Try 6 — establish the investigation first, then perform targeted work

### What changed

Try 6 changed what generated work and when the board became available:

**Read sources → frame an initial investigation → targeted specialist consultations → grouped evidence resolution/brokerage → refine → review selected premises → verify connections → publish.**

- Original evidence reading became the single producer of source observations. Other roles referenced the notebook instead of repeatedly extracting new layers of findings.
- The frame selected initial board premises, plausible explanations, and concrete evidence directions.
- A tag alone no longer spawned broad specialist work; consultations needed a named branch ambiguity or purpose.
- Only premises selected for the current map and its active connections required review, not every notebook entry.
- Final gaps remained evidence requests for a later version rather than triggering an automatic backward loop of extraction and question generation.
- New or changed passages were read in later versions; earlier versions and original observations remained preserved.
- Subsequent recovery separated node selection from connection generation and allowed invalid individual arrows to be quarantined without discarding a usable frame.
- Application-wide context/output/time quotas were removed from active calls where documented. Native model capacity, available memory, validation, cancellation, and explicit failure states remained. This did not create infinite context. [L11–L13]

### What the reviewed V1 and V2 actually achieved

The latest reviewed experiment used one Qwen model track and the IA-16036 evidence package. V2 added two documents containing physical routing and field valve observations, plus one released storyteller answer. [L14]

| Recorded measure | V1 | V2 |
| --- | ---: | ---: |
| Documents, excluding incident description | 10 | 12 |
| Source-notebook findings | 100 | 154 |
| Board nodes, including focal event | 5 | 9 |
| Active connections | 4 | 6 |
| Verified connections | 0 | 0 |
| Supported non-focal nodes | 1 | 5 |
| Published execution status | Partial; finished | Partial; finished |

V1 was not expected to solve the incident. It should have established accurate known facts, preserved plausible alternatives, and asked for missing information. V2 should have used the newly supplied routing and valve chronology to narrow the physical explanation without claiming more certainty than the records allowed.

### What still failed

1. **New evidence did not sufficiently revise the explanation.** Routing and valve observations were extracted, but the three broad branch descriptions and their gaps remained substantively unchanged.
2. **Existing information was still requested as missing.** The map/resolver did not consistently use the supplied alarm mapping and routing records.
3. **The board contained incorrect relationships or roles.** Opposite temporal arrows coexisted, and a sampled RUN indication was labeled a protective barrier without establishing that function.
4. **An identified error survived publication.** Review noticed the incorrect pressure timestamp, but the board/summary retained it.
5. **Some review and question handoffs were inconsistent.** All four new verifier questions were saved but absent from the normal published answering route. They needed explicit assessment and disposition, not necessarily automatic release.
6. **Review remained expensive.** V2 took 78 minutes 39 seconds; premise-review tasks accounted for about 60.25 minutes, or 76.6%. The record shows review cost, not an unexplained scheduling stall. [L14]

V1 included engineering recovery and a sampling-profile change, so its approximately 152-minute elapsed time is not a clean speed baseline against V2. Zero verified links is not, by itself, proof of a bad preliminary RCA; the specific errors and missed use of available evidence are the substantive findings.

**Assessment:** Try 6 produced preserved, evolving investigation versions and more supported statements. It has not yet demonstrated the central RCA capability we want: reliably integrating new evidence into a better-supported causal explanation and then into appropriate prevention proposals.

## A4. The development trajectory in one view

| Generation | Main design question | Improvement introduced | Main unresolved RCA issue |
| --- | --- | --- | --- |
| Try 4 | Can domain specialists investigate an incident and assemble a causal board? | Specialist workflow, evidence assessment, board verification, action gating | Facts and hypotheses did not consistently become a complete supported mechanism; processing also expanded excessively. |
| Try 5 | Can the investigation survive failures and retain trustworthy, reusable work? | Persistent tasks, provenance, independent failures, refined review responsibilities | Correctness and prioritization remained weak; the ledger could grow faster than useful causal progress. |
| Try 6 | Can an initial investigation guide which work happens next? | Early framing, targeted consultation, selected-premise review, explicit version publication | New evidence did not consistently change the mechanism, resolve stale gaps, or repair published errors. |

This history motivates an improved RCA method. It does not support a claim that every failure was caused by the same defect, that one model is categorically incapable, or that more agents/context alone will solve the problem.

# B. How existing RCA research presents itself

## B1. Scope of this review

This is a targeted positioning review, not a systematic literature review or a claim to have established novelty. It includes the three benchmarks discussed earlier and representative method/analysis papers. The descriptions below summarize the authors' positioning; they are not quotations or independently reproduced results.

Most of the selected computational benchmarks concern cloud or microservice faults. Industrial accident investigations also involve physical mechanisms, people, procedures, organizational conditions, and incomplete historical records. Transfer between these settings must be demonstrated, not assumed.

## B2. Representative papers and their contribution claims

### 1. RCAEval — a benchmark and reproducible comparison framework

**Paper:** *RCAEval: A Benchmark for Root Cause Analysis of Microservice Systems with Telemetry Data*. First preprint: December 2024; revised February 2025. [Primary paper](https://arxiv.org/abs/2412.17015)

**Positioning:** existing RCA methods need a common evaluation basis. The contribution is a dataset/framework rather than a claim to solve all RCA. It supplies 735 failure cases and 15 baseline implementations, using metrics, logs, and traces, with coarse service-level and finer indicator-level evaluation.

**Lesson for our paper:** evaluate subsystem localization separately from the precise condition or mechanism identified. Do not use broad topical relevance as proof of a correct RCA. Its telemetry task is not directly equivalent to our industrial document investigation.

### 2. ITBench — interactive IT automation tasks and measurable outcomes

**Paper:** *ITBench: Evaluating AI Agents across Diverse Real-World IT Automation Tasks*. ICML 2025. [Conference paper](https://proceedings.mlr.press/v267/jha25a.html)

**Positioning:** a framework for reproducible agent evaluation across SRE, compliance/security, and financial operations. The SRE component distinguishes diagnosis, fault propagation, and mitigation; it evaluates agents interacting with operational environments rather than only generating prose.

**Lesson for our paper:** distinguish identifying a cause, explaining how it produced the outcome, proposing an action, and demonstrating action effectiveness. In our current setting, an expert-reviewed recommendation is not proof that a plant intervention prevented recurrence. [SRE method details](https://arxiv.org/html/2502.05352v1#A3)

### 3. Cloud-OpsBench — reproducible, evidence-grounded investigation

**Paper:** *Cloud-OpsBench: A Reproducible Benchmark for Agentic Root Cause Analysis in Cloud Systems*. February 2026 preprint, revised August 2026. [Primary paper](https://arxiv.org/abs/2603.00468)

**Positioning:** accurate final diagnoses do not necessarily reflect justified investigations. The benchmark combines 754 runtime-verified cases, frozen tool-response replay, and diagnostic evidence graphs. It evaluates both outcomes and the evidence established during investigation, allowing alternative valid evidence paths.

**Lesson for our paper:** preserve controlled evidence releases and assess whether the explanation is supported, not just whether it names the expected cause. Expert reference milestones belong in the evaluator, not in the tested agent's answer-bearing input. Its evidence graphs are evaluation annotations, not a complete industrial RCA engine we can directly adopt.

### 4. RCACopilot — an automated diagnosis method for cloud incidents

**Paper:** *Automatic Root Cause Analysis via Large Language Models for Cloud Incidents*. First preprint 2023; EuroSys 2024. [Primary paper](https://arxiv.org/abs/2305.15778), [author-hosted conference version](https://tianyin.github.io/pub/rca-copilot.pdf)

**Positioning:** an on-call diagnosis system that routes alerts to incident handlers, gathers diagnostic information, predicts a root-cause category, and generates an explanation. Evaluation uses a year of Microsoft incident data.

**Lesson for our paper:** demonstrate the value of the investigation procedure, not just the interface. Our proposed scope includes progressive document-based physical and organizational explanations, which is different from predicting an operational incident category; that difference must be tested rather than advertised as automatic superiority.

### 5. Graph Traversal Agent — an auditable, graph-guided RCA method

**Paper:** *Auditable Graph-Guided Root Cause Analysis for Kubernetes Incidents*. June 2026 preprint. [Primary paper](https://arxiv.org/abs/2606.08590)

**Positioning:** combine LLM judgments with a typed evidence graph, deterministic traversal/tool operations, and a separate validation stage. The authors explicitly audit scenario-specific shortcuts and restrict their claims to the evaluated ITBench snapshots; some gains remain benchmark-coupled.

**Lesson for our paper:** graphs and validation already exist in RCA research. Our claim must identify what our investigation method adds and survive tests without case-specific hints. A graph's internal consistency does not establish the truth of its causal interpretation.

### 6. Beyond Fault Localization / DiagGuard — process analysis plus a targeted method

**Paper:** *Beyond Fault Localization: A Trajectory-Level Study of LLM Agents for Microservice Root Cause Analysis*. August 2026 preprint. [Primary paper](https://arxiv.org/abs/2608.21310)

**Positioning:** study RCA as an observable diagnostic process, not only a final service prediction. The work analyzes 3,500 trajectories against annotated propagation paths, identifies evidence-handling failures, and proposes grounding followed by verification through DiagGuard.

**Lesson for our paper:** this is close prior work for the alternative analysis direction. Simply reporting omitted evidence or unsupported inference is unlikely to be a sufficient distinguishing contribution. Progressive industrial evidence and the quality of version-to-version causal revision are possible comparison dimensions, not established novelty claims.

### 7. Industrial accident-report extraction and causal-chain reconstruction

**Paper:** *Large language model-driven information extraction and causal chain reasoning from chemical accident investigation reports for process safety intelligence*. 2026 publisher record. [Publisher page](https://www.sciencedirect.com/science/article/pii/S0950423026001907), [DOI](https://doi.org/10.1016/j.jlp.2026.106101)

**Positioning:** extract entities and causal relationships from chemical accident reports, then assemble hierarchical causal graphs. The publisher abstract describes a 126-report annotated benchmark, direct and contributing causes, organizational deficiencies, and confidence-based expert review.

**Lesson for our paper:** industrial causal-graph extraction is not an untouched area. A potential distinction is investigating incomplete evidence through questions and successive releases, rather than reconstructing causation already documented in a completed report.

**Access limitation:** this entry is based on publisher-indexed abstract/introduction text. Direct full-page access returned HTTP 403; the full methods, data availability, and evaluation must be checked before making a detailed novelty claim against it.

### 8. Adjacent work: general multi-agent failure analysis

**Paper:** *Why Do Multi-Agent LLM Systems Fail?* 2025. [Primary paper](https://arxiv.org/abs/2503.13657)

**Positioning:** an empirical investigation of failure modes in multi-agent LLM systems. It is not an industrial RCA benchmark.

**Lesson for our paper:** generic agent failure analysis is already a research topic. The alternative proposal would need an RCA-specific task and evidence, not merely a new catalogue of application errors.

## B3. What the literature means for our positioning

The selected papers support several distinct contribution types:

| Paper type | Main object of contribution | What readers expect to see |
| --- | --- | --- |
| Benchmark/resource | Cases, environment, annotations, evaluation protocol | Validity, reproducibility, useful coverage, and meaningful baseline results |
| RCA method | A procedure that improves diagnosis or explanation | Comparisons, justified design choices, causal/evidence quality, and limitations |
| Industrial knowledge extraction | Structured facts and causal relationships from reports | Annotation quality, extraction/graph accuracy, and expert assessment |
| Diagnostic-process study | Understanding when and how investigations succeed or fail | Controlled comparisons, attributable findings, and generalizable insight |

**Our proposed distinction, still to validate:** an industrial RCA investigation that begins with incomplete records, asks for discriminating evidence, revises competing mechanisms, and connects supported causes to prevention proposals. “Multi-agent,” “evidence-grounded,” and “causal graph” alone are not sufficient novelty claims.

The three benchmarks have been identified and their relevant methods reviewed; they have **not** been downloaded, adapted, or run through our application. Any future adapted industrial evaluation must be described separately from the benchmarks' original tasks and leaderboards.

# C. Two proposed paper directions for discussion

## C1. Option 1 — an RCA-method paper: the currently preferred direction

### Working title

**Evidence-Grounded Interactive Root Cause Analysis for Industrial Incidents**

### Central research question

Can an evidence-driven investigation procedure turn incomplete incident accounts and progressively supplied records into accurate, qualified causal explanations and useful prevention proposals?

### How the paper would present itself

An RCA methodology and its evaluation—not a dashboard paper and not a claim that software reliability alone produces correct RCA. The agents implement complementary investigation responsibilities; the contribution is how evidence, questions, alternatives, and causal judgments work together.

“RCA as a whole” is the target workflow, not permission to infer a complete root cause from insufficient records. The method must identify when the physical explanation is established but an organizational cause remains unresolved, and when even the physical mechanism is still uncertain.

### Proposed investigation method

1. **Establish context.** Identify equipment, people, terminology, locations, normal function, and incident configuration. Do not invent equipment design from component names.
2. **Build source-backed observations.** Preserve entities, actions/states, timing, measurements, documentary requirements, and uncertainty separately from causal interpretations.
3. **Develop competing mechanisms.** Specialists explore plausible directions; the causal process integrates them into explanations rather than treating every tag as a cause.
4. **Define what each mechanism needs.** Identify required facts, available support, contrary observations, and unresolved assumptions. These are generated from evidence and domain knowledge, not copied from the hidden evaluation answer.
5. **Acquire discriminating evidence.** The broker preserves ownership when merging equivalent questions. The answering process searches existing knowledge before requesting genuinely unavailable information.
6. **Revise explicitly.** New evidence may strengthen, weaken, replace, or leave an explanation unchanged. The board, summary, and outstanding questions must reflect the same revision.
7. **Establish causal relationships.** Distinguish physical connections, chronology, source reports, possible mechanisms, and supported causal contributions. Preserve interacting causes and valid alternatives.
8. **Develop prevention proposals.** Tie each proposed action to a supported causal or barrier finding, identify its intended effect, and specify how effectiveness would be assessed. Expert approval and real implementation remain separate.

This is a proposed method to implement and test. The Try 6 findings show that several of these responsibilities are not yet reliably achieved.

### Proposed contributions

- **Investigation method:** a general evidence-driven progression from initial account to qualified causal explanation and cause-linked prevention proposals.
- **Progressive industrial evaluation:** expert-reviewed cases with initial records, subsequent evidence releases, alternative admissible explanations, and stage-specific uncertainty boundaries.
- **Empirical assessment:** whether the method improves RCA quality and investigator usefulness over simpler approaches, and which elements contribute to that improvement.

Any contribution claim must be supported by completed work. A resource contribution also requires a credible sharing/reproducibility arrangement; private partner records do not automatically become a public benchmark.

### Experiments needed

- Compare a direct document-to-RCA baseline, a single-agent iterative investigation, and the proposed specialist-based method.
- Keep evidence access and model identity controlled. Report resource-matched comparisons or quality/cost curves so additional calls are not mistaken for an architectural benefit.
- Start with fixed evidence batches and no autonomous storyteller. This isolates causal investigation from answer-generation reliability.
- Then test question-driven acquisition against the same frozen scenario record. Explicitly mark requests that the scenario cannot answer.
- Evaluate additional models independently, without combinations or fallbacks, and include repeated runs where variability matters.
- Use domain experts to assess source fidelity, causal adequacy, remaining uncertainty, and action relevance. Avoid exact graph matching as the only criterion when several explanations are valid.
- Ablate concrete method components, such as explicit evidence requirements and post-review reconciliation. Do not use a knowingly broken implementation as the only baseline.

### What to measure

| RCA capability | Evaluation question |
| --- | --- |
| Incident reconstruction | Are entities, states, chronology, and measurements faithful to the supplied records? |
| Mechanism identification | Does the explanation identify how the outcome occurred, with appropriate scope? |
| Causal support | Are proposed connections justified by evidence rather than temporal association or repeated assertions? |
| Alternative explanations | Are competing mechanisms investigated and retained or ruled out for stated evidential reasons? |
| Question usefulness | Does a request target a material uncertainty, avoid already answered facts, and distinguish plausible explanations? |
| Progressive revision | Does new evidence produce the appropriate changes while preserving still-valid conclusions? |
| Prevention relevance | Do proposed actions address supported causes/barriers, with plausible effectiveness checks? |
| Expert utility and effort | Does the output help qualified investigators, and at what time, token, and review cost? |

Report these dimensions separately rather than relying only on one 100-point aggregate. Do not penalize V1 for causes that become inferable only after later evidence. Proposed actions can be evaluated for relevance, but reduced recurrence cannot be claimed without outcome evidence.

### Suggested paper structure

1. Introduction: the industrial RCA problem and the limits of incomplete evidence.
2. Related work: automated diagnosis, industrial causal extraction, and interactive investigation.
3. Task definition: evidence releases, hypotheses, causal support, questions, and closure boundaries.
4. Proposed RCA method and the role of each component.
5. Data, expert annotation, baselines, and evaluation protocol.
6. Results: reconstruction, causal explanation, revision, and prevention relevance.
7. Ablations and representative investigations.
8. Limitations, human oversight, privacy, and conclusion.

### Current readiness and main risk

We have a prototype, preserved investigations, source packages, and concrete acceptance targets. We do **not** yet have a reliable full-RCA result across held-out cases, expert-validated comparative results, or demonstrated benefit from the proposed changes.

The primary risk is an overly broad claim: many features can be implemented without demonstrating that the system performs better RCA. The paper needs a clearly specified method, suitable cases, and substantive causal results—not merely successful execution.

## C2. Option 2 — an evaluation/process-analysis paper: retained as an alternative

### Working title

**From Evidence to Explanation: Evaluating Causal Revision in Multi-Agent Incident Investigation**

### Central research question

When new incident evidence arrives, do single- and multi-agent systems use it to revise causal explanations correctly, and where do evidence interpretation, coordination, and revision succeed or fail?

### How the paper would present itself

A controlled empirical study of RCA behavior. It would not begin with the conclusion that models fail, and it would not present our development bugs as general model limitations. Positive and negative outcomes would both be reported. ARR explicitly permits substantive negative-result and analysis contributions. [ARR contribution guidance](https://aclrollingreview.org/cfp)

### Proposed contributions

- A staged, source-grounded evaluation protocol for causal investigation and revision.
- A reproducible analysis distinguishing acquisition, interpretation, synthesis, review, and publication outcomes.
- If supported by experiments, a targeted method that improves the measured RCA behavior.

The general multi-agent failure topic and RCA trajectory analysis already have close prior work in Section B. The distinctive task and findings would need to be demonstrated; they cannot be assumed from the industrial setting alone.

### Controlled study design

1. Prepare expert-reviewed incident packages with stage-specific expectations before testing.
2. Compare a single agent and a repaired multi-agent implementation using the same model and evidence.
3. Release supporting, contradicting, qualifying, and irrelevant evidence in controlled conditions.
4. Measure what should change, what should remain stable, and whether questions target the remaining uncertainty.
5. Use selected diagnostic interventions: supply the exact relevant source bundle, remove a coordination handoff, or bypass a flawed retrieval boundary. These are evaluator experiments, not evidence secretly supplied in the main comparison.
6. Attribute results only to the boundary actually tested. If a correct review is not applied, that is a workflow failure; if a displayed answer differs from the committed answer, that is an implementation failure; neither proves that the model misunderstood the source.
7. Repeat on additional incidents and models, including successful cases. Freeze the tested configuration rather than silently repairing it mid-comparison.

### Suggested paper structure

1. Motivation: reliable evidence-to-explanation revision is an RCA requirement.
2. Related work and a precise statement of the evaluation gap.
3. Task, cases, release protocol, and expert expectations.
4. Compared systems and controlled execution conditions.
5. Results: causal accuracy, evidence use, revision, and investigation effort.
6. Diagnostic interventions and attributable failure mechanisms.
7. Targeted improvement and ablations, if validated.
8. Limitations and implications for RCA systems.

### Current readiness and main risk

Our traces provide useful pilot examples but not yet a controlled cross-model study. Known routing/status defects must be repaired or explicitly isolated, and the extensively debugged cases cannot serve as untouched held-out tests.

The main risk is confusing a case-specific software postmortem with a general scientific result. This option is not automatically easier or more publishable than the method paper. Negative results require the same care in task validity, comparison, and claim scope.

## C3. Comparing the two options

| Dimension | Option 1: RCA method | Option 2: RCA behavior study |
| --- | --- | --- |
| Main question | How should the system conduct a defensible industrial RCA? | How reliably do different agent arrangements conduct and revise RCA? |
| Central contribution | Investigation methodology and demonstrated RCA benefit | Controlled evaluation, attributable findings, possibly a targeted repair |
| Role of multiple agents | An implementation choice whose value must be established | One experimental factor, compared with simpler alternatives |
| Main results | Better-supported mechanisms, useful questions, appropriate revisions, cause-linked actions | Measured strengths/failures in those same RCA capabilities |
| Software defects | Background engineering to correct | Confounds to remove or separately identify—not the core scientific claim |
| Need for expert case evaluation | Essential | Essential |
| Current project preference | Preferred | Previously dropped; included for professor feedback |

The options share much of the data and evaluation work, but one paper should have a clear primary contribution. We should not market an unfinished method as a successful system, or rebrand every implementation problem as a model finding.

## C4. Work needed whichever direction is chosen

1. **Establish the evidence base.** Inventory which incidents have source records, partner RCA conclusions, and permission for research/release. Historical summaries alone do not supply a complete investigation ground truth.
2. **Separate data types.** Distinguish original records, partner-derived reconstructions, and historically anchored synthetic cases. The IA-16036 package is a controlled reconstruction, not recovered original field documentation. [L15]
3. **Reserve development and evaluation cases.** R3 and IA-16036 have informed extensive development. Use them as development/pilot cases; do not call them untouched held-out tests. Split by incident family to reduce near-duplicate leakage.
4. **Obtain independent expert judgment.** Where feasible, use two reviewers and adjudicate disagreements. Partner conclusions are important evidence, but supplied records may not uniquely justify every reported causal link.
5. **Keep evaluator knowledge separate.** Hidden causes, expected changes, and final RCA documents must not leak through prompts, filenames, source metadata, or storyteller replies.
6. **Freeze comparisons.** Record model digest, prompts, implementation, evidence, releases, and resource use. Existing recovery runs remain disclosed pilot evidence.
7. **Choose case count and repetitions from the evaluation design.** Use pilot variability, annotation capacity, and the intended claim to set a justified sample size; avoid treating many nodes from one incident as independent cases.
8. **Support a language-research contribution.** Explain the challenge in cross-document interpretation, evidence-seeking dialogue, and causal explanation—not just the use of an LLM in an industrial app.
9. **Test proposed improvements before claiming them.** The earlier repair plan remains proposed work, not a proven solution documented by the present results.

## C5. Questions to take to the professor

- Should the primary contribution be a new industrial RCA methodology, or a controlled investigation of RCA capability and revision?
- What scope of RCA is feasible for the first paper: physical mechanism, broader contributing conditions, or also expert-reviewed prevention proposals?
- Which partner incidents have sufficient original evidence and expert availability for defensible evaluation?
- Can reconstructed/synthetic cases be included as a separate experimental tier, and what validation would be required?
- What is the most credible distinguishing contribution relative to interactive cloud RCA and industrial report-to-graph extraction?
- What minimum experimental result would justify moving from a prototype description to the chosen paper claim?

**Recommended starting position for the meeting:** pursue Option 1 as the main objective, while asking whether Option 2 offers a stronger first contribution given the available evidence and expert support. Do not choose the framing merely because some development runs failed.

---

## Local evidence index for Section A

These links point to preserved project records. They support the development history, not independent peer-reviewed validation of the application.

- **L1 — Try 4 design:** [Try 4 README](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/README.md>).
- **L2 — Early Try 4 R3 result:** [Qwen synthetic-packet scorecard](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/evals/r3-qwen-try4-results.md>).
- **L3 — Separate ground-truth-derived R3 result:** [Qwen scorecard](</Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package/06_run_records/try4-ground-truth-benchmark-2026-09-08-qwen-only-v2/qwen3.5_latest/scorecard.md>).
- **L4 — Later Try 4 failures and redesign rationale:** [September 18 cross-run review](</Users/dhwanilchauhan/Desktop/RCA Try 1/RCA_SYSTEM_REVIEW_2026-09-18.md>); [Try 4 repair chronology](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4/REPAIR_NOTES.md>).
- **L5 — Try 5 implementation:** [Delivery record](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/docs/try5-implementation.md>); [Try 5.2 changes](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/docs/engine-try5.2.md>).
- **L6 — Try 5 live launch/stop records:** [Try 5.1](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/ia16036-2026-09-18-launch.md>); [Try 5.2](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/ia16036-try5.2-launch.md>); [Try 5.2.1](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/ia16036-try5.2.1-launch.md>).
- **L7 — Claim-review diagnostics:** [Rejected meaning-decomposition candidate](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/fixed-meaning-results.md>); [literal-review results and limitations](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/literal-review-results.md>).
- **L8 — Controlled board comparison:** [Pilot summary](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/board-comparison-summary.md>).
- **L9 — Work growth and progressive-board intervention:** [Supervised B1 run](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/supervised-b1-run.md>).
- **L10 — Fresh cleaned-input Try 5 test:** [Case-content-only V1 receipt](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 5/evals/try5/case-content-b1-run.md>).
- **L11 — Try 6 strategy and preservation of the paused Try 5 run:** [Implementation record](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/docs/try6-implementation.md>).
- **L12 — Capacity changes and remaining physical boundaries:** [Try 6 capacity policy](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/docs/try6-capacity-policy.md>).
- **L13 — Try 6 V1 recovery and its limitations:** [Frame/connection recovery receipt](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v1-frame-recovery.md>).
- **L14 — Audited V1 and V1-to-V2 outcomes:** [Detailed evidence review](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/v1-v2-presentation-review/output/Try6_V1_V2_Evidence_Review.md>); [frozen diagnostic export](</Users/dhwanilchauhan/Desktop/RCA Try 1/Try 6/evals/ia16036-v2-controlled/failure-report-evidence.json>).
- **L15 — Controlled package provenance:** [IA-16036 package description](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/README.md>); [prepared input-view description](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/07_case_content_inputs/README.md>).

## Document status

This is a discussion brief, not a submitted paper, a systematic review, or a completed experimental result. No application code, evidence package, stored model output, or historical score was changed to create it. Research links were checked on 20 September 2026; preprints and the industrial-paper access limitation are identified above.

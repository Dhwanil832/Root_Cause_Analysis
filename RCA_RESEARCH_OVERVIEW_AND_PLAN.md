# Industrial RCA research: what we are building and how we will test it

Prepared: 21 September 2026  
Audience: someone new to the project, its application, and root cause analysis

> **In one sentence:** We are investigating whether an AI-assisted system can understand an industrial incident, seek useful evidence, build a justified explanation of how it happened, and revise that explanation as new information arrives.

This document explains the research objective, proposed investigation process, development history, evidence-generation plan, and evaluation strategy. It is not a claim that we have already built a reliable autonomous investigator. **Try 7 is presented here as the proposed research design to validate, not as a demonstrated solution.** Implementation progress and remaining acceptance work are tracked separately.

## 1. What is root cause analysis?

Root cause analysis, or RCA, investigates how and why an incident occurred so that meaningful preventive changes can be identified.

For example, “a beam fell” describes an event. “Gravity caused it” is physically relevant but does not explain why the beam lost its support at that moment. An investigation needs to establish the equipment arrangement, what changed, which conditions allowed the change to matter, and whether relevant protective measures worked as intended.

An incident can have several interacting causes. A useful RCA should not stop at a broad label such as equipment failure, poor communication, or operator error. It should explain the specific mechanism and the conditions behind it, with evidence.

The distinction matters for prevention. A recommendation cannot be justified merely because it sounds sensible; it should address something the investigation actually established.

## 2. What problem are we trying to solve?

Industrial investigations rarely begin with a complete, consistent account. Information is spread across incident descriptions, operating logs, drawings, maintenance records, procedures, measurements, photographs, and witness accounts.

The investigator must work out:

- What the equipment and surrounding system actually do.
- What happened, in what sequence, and under which operating conditions.
- Which facts are established and which statements are interpretations.
- Which explanations fit the evidence and which remain possible.
- What additional information would distinguish those explanations.
- How the explanation should change when new evidence appears.

Our research asks whether an AI-assisted workflow can perform these connected activities usefully and transparently. Producing a plausible final paragraph is not enough.

The difficult part is not just finding relevant words in documents. It is combining their meanings correctly. A drawing may establish that two components are connected, but not that a valve between them was open during the incident. A blank inspection field does not establish that the physical inspection never happened.

## 3. What do we want to achieve?

We want a system that can maintain an evolving, evidence-grounded investigation.

Its working output should contain:

- An understandable account of the incident, equipment, people, locations, and sequence.
- Plausible explanations, including their assumptions and unresolved conditions.
- A causal board showing relevant events, conditions, and proposed relationships.
- Questions that address concrete information gaps.
- Traceable evidence for statements and connections.
- A clear record of what changed after each evidence release and why.
- Prevention-oriented findings and corrective-action proposals when the evidence warrants them.

We do **not** expect a complete RCA on the first pass. A good initial investigation may identify two plausible mechanisms and ask for the particular record that would distinguish them.

We also do not want a system that keeps generating questions indefinitely. The aim is useful investigation progress, not the largest question list, the most agents, or the biggest diagram.

### The central research question

**Can a progressive, evidence-driven investigation workflow produce better-supported industrial causal explanations and better revisions than simpler ways of analyzing the same evidence?**

Supporting questions include whether the system asks useful questions, combines information across documents, handles contradictions, and avoids becoming more confident than its evidence allows.

## 4. What information do we currently have?

We have historical incident records from the industry partner, supporting investigation-method literature, examples of industrial documents, and some more detailed material for the R3 beam incident.

These resources serve different purposes:

| Resource | What we use it for | What it does not establish |
| --- | --- | --- |
| Historical incident rows | Anchor the incident type, activity, reported event, consequences, and recorded investigation findings. | A complete equipment model, evidence trail, or verified explanation of every intermediate step. |
| Investigation guides and training material | Understand how an industrial investigation should be structured. | Facts about a particular incident. |
| Partner document examples | Learn the structure and level of detail of realistic forms, logs, and supporting records. | That the example's equipment, requirements, or recorded actions apply to our case. |
| Case-specific evidence, where available | Establish facts about the particular event, within each source's limits. | That every statement is complete or every recorded conclusion is correct. |
| Constructed test documents | Create controlled investigation tasks where evidence can be released in stages. | New authentic records of what historically happened. |

This is an important limitation: a spreadsheet row may name a recorded root causal factor without supplying the documents that justify it. We cannot honestly evaluate a detailed historical reconstruction as though those missing records existed.

Our solution is to build **historically anchored synthetic investigation packages**, while keeping historical facts and constructed details distinguishable in the private research record.

## 5. How the proposed system works: one investigation from start to finish

### Step 1 — We provide the incident description and starting documents

The user supplies the initial account and chooses a model. Documents enter through three distinct channels:

1. **Default references:** applicable background material, such as a plant layout or equipment handbook.
2. **Starter documents:** evidence provided with this particular incident.
3. **Later answer documents:** material supplied in response to an investigation request or as a controlled evidence update.

Each document retains its source identity, revision, scope, and the point at which it became available. The three categories remain separately preserved.

The application's document-processing layer makes the supplied material usable for investigation and records extraction problems. A document being uploaded does not automatically mean its relevant contents reached the model.

### Step 2 — The system establishes its understanding

The system identifies the event, entities, component names, relevant locations, operating configuration, and initial sequence.

If it does not know what a particular beam or yoke does, it should ask or consult applicable documentation. General model knowledge can suggest a useful question; it cannot prove the design of that specific machine.

Baseline questions help establish this understanding. Missing answers should remain visible, but independent investigation work can continue where the missing information is not essential.

### Step 3 — It tags the incident and selects relevant expertise

Tags identify which investigative perspectives are relevant. Examples include equipment, electrical systems, stored energy, work environment, maintenance, isolation, and communication.

The broader specialist pool also covers human involvement, vehicles, crane/lifting work, process/material involvement, planning, rail equipment, wildlife, and unfamiliar incident types.

A tag is **not a cause**. Selecting “human involvement” does not blame a person. Selecting “isolation” does not establish an isolation failure.

The tag pool is predefined; the specialists consulted for an incident are selected dynamically.

### Step 4 — Specialists explore relevant uncertainties

Each selected specialist investigates its area and keeps a domain-specific knowledge base within that model's investigation.

Specialists receive example kickoff questions to demonstrate useful directions. Those examples are not a mandatory questionnaire or an exhaustive script.

The proposed improvement is to give consultations a concrete purpose: an unexplained observation, a possible mechanism, an uncertain component function, or a condition that needs checking. A tag should not automatically trigger unlimited broad questioning.

Separate specialist knowledge bases allow different perspectives to notice different things. Some overlap is expected. However, two agents repeating a statement from the same source do not create two independent pieces of evidence.

### Step 5 — The question broker organizes the proposed questions

The broker comes **after questions have been generated**.

It identifies genuinely overlapping requests and combines them where appropriate, while retaining:

- Who asked each question.
- The equipment, time, location, and operating state being asked about.
- Why each specialist needs the answer.
- The separate parts that require answers.

For example, two specialists may both need a valve log, but one needs the recorded position while the other needs the time and sequence of operations. Obtaining the position does not answer both requests completely.

### Step 6 — A common answer-fetching function searches available knowledge

The answer-fetching function can search across the specialist knowledge bases and released documents **within that model's track**.

It should return a supported answer with source references, a partial answer, an unresolved conflict, or a clear account of what could not be found. If the available material is insufficient, the request goes to the user or the controlled answering process used in experiments.

The workflow is:

**Questions → broker → answer fetching → broker → every relevant specialist and explanation.**

The broker must actually deliver updates to the affected recipients. Merely saving a list of their names is insufficient.

This is a shared responsibility, not a requirement to create a permanent agent for every question. Answering work can be scheduled as needed.

### Step 7 — Causal analysis builds and compares explanations

The causal-analysis role uses the available knowledge to explain how the event could have occurred. It may also generate questions, which enter the same broker and answer-fetching process.

Each explanation should identify:

- The outcome or transition it explains.
- The proposed mechanism.
- Conditions that must be true for that mechanism to work.
- Supporting evidence and evidence that challenges it.
- Assumptions that have not been established.
- An observation that could distinguish it from alternatives.

This is the intended center of the investigation: **testable explanations, rather than an expanding collection of isolated claims and questions**.

Explanations can involve conditions acting together. The system should not assume that only one cause can be correct.

### Step 8 — It checks three different things separately

Before presenting a causal explanation, the system must distinguish:

1. **Factual support:** does the evidence establish the statement?
2. **Causal role:** is the statement actually an event, condition, protective measure, or merely background information?
3. **Connection validity:** does the evidence justify the proposed relationship between statements?

For example, “the motor-running indication was on” may be a supported observation. That does not automatically make the indication a protective barrier. Nor does it prove that the motor supplied adequate pressure throughout the event.

Likewise, two supported statements do not automatically form a supported causal connection.

### Step 9 — It publishes a useful first version

The system preserves V1: its current understanding, explanations, board, source references, questions, uncertainties, and execution limitations.

The board is an investigation aid, not an automatic declaration of truth. Proposed and unresolved content should remain visibly distinct from established findings.

A local failure should not discard useful independent work. Conversely, if a failed step supplied a necessary foundation, downstream conclusions cannot be treated as valid simply because the application kept running.

### Step 10 — New evidence produces a revised version

When a new answer or document arrives, the system identifies what it affects. It may strengthen an explanation, weaken it, correct a statement, withdraw a connection, reopen a question, or leave an item unchanged for a stated reason.

It then publishes V2 without overwriting V1. Later evidence may produce V3 and subsequent versions.

**Progress means a justified change in understanding—not merely new wording, more nodes, or greater confidence.** Sometimes the correct update is to become less certain.

## 6. A simple example of the progress we want

Consider a constructed case involving a loss of instrument-air pressure.

**Initial evidence:** the receiving area reports low pressure, and an alarm appears. At this stage, a supply problem, a distribution problem, or a measurement problem may remain plausible. A useful V1 should identify the uncertainty rather than select a final cause prematurely.

**Next evidence:** pressure records show different behavior at two measurement points. The system should ask where those points are located and what lies between them. The readings alone may not establish that relationship.

**Further evidence:** a routing record establishes the measurement locations, and an operations log records relevant actions. The system should now combine the topology, readings, and timing to assess which explanations fit.

Even then, an action occurring near an event does not automatically prove causation. Uncertain instrument accuracy or an incomplete action sequence may remain material gaps.

This tests cross-document understanding: the explanation depends on relationships among records, not on copying an answer sentence from one document.

The example illustrates the intended behavior. It is not a claim that an existing run successfully demonstrated every step.

## 7. What are the agents, and what does the application do?

An “agent” here means a model-assisted role with a defined responsibility. It does not necessarily mean a separate model, permanent process, or independent personality.

| Responsibility | Purpose |
| --- | --- |
| Incident understanding and framing | Establish the system, event, entities, configuration, and initial investigative position. |
| Tagging and specialist selection | Identify which kinds of expertise are relevant. |
| Domain specialists | Explore scoped uncertainties from different technical and operational perspectives. |
| Question broker | Preserve question intent, merge compatible requests, and route answers back. |
| Answer fetching | Find supported answers across released knowledge and identify missing or conflicting information. |
| Causal analysis | Develop and revise explanations and proposed board connections. |
| Review | Assess factual support, roles, and relationships without treating another model call as infallible. |
| Optional storyteller | Prepare controlled simulated answers for experiments; not investigate or grade the case. |

The application handles storage, source identity, scheduling, input delivery, version history, routing, and display. This supporting software is often called the **harness**.

The investigator remains responsible for interpretation. Correctly formatted output does not establish correct reasoning. Likewise, a software failure to deliver evidence should not be blamed on the model's reasoning.

## 8. Why have we built several application versions?

**Try 4, Try 5, and Try 6 are application generations. V1, V2, and V3 are investigation versions inside one model's run.**

| Generation | What we explored | What the saved work showed | Direction of the next change |
| --- | --- | --- | --- |
| Try 4 | A specialist-led evidence and questioning pipeline that generated causal boards. | Useful investigative material and visible boards, but incomplete causal integration. Later runs accumulated large shared inputs and excessive candidate-link work; some encountered truncation or context-related blocking. | Move to smaller, persistent tasks with explicit inputs and recoverable outputs. |
| Try 5 | A durable task engine, source-bound evidence, local failure handling, and a separately operated storyteller. | Better recovery and inspectability, but the amount of work could still grow before a useful investigation finished. The controlled before/after pilot retained two nodes and no causal connections. | Establish an initial investigation position early, then focus subsequent work on its important uncertainties. |
| Try 6 | Early framing, targeted consultations, selected-premise review, and publication of partial investigations. | Published V1 and V2, but evidence updates did not consistently revise the mechanism. Reviews identified errors that remained in board wording, some questions stayed stale, and causal roles/directions were sometimes inappropriate. | Make evidence impact, answer coverage, revision application, and separate factual/causal assessment explicit. |
| Try 7 — proposed research design | An explanation-centered investigation with traceable evidence updates and controlled evaluation. | Not yet established as a reliable improvement by a completed comparative evaluation. | Validate the relevant execution paths and then test whether the changes improve RCA behavior. |

These were development experiments with changing configurations and evidence. They are not a fair, controlled ranking of application generations.

The saved board comparisons make the outputs inspectable. Try 4 has a genuine R3 V1/V2 pair; Try 6 has a published partial IA-16036 V1/V2 pair. Try 5's comparison uses explicitly labeled diagnostic snapshots, not a completed application V1/V2 sequence.

## 9. What changes are we proposing for Try 7?

In the order they matter to an investigation:

1. Preserve the initial inputs and isolate each model's evidence, knowledge, and versions.
2. Establish incident-specific equipment and operating context before assuming a mechanism.
3. Organize investigation around explanations with conditions, assumptions, and distinguishing evidence.
4. Bring related original evidence together, including relevant definitions, topology, qualifications, and contrary observations.
5. Direct specialist work toward meaningful uncertainties while allowing justified new directions.
6. Merge questions without losing their different purposes or unanswered parts.
7. Return partial and revised answers to all affected specialists and explanations.
8. Identify the effect of new evidence on existing statements, assumptions, and connections.
9. Apply source-backed corrections and reassess conclusions that depended on the old statements.
10. Review factual support, causal roles, and causal connections separately.
11. Publish useful partial results with visible unresolved work and a genuine before/after record.
12. Preserve controlled releases and complete experiment records so results can be assessed fairly.

We do not propose fixed question quotas as the main solution to workload growth. Questions should earn priority through their investigative purpose, and unchanged requests should not create endless duplicate work. Native model capacity and execution failures still need honest handling; removing an application limit does not create unlimited model context.

## 10. How existing work informs this design

We are not claiming that hypothesis testing, barrier analysis, or multi-agent RCA are new inventions.

The research review identifies several ideas to adapt and test:

- **AgentRCA:** explicit comparison and updating of candidate explanations. We do not assume access to its kind of digital twin or a fixed fault catalog.
- **MA-RCA:** separation between proposing an explanation, collecting supporting information, and validating it. Historical similarity is a lead, not proof about the current incident.
- **DiagGuard:** attention to grounding and verification around diagnosis. An internal reviewer must itself remain accountable to original evidence.
- **Cloud-OpsBench:** controlled evidence availability and evaluation of intermediate investigative achievements, not only the final answer.
- **RCAEval and ITBench:** reproducible tasks, meaningful baselines, and clearly defined outcomes. Finding a faulty component is not equivalent to completing an industrial accident investigation.

Industrial investigation guidance remains important for the actual task: reconstruct events and conditions, investigate interacting causes, examine relevant controls, and connect preventive recommendations to established contributors.

These are proposed adaptations, not evidence that a method will transfer unchanged to our setting. Detailed paper links, source-specific explanations, and transfer limitations are preserved in the [research proposal](RCA_MECHANISM_REDESIGN_PROPOSAL.md).

## 11. How we will create the synthetic evidence packages

We start with a historical incident row, not an unrestricted fictional story.

For each selected incident:

1. Extract the reported event, activity, consequence, and recorded findings. Identify missing information and conflicting fields.
2. Remove unnecessary personal information and distinguish reported observations from recorded causal interpretations.
3. Construct a fixed, plausible scenario that fills the gaps needed for a controlled experiment. Record which details are historical and which are synthetic.
4. Create realistic documents using the partner examples for format—not as a source of case facts.
5. Distribute useful information across records so that important conclusions require understanding their relationships.
6. Define the initial package and later releases before running the investigator.
7. Write private expectations for what each release should establish, challenge, or leave unresolved.
8. Check consistency, technical plausibility, release fairness, and information leakage. State what has not been independently validated.

An illustrative release sequence is:

- **B0 → V1:** incident description, applicable default references, and starter records. Enough for a useful initial position, not necessarily a final cause.
- **B1 → V2:** a targeted answer or document that resolves an important relationship or challenges a preliminary explanation.
- **B2 → V3:** additional evidence that tests remaining uncertainty, including whether the model revises an earlier belief appropriately.

We set **evidential expectations**, not a mandatory sentence or graph layout. Alternative explanations and equivalent formulations must be accepted when the supplied evidence supports them.

Misleading material may include a plausible but unconfirmed report, a superseded record, or a document with limited scope. The investigator must have a fair basis for recognizing its limitations. We should not manufacture arbitrary contradictions and then penalize the model for failing to resolve an impossible case.

The package's private scenario, expected outcomes, future releases, and answer key must remain inaccessible to the investigator. A filename saying “private” is not sufficient isolation.

The full generation instructions are in [the synthetic-package guide](Try%207/SYNTHETIC_EVIDENCE_PACKAGE_GENERATION_GUIDE.md).

## 12. What role does the storyteller play?

The optional storyteller simulates an information source during testing. It is not allowed to invent a changing world merely to answer whatever question appears next.

It works from the fixed scenario and approved answer material, with memory of what has already been released. It must preserve uncertainty, partial answers, and source limitations.

We separate its work from RCA execution:

**RCA produces V1 and requests → RCA stops → answering process prepares a batch → batch is checked and explicitly released → RCA produces V2.**

This separation lets us test the answering system and the investigator independently. If an answer is incorrect, we need to know whether the investigator misused valid evidence or the answering process supplied bad evidence.

For the first clean comparisons, fixed document releases can remove storyteller variability altogether. Storyteller experiments can then test an additional capability without obscuring the basic RCA result.

## 13. How will we evaluate performance?

Evaluation must ask whether the system established the right relationships **from evidence available at that stage**.

For each case and release, we prepare private assessment targets covering:

| Dimension | What we inspect |
| --- | --- |
| System understanding | Correct entities, functions, locations, operating state, and relevant sequence. |
| Evidence integration | Correct use of related information across records, including qualifications. |
| Information needs | Whether a question seeks information that can resolve a meaningful uncertainty. |
| Factual support | Whether a statement is established at the scope and certainty claimed. |
| Causal explanation | Whether the mechanism and connections are justified, rather than merely associated. |
| Revision | Whether new evidence changes affected statements and relationships appropriately without losing still-valid work. |
| Uncertainty | Whether unknowns, partial answers, and contradictions remain accurately represented. |
| Preventive relevance | Whether proposed actions address established contributors, when the case permits assessing this. |

We judge a question's information need, not whether it matches our preferred wording. A correct guess without the necessary released evidence is not an evidence-grounded success.

### What can be checked automatically?

Deterministic software checks can establish whether source references exist, documents were released on time, IDs and graph endpoints resolve, versions are preserved, and private material was excluded.

They cannot generally establish that a free-text explanation is causally correct. A valid citation can still be misinterpreted.

### What still needs a judgment?

Whether a question is semantically useful, a source supports a claim, or an arrow represents a justified mechanism requires semantic assessment.

**The choice of human review, an LLM-assisted evaluator, or a combination is not yet locked.** We should first prepare precise targets and inspectable outputs. Before scored evaluation, we must select and freeze the assessment protocol. Any automated semantic judge needs validation; it cannot simply be treated as ground truth.

Without external expert review, we can assess consistency with a constructed package's declared evidence and scenario, but we must not claim that this establishes real-world industrial correctness. Independently reviewed historical material can support a stronger but still appropriately scoped assessment.

### What scores would we report?

Initially, each applicable target can be marked met, partial, missed, overclaimed, or not testable, with supporting output excerpts.

We can then report target coverage, unsupported conclusions, successful evidence-led revisions, outstanding material gaps, and investigation cost. Definitions, denominators, and any weights must be frozen before formal testing. There is no agreed universal 100-point rubric in this plan.

### Whose failure was it?

Keep four categories separate:

- **Package limitation:** the test did not supply sufficient or coherent evidence.
- **Harness failure:** evidence, questions, answers, or corrections were lost or mishandled by the application.
- **Execution failure:** a provider or resource problem prevented the intended operation.
- **Model error within the tested configuration:** intact evidence was delivered, but the model misread it, invented information, or made an unjustified inference.

If the records cannot establish the source of failure, report the result as inconclusive. Do not speculate or assign every remaining problem to the model.

## 14. What experiments would make the research convincing?

First establish a clean controlled pilot, then broaden the evaluation.

- Compare the proposed workflow with a simpler single-agent investigation using the same evidence releases and comparable model settings.
- Include a direct analysis of all evidence available at a given stage as a baseline where appropriate.
- Test selected mechanisms separately—for example, with and without explicit explanation records or evidence-impact revision—to see what contributes to performance.
- Use multiple incident types rather than tuning only to the R3 or instrument-air case.
- Keep development cases separate from held-out evaluation cases. Variants derived from one historical incident belong in the same split.
- Keep each model's evidence, answers, knowledge, and versions independent. Do not silently substitute a stronger model or share another model's discoveries.
- Freeze prompts, application revision, evidence package, release schedule, and model configuration for each scored experiment.
- Record interventions, invalid runs, latency, call counts, and resource usage alongside RCA quality.
- Repeat a declared subset or use repeated trials where feasible to assess variability. Report uncertainty rather than treating one successful run as general proof.

If two systems receive different evidence because they ask different questions, that difference becomes part of the experimental design. It must be recorded rather than described as an identical-input comparison.

## 15. What would the paper contribute?

The preferred paper remains about **industrial RCA as an evolving investigation**, not primarily about software defects or failures of multi-agent systems.

The intended contribution would be a combination of:

1. An investigation mechanism that connects understanding, evidence requests, competing explanations, and causal revision.
2. A transparent method for constructing historically anchored, staged evidence packages.
3. An evaluation of whether the mechanism improves evidence-grounded investigation and revision compared with appropriate baselines.
4. An analysis of where the approach remains unreliable and what can legitimately be concluded from the available data.

The paper should establish novelty through comparison with prior work. “We used multiple agents” and “we displayed a causal graph” are not sufficient contributions on their own.

The strongest result would show that the system identifies meaningful mechanisms and updates them correctly across different cases—not just that it produces a polished final explanation. A positive outcome is a hypothesis to test, not a result we can promise.

## 16. The practical plan from here

1. **Preserve the baselines.** Keep prior code, configurations, inputs, and outputs available for inspection.
2. **Complete and verify the relevant proposed changes.** Focus on source delivery, question intent, partial answers, revisions, and separate factual/causal judgments.
3. **Prepare one controlled package.** Freeze the world, evidence releases, and expected changes before testing.
4. **Run one model through the stages.** Inspect V1 itself, then evaluate the actual progression to V2 and V3.
5. **Identify the source of each failure.** Repair execution defects without silently editing model outputs into success.
6. **Broaden to development cases.** Check whether the method generalizes across different industrial situations.
7. **Finalize the evaluation protocol.** Decide who judges semantic targets, how disagreements are handled, and which measures are reported.
8. **Freeze the research configuration and run held-out comparisons.** Keep researcher interventions and case leakage out of scored runs.
9. **Write the paper around the observed results.** Report capabilities, costs, limitations, and reproducible procedures without overstating validation.

Fine-tuning, model combinations, and fallback models are not prerequisites for this phase. First we need to understand the behavior of the plain investigation method under controlled evidence conditions.

## 17. What success would look like

A successful system would not always announce a root cause.

It would be able to say, in effect:

> “These observations are established. Two mechanisms remain plausible. This particular record would distinguish them. After receiving it, one explanation weakened and the other gained support. These statements and connections changed for these evidential reasons. These remaining uncertainties prevent a stronger conclusion.”

That is the behavior we want to build, measure, and improve: an investigation that learns from evidence rather than a diagram that merely grows.

## Project reading guide

- [Detailed mechanism proposal and research references](RCA_MECHANISM_REDESIGN_PROPOSAL.md)
- [Try 4–6 development history and paper directions](RCA_RESEARCH_BRIEF_TRY4_TRY6_AND_PAPER_OPTIONS.md)
- [Try 6 V1/V2 failure audit](Try%206/evals/TRY6_V1_V2_FAILURE_REPORT_2026-09-20.md)
- [Try 7 technical plan and separate implementation receipt](Try%207/TRY7_EXECUTIVE_PLAN.md)
- [Synthetic evidence-package generation guide](Try%207/SYNTHETIC_EVIDENCE_PACKAGE_GENERATION_GUIDE.md)
- [Implementation and paper checklist](RCA_IMPLEMENTATION_AND_PAPER_CHECKLIST.md)

This overview consolidates the project's existing records and design decisions. It does not report a new experiment, a new literature search, expert approval, or completed comparative validation.

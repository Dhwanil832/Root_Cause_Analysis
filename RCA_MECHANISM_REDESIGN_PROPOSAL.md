# Proposal: an evidence-driven, hypothesis-testing RCA investigation

Date: 20 September 2026  
Status: proposed mechanism, not implemented or experimentally validated  
Scope: industrial incident investigation, not a study primarily about software defects or agent failures

## 1. Recommendation

Keep the workbench, independent model tracks, specialist knowledge bases, common answer fetching, evidence provenance, and version history. Change the investigation's central unit of work.

**The unit should be a testable explanation of part of the incident, together with the evidence needed to assess it. It should not be an isolated question, extracted statement, or proposed board node.**

The investigation should continually establish:

1. What happened, and what remains uncertain about the sequence?
2. How could the actual equipment, people, environment, and operating configuration produce that outcome?
3. Which explanations fit the evidence, and which observations would distinguish them?
4. Which controls were relevant, how did they perform, and what conditions explain their performance?
5. What changes would address the established contributors, and how would their effectiveness be checked?

This is an adaptation of existing investigation principles to our evidence-and-agent workflow. It is not a claim that we have invented hypothesis testing, systemic accident analysis, or multi-agent RCA, or that this design already outperforms published methods.

**Industrial foundation:** the industry partner's supplied Sologic training and cause-pattern material should anchor the investigation's causal structure. External RCA research contributes complementary methods, and AI benchmarks contribute evaluation ideas. Neither replaces the partner's industrial investigation practice. Section 2.3 records the local sources reviewed and the changes they imply; this alignment is proposed, not yet partner-approved or implemented.

## 2. What the research contributes

### 2.1 Work explicitly concerned with the RCA or accident-analysis process

| Work | What it actually does | Useful lesson and boundary for our system |
| --- | --- | --- |
| [AgentRCA: Agentic Root Cause Analysis through Evidence-Grounded Reasoning](https://arxiv.org/html/2607.22385v1), July 2026 preprint | Evaluates candidate physical faults using tools, normal-operation comparisons, and a changing hypothesis table. It uses a normal-data-trained digital twin and supplied fault descriptions; its evaluations include PRONTO and the simulated Tennessee Eastman process. | Borrow explicit hypothesis comparison and configuration-appropriate baselines. We do not currently have an equivalent digital twin, and our investigation cannot be restricted to a supplied list of fault classes. This is fault diagnosis, not demonstrated completion of an organizational accident investigation. |
| [MA-RCA: Leveraging multi-agent framework for root cause analysis](https://link.springer.com/article/10.1007/s40747-025-02096-0), published online November 2025; 2026 journal volume | Separates RCA coordination, retrieval, validation, and reporting. Retrieved historical patterns generate possibilities; validation checks them against operational data. Its evaluation uses cloud and power-metering datasets. | Borrow the distinction between proposing a cause and testing it with case evidence, including reusable verification work. Historical similarity must not become proof about our current incident. Published evaluation results are not evidence that its design transfers unchanged to our documents. |
| [CAST Handbook](https://psas.scripts.mit.edu/home/get_file4.php?name=CAST_Handbook.pdf), Nancy Leveson, 2019 | An accident-analysis method based on systems theory. It examines physical events, safety constraints, controls, responsibilities, feedback, and interactions; analysis generates further investigation questions. | Use it to examine why relevant safety controls were ineffective, including what people knew and why actions made sense at the time. CAST is an analysis method, not a complete evidence-collection procedure. We are borrowing a systems lens, not claiming full CAST compliance. |
| [Tripod Beta](https://tripod.energyinst.org/beta), established incident-analysis methodology | Connects the event sequence to hazards, affected objects, barrier performance, and deeper conditions. Its model and evidence gathering inform each other. | Make barrier analysis serve the explanation. Include controls that worked in a near miss. Do not force every technical failure into a human-error explanation or assume that every conceivable safeguard was a required barrier. |
| [HSE HSG245: Investigating accidents and incidents](https://www.hse.gov.uk/pubns/hsg245.pdf), 2004 guidance | Connects information gathering and analysis to risk controls, implementation, and follow-through. It explicitly describes investigation and analysis proceeding together. | Treat questions and analysis as an iterative investigation that ends in prevention-oriented findings, not just a completed diagram. This is established guidance, not a recent AI result. |
| [NASA spaceflight mishap investigation handbook](https://www.nasa.gov/wp-content/uploads/2021/06/spaceflight-mishap-handbook_tagged.pdf), sections 6.2.1-6.2.2 | Distinguishes fault-tree exploration of potential causes from events-and-causal-factor analysis using existing evidence. | Maintain separate exploratory explanations and evidence-backed findings. Its spaceflight context is different from ours; we are adopting a representation distinction, not NASA's regulatory workflow. |
| [DiagGuard / Beyond Fault Localization](https://arxiv.org/html/2608.21310v1), August 2026 preprint | Studies diagnostic trajectories and fault-propagation paths, then tests grounding and verification stages around a diagnostic agent. | Check whether relevant evidence was acquired, interpreted correctly, and actually used in the explanation. Its microservice results support investigating this design idea, not assuming it solves industrial accident RCA. |

AgentRCA also reports that the hypothesis-table approach did not help every model: a smaller model regressed under the additional structure. Accordingly, we should test a compact explanation record rather than ask our model to repeatedly rewrite a large comparison matrix. This is a caution about transferring the method, not a prediction about our Qwen run.

An additional directly industrial paper, [Root Cause Analysis for Industrial Incidents based on Retrieval-Augment with Hypothetical Queries Collaboration](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5861144), was posted to SSRN in December 2025. Its accessible abstract describes generating hypothetical queries for document retrieval. I could verify the abstract, not inspect the full paper, so it is supplementary context rather than a principal basis for this proposal.

### 2.2 What we retain from the benchmarks discussed earlier

| Benchmark | What we borrow | What we do not assume |
| --- | --- | --- |
| [RCAEval](https://arxiv.org/html/2412.17015v5) | Evaluate both the broad location of a problem and the specific diagnostic indicator; use reproducible cases and baselines. | Identifying an affected component or indicator completes a full industrial RCA. |
| [ITBench](https://proceedings.mlr.press/v267/jha25a.html) | Test actions and outcomes in a defined environment, not only the persuasiveness of a final narrative. | Our document workbench has a live plant environment or authority to conduct operational interventions. |
| [Cloud-OpsBench](https://arxiv.org/html/2603.00468v2) | Hold available evidence fixed across comparisons; assess established diagnostic milestones and their evidential dependencies, allowing alternative valid investigation paths. | Its hidden evaluator graph should be supplied to the investigating model, or its Kubernetes results establish industrial safety performance. |

Our adaptation is to evaluate whether the model establishes meaningful parts of an industrial mechanism, with appropriate uncertainty, as evidence arrives. The benchmark answer key remains outside the investigation. The agent must derive its own explanations and information needs.

### 2.3 Industry-partner background literature: the methodological foundation

Source folder: [Try 1/Background Litrature](<Try 1/Background Litrature/>). The review covered the two Sologic training decks, the diagrams embedded in `CAUSE PATTERNS.docx`, both supplied meeting transcripts, selected OSHA/DOE methodology sections, and the identities and applicability metadata of the `RCA_Ref` documents. It was not a page-by-page review of the entire library, a new analysis of the historical spreadsheets, or a review of the meeting recording. Both transcripts contain substantial timestamp gaps, so they cannot establish everything agreed in those meetings. The human-error deck also contains draft presentation notes; it should not be described as a ratified company policy.

| Partner-provided source | What it establishes about the intended method | Consequence for our design |
| --- | --- | --- |
| [Sologic RCA Process Demonstration](<Try 1/Background Litrature/Ericks Guide books/Sologic RCA Process Demonstration.pptx>), slides 6, 11, 15–18 | Evidence collection, problem definition, cause-and-effect analysis, solutions, and reporting form one process. The causal explanation works backward from a focal event and includes causes acting together. | Start with a clearly scoped event. Represent a combination such as A **and** B producing C, not merely two unrelated arrows into C. Preserve intermediate mechanisms instead of jumping from a broad category to the outcome. |
| Same deck, slide 16, and [CAUSE PATTERNS](<Try 1/Background Litrature/Ericks Guide books/CAUSE PATTERNS.docx>) | An event can depend on a change together with pre-existing states or properties. The patterns illustrate damage/impact, falling, fire/contamination, and human action. | Specialists investigate both what changed and what made that change consequential. Patterns guide questions and candidate explanations; they do not prove that every illustrated condition occurred in this incident. Do not expand generic conditions merely to increase node count. |
| [Human Error + Intro deck ideas for Cliffs](<Try 1/Background Litrature/Ericks Guide books/Human Error + Intro deck ideas for Cliffs.pptx>), slides 15–20, 28–39 | Define the focal point, time, place, actual impact, and potential impact. Describe human actions factually and investigate the conditions behind them. The Cause + 2 teaching device encourages deeper investigation. | A near miss's potential injury is not an actual injury. Human action can appear in the explanation, but "operator error" is not an adequate endpoint. Seeking deeper causes must not become an instruction to invent two organizational layers. |
| Same human-error deck, slide 26 and its speaker notes | A specific preventive change is different from a task such as reviewing a procedure or conducting additional analysis. | Keep investigation tasks separate from corrective actions. Each proposed corrective action should identify the supported causal relationship it is intended to change and a way to verify effectiveness. |
| [OSHA Root Cause fact sheet](<Try 1/Background Litrature/OSHA Docs/OSHA3895 (1).pdf>), pages 1–3 | Investigation should address underlying system factors, often multiple, rather than stop at the immediate problem or individual fault. | Preserve interacting technical and organizational contributors where supported; do not require a single deepest cause. This supplied guidance is not itself proof of a case-specific violation. |
| [DOE accident-analysis handbook](<Try 1/Background Litrature/OSHA Docs/DOE-Accident-and-Operational-Safety-Analysis-Volume-I-Accident-Analysis-Techniques (1).pdf>), section 2.9, printed pages 2-111–2-112 | Verification traces conclusions and proposed needs back through analysis to facts; technical and factual accuracy require appropriate human review. | Evaluate traceable facts → mechanism → contributors → preventive needs. A connected diagram alone is insufficient. Use expert-prepared evaluation references and human adjudication of genuinely new interpretations, not an LLM judge. We are borrowing this verification principle, not importing DOE's institutional approval requirements. |

**A display convention is not a causal direction.** The Sologic demonstration draws from effect toward its explanatory causes, backward in time. Our underlying record should explicitly identify the effect, its contributing causes, and any joint requirement. The evaluator must compare those meanings, not penalize a different left/right canvas arrangement.

#### Keep methodology, document templates, case knowledge, and evaluation truth separate

- **Method guidance:** Sologic decks, cause-pattern examples, and the supplied investigation guides explain how to investigate. They are not observations of the current incident.
- **Document-format examples:** the partner's sample documents in `RCA_Ref` show what documents should look like: their structure, fields, level of detail, and supporting records. As clarified by the user, their role in this project is template/reference material, not operational knowledge about the investigated incident. Keep them outside the investigation's evidence retrieval and evaluation answer key. Their contents must not establish a cause, an applicable requirement, or a violation.
- **Case-specific reference knowledge:** separately supplied and verified plant/equipment documents can establish relevant system relationships or expectations after checking site, equipment, task, revision, and incident-date applicability. This is a different input class from the partner's document-format examples.
- **Case evidence:** incident-specific records and observations establish what was reported or observed, with source limitations preserved.
- **Hidden evaluation reference:** an independently reviewed case key records acceptable findings, evidence combinations, alternatives, and unresolved issues. It must not enter the investigating model's evidence store.

Use a sample lockout form to understand the shape of a lockout record, a maintenance example to understand how a work instruction is documented, and a training form to understand the records an investigator might request. Do not copy their equipment states, actions, requirements, employee details, or conclusions into the current case. If they inform a synthetic evidence package, the package's facts must come from the separately fixed scenario, not from incidental content in the templates. Template contents must not leak into the hidden case key either.

The `RCA_Ref` folder includes Dearborn task examples and documents with dates different from the R3 event. Those differences are not deficiencies in this template collection: it was not supplied as R3 case evidence. Likewise, blank fields in a sample form are not evidence of missing training, omitted work, or absent physical controls. The user's clarification governs how these examples are used; the July 29 transcript also describes the supplied documents as reference examples.

## 3. The revised investigation loop

### Step 1 - Build an incident-specific understanding of the system

From the initial account and available documents, establish the incident boundary, affected people/assets, operating mode, relevant locations, and what the components do.

Maintain distinct records for:

- **Reference knowledge:** how the plant or equipment is designed to operate, including the applicable configuration and document revision.
- **Incident observations:** what a source reports happened, where, when, and under what observation limitations.
- **Interpretations:** what those observations may imply.

A plant drawing can establish a connection. It does not establish that a valve was open that morning. A handbook can establish an applicable expectation, but not whether a person followed it. A model's general engineering knowledge can suggest a question; it cannot establish an undocumented feature of a particular machine.

Ask baseline questions when an unknown prevents understanding. Continue with explicitly marked gaps when other parts can be investigated independently.

### Step 2 - Reconstruct the sequence and locate the important change

Build a timeline that preserves observation times, uncertainty, source disagreement, and the distinction between commanded and observed states.

Compare the actual operating mode with the relevant reference condition: production, shutdown, maintenance, startup, or a temporary arrangement. A production baseline may be inappropriate during an outage.

The immediate objective is to identify the changes or unexplained transitions requiring an explanation, not to declare a root cause. Recovery after an intervention is useful evidence, but does not alone establish which change caused recovery.

### Step 3 - Develop plausible mechanisms, not lists of blame categories

Tags still select expertise. Specialists contribute mechanisms relevant to the equipment, task, exposure, or unexplained observations. A mechanism describes how an outcome could occur, including combinations of conditions where necessary.

For each active explanation, maintain a compact record:

| Field | Purpose |
| --- | --- |
| Outcome or transition explained | Defines the branch's actual subject. |
| Proposed mechanism | States how the transition could occur, not merely which category is involved. |
| Required conditions | Identifies what must hold for this particular explanation to work. |
| Supporting and challenging evidence | Grounds comparison in original sources. |
| Unresolved assumptions | Prevents a plausible assumption becoming an established fact. |
| Useful discriminating observation | Identifies evidence that could change the explanation or separate alternatives. |

Alternatives need not be mutually exclusive. Several conditions can jointly produce the outcome. Preserve an unresolved-mechanism route when the available candidates fail to explain an important observation; do not choose the least implausible candidate merely to finish.

This record is an inspectable justification summary, not a request to expose a model's hidden internal reasoning.

### Step 4 - Choose evidence that can change the investigation

A proposed question should identify its investigative purpose. It can:

- establish a missing fact needed to understand the system;
- distinguish plausible mechanisms;
- check a decisive assumption, contradiction, or causal connection;
- establish the performance of a relevant control;
- explain a known action in its work context;
- investigate an important observation that the current explanations do not cover.

Priority depends on what an answer could change, the significance of the gap, and whether useful evidence is accessible. Ask for a drawing when geometry is uncertain; an interview is not automatically an adequate substitute. Preserve an evidence source at risk of disappearing before a lower-value retrospective query.

**No fixed number of questions per tag is proposed.** However, permission to ask questions is not permission to repeat an unchanged request. Deferred questions remain visible with a reason. An unavailable answer becomes a specific outstanding evidence need, not an endless regeneration task or evidence against a hypothesis.

The question broker merges overlapping requests while retaining their purposes, scopes, and originating specialists. If two questions share only part of an answer, the uncovered part remains open.

### Step 5 - Search and answer before asking the user again

The common answer-fetching agent searches all specialist knowledge bases and original evidence within the current model track. It can retrieve neighboring passages, tables, legends, and related documents where context is necessary.

Return a source-backed result as answered, partially answered, disputed, or not established. Distinguish independent corroboration from several agents repeating the same document.

The question broker then returns that result to every relevant specialist and the causal investigation role. This preserves our agreed routing: **answer fetching searches across knowledge; the broker distributes the result.**

Reference literature and historical cases can suggest mechanisms and expected signatures. Only applicable current-case evidence can establish that those conditions occurred here. Simulation answers remain attributed to their released scenario source, not represented as independent real-world observations.

### Step 6 - Update the explanation, not just its confidence label

For every consequential new answer, determine what is added, corrected, supported, contradicted, or still unresolved. Revisit affected dependent statements and connections, while retaining unaffected work.

Check four distinct questions:

1. Does the source actually support the observation as worded?
2. Are the entity, location, configuration, and time correct?
3. Is the proposed mechanism plausible for this actual system?
4. Does the evidence justify this connection, and what uncertainty remains?

Two true statements do not automatically form a causal link. An earlier event can precede a later one without causing it. An alarm can reveal a condition without initiating it.

A review that detects the wrong timestamp or component must trigger a correction, withdrawal, or clearly visible unresolved discrepancy. It must not merely change a badge while preserving a false sentence. A conflict should identify incompatible claims about the same scope; different observations at different times may describe a changing system rather than a contradiction.

A failed claim should not erase independent valid work. But conclusions dependent on that claim must lose the support they no longer have.

### Step 7 - Investigate controls and deeper contributing conditions

Physical explanation and control analysis should inform one another. We do not have to wait for complete mechanical certainty before gathering relevant planning or handover evidence.

For an implicated control, ask what it was intended to prevent, whether it applied in this configuration, what evidence establishes its state, and how its performance affected the event. Distinguish an absent control, an ineffective control, a control outside its intended function, and a control whose state is unknown.

Where people or organizations contributed, investigate the information available at the time, responsibilities, competing demands, procedures, feedback, and coordination. Do not stop at "operator error," and do not manufacture "poor safety culture" because a deeper box is expected.

Potential improvements are not automatically evidence that their absence caused the incident. Nor does every investigation require one deepest root-cause node. The result can contain several interacting causal and contributing conditions, with explicit limits on what could be established.

### Step 8 - Publish a useful investigation version and prevention plan

V1 should contain a defensible preliminary sequence, relevant system understanding, active explanations, supported findings, and targeted evidence requests. It need not contain a complete causal board.

Later versions should show substantive changes: an explanation strengthened or weakened, a wrong statement corrected, a control's role established, or a concrete gap remaining. Unchanged wording is not evidence of stagnation when new evidence genuinely corroborates it; changed wording is not evidence of progress by itself.

Keep three distinguishable views:

- **System/context view:** how equipment, people, and controls are related.
- **Investigation view:** proposed mechanisms, alternatives, and unresolved questions.
- **Evidence-backed findings view:** statements and relationships currently justified, with qualifications.

These can be layers of one interface rather than three separate applications. Node labels such as event or barrier remain metadata, not repeated sentence prefixes.

For established contributors, propose actions that identify the mechanism or control they address, the expected preventive effect, and how an authorized person would verify effectiveness. Immediate protective actions can be recorded separately from final corrective actions; uncertainty about the final cause must not be interpreted as a reason to delay human safety decisions.

Publishing a version is different from closing the investigation. Human review determines acceptance and closure, including the significance of remaining uncertainty. The application must not independently manipulate plant equipment or treat an imagined counterfactual as an executed test.

## 4. A concrete R3 illustration

This is a demonstration of investigative behavior, not a fresh factual finding about the R3 accident.

The initial account says the beam fell and describes the recovered beam/link/keeper and changed outage configuration. That supports an outcome and several observations. It does not, by itself, establish the full release mechanism.

| Investigation issue | Productive next step | What must not be assumed |
| --- | --- | --- |
| What normally retains or supports the assembly? | Request an applicable drawing or qualified explanation of the beam, link, keeper, yoke, and support interfaces. | That a device called a keeper retains the entire assembly against every possible motion. |
| Did something break, disengage, move, or become unsupported? | Compare inspection findings with the actual geometry and configuration. Retain alternatives where inspection coverage is incomplete. | That "no apparent damage" rules out every failure, or proves one alternative mechanism. |
| What changed during the outage? | Establish which support relationships changed when rolls were removed and systems isolated. | That an isolation operation necessarily removed the relevant physical support. |
| Could the proposed relative motion release the assembly? | Seek positional evidence, dimensions, applicable engineering analysis, or a qualified reconstruction. | That naming "off-center displacement" makes disengagement physically demonstrated. |
| What should have prevented this mechanism? | Establish intended control function, applicable requirements, actual implementation, and inspection evidence. | That a blank restraint-record field proves no restraint was physically present. |
| Why did the relevant arrangement exist? | Investigate the documented work plan, available information, design assumptions, responsibilities, and handover as relevant. | That a planning failure, missing qualification, or organizational cause is already established. |

A later drawing may establish that disengagement is possible in a certain arrangement. That changes physical plausibility, not proof that the necessary motion happened. A subsequent observation can then support or challenge that motion. Only their combination may justify the mechanism. This is the progression our board should make visible.

Counterfactual questions such as "Would this mechanism remain possible with the proposed restraint?" can expose assumptions and guide expert checks. An LLM's answer alone is not a physical test, and removing one factor is not a universal test of causation when several independent routes can produce the outcome.

## 5. What changes relative to Try 6

Try 6 already has initial framing, branches, targeted consultation, evidence resolution, and review. The proposal is not simply to rename those stages or add another critic. The reviewed [V1/V2 evidence report](<Try 6/evals/v1-v2-presentation-review/output/Try6_V1_V2_Evidence_Review.md>) documented facts entering the notebook without adequately changing the selected mechanism, review findings not repairing some wording, and new evidence requests lacking a publication route.

| Existing capability to preserve | Required change in behavior |
| --- | --- |
| Source notebook | Explicitly connect relevant reference knowledge, observations, and unresolved assumptions to active explanations without promoting all observations to board nodes. |
| Initial frame and branches | Make each active branch specify its mechanism, supporting/challenging evidence, and unresolved conditions. |
| Specialist consultation | Give a concrete investigative assignment, while allowing evidence-grounded alternatives and blind-spot questions. Tags route expertise; they do not establish causation. |
| Question broker and common answering | Preserve merged subquestions and return answers to every affected owner; search before issuing a redundant user request. |
| Statement and connection review | Make correction and dependent reassessment part of the update, not optional prose left beside an unchanged board. |
| Versioned publication | Publish findings, alternatives, change explanations, and actionable gaps together. A usable partial version must not imply final closure. |

Separate specialist knowledge bases remain useful for different perspectives. The same shared source retrieved by three specialists still counts as one source. Separate model tracks remain independent. There is no new requirement for an ensemble, fallback model, or fine-tuning.

## 6. How to establish whether it is actually better

Use the same model and the same released evidence to compare the existing Try 6 mechanism with this proposal. Keep hidden case truth and evaluator expectations out of both runs. Test the investigator first with fixed releases; reconnect the storyteller only after that comparison is interpretable.

Before a new evidence release, specify what it can establish, what it challenges, and what remains unknowable. Where several explanations remain consistent, the correct output is uncertainty, not forced selection.

Assess:

1. **Observation fidelity:** correct entity, value, location, timing, and scope.
2. **Mechanism quality:** justified directed connections, including interacting conditions, rather than merely correct component names.
3. **Evidence use:** decisive available information changes the relevant explanation or is explicitly judged insufficient.
4. **Question value:** requests resolve meaningful gaps and do not repeatedly ask for already supplied information.
5. **Revision quality:** warranted corrections happen; unsupported certainty is reduced; unrelated valid findings survive.
6. **Depth:** the investigation distinguishes the physical mechanism from relevant control and contextual contributors.
7. **Prevention relevance:** proposed actions address established contributors and include a means of checking effectiveness.
8. **Practical cost:** calls, elapsed time, and user burden per meaningful investigative advance.

### Evaluation without an LLM judge

Use an expert-reviewed hidden reference and deterministic scoring for the portions that can be specified in advance. This is a proposed evaluation design, not an already implemented evaluator.

1. **Prepare a case key once, before comparing models.** Record the focal event; scoped facts; acceptable mechanisms and joint-cause groups; relevant controls; acceptable evidence combinations; and what each evidence release leaves uncertain. Include alternative valid explanations and multiple acceptable paths rather than one required diagram. Distinguish missing evidence from evidence against a claim.
2. **Require structured investigation records alongside readable prose.** Entity, relation, state, time/configuration, source span, uncertainty, causal-group membership, and action target are explicit fields. These are generic fields, not a menu of the hidden case's correct causes. A source citation's existence alone does not prove that it supports the claim.
3. **Compute separate, version-aware metrics.** Score factual precision/recall; supported causal relations and complete joint-cause groups; accepted evidence combinations; justified uncertainty; warranted revisions; repeated or already answered requests; and cause-linked action coverage. Compare only against what the evidence released so far can establish. Do not reward an empty board for avoiding errors, count generic physics nodes as investigative depth, or treat two individually correct nodes as a verified mechanism. Do not add a 100-point weighted total until the weights and acceptance criteria are agreed with the partner.
4. **Route unmatched meanings to limited human adjudication.** Explicit aliases and normalization can match known equivalents, but arbitrary free-text causal validity cannot be reliably decided by string matching. New interpretations remain unadjudicated, not automatically wrong or silently ignored. Report automatic-scoring coverage and outstanding adjudications. If a new interpretation is accepted, update the versioned key and rescore all compared systems consistently. Final engineering adequacy and action effectiveness still require qualified review.

The partner's joint-cause diagrams make plain edge accuracy insufficient: a model can mention A, B, and C yet fail to establish that A and B jointly explain C. The DOE verification guidance also makes action-to-evidence traceability part of the evaluation, not merely narrative quality. These are concrete industrial criteria; the case-specific accepted mechanisms still need independent review. Library templates alone cannot supply that ground truth.

Evaluate across incident families and held-out cases so that changes do not merely encode the R3 or IA-16036 answer. Keep related variants of one incident together when separating development and test cases. Test the competing-explanation record, targeted evidence selection, and correction/update mechanism separately as well as together. Frozen evidence releases allow reproducible model comparisons; storyteller-generated releases should be assessed separately before being used as a common test fixture.

The initial success criterion is a better-supported and appropriately incomplete V1 that makes the correct changes in V2. It is not a larger board, more questions, or more confident language.

## 7. Proposed implementation order, once approved

1. Agree on the investigation records and their meaning: system knowledge, observation, explanation, evidence need, supported finding, human decision.
2. Connect explanation updates to existing source reading, question handling, and review. Make corrections and outstanding evidence requests visible before adding more exploratory work.
3. Test a controlled two-version investigation against the current implementation, including a withheld answer that should remain unresolved.
4. Extend control/context analysis and cause-linked action review; test across additional incident families.
5. Reconnect the separately evaluated storyteller using frozen scenario truth and attributed answer releases.

This order addresses the evidence-to-explanation transition first. It does not require rebuilding the entire application or generating another large population of agents.

## Bottom line

**Use the partner's industrial RCA guidance to anchor the investigation, research to improve the mechanism, independently reviewed case references to evaluate it, and applicable case evidence to decide its conclusions.**

The proposed change is from accumulating analysis artifacts to maintaining and testing explanations: understand the system, identify the unexplained transition, compare plausible mechanisms, obtain discriminating evidence, revise the explanation, investigate relevant controls and context, and verify prevention-oriented findings with human oversight.

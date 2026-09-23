# RCA implementation and paper checklist

Date: 20 September 2026  
Status: planning checklist; app changes and experiments below are not completed.  
Scope: industrial RCA from progressively released documents, not primarily a paper about software failures.

## Agreed direction

Build the investigation mechanism and evidence packages now. Decide later whether semantic judgments will come from us, an LLM, or both. Do not restrict the investigation to canned questions merely to make it easy to score.

We can postpone **who judges**, but we must define the scenario, expected evidence-driven changes, and what information was available before running it. Select and freeze the final judging protocol before evaluating held-out cases. This prevents choosing a rubric or judge because it favors results we have already seen.

The partner's sample documents supply document structure and style only. Their incidental contents are not current-case evidence or the answer key. RCA training guides supply methodology. Historical incident rows supply an initial factual anchor; synthetic extensions are separately identified in the private case manifest.

## A. Code changes — start here

### A1. Preserve and identify the working baseline

- [ ] Preserve the current Try 6 code, prompts, configuration, and saved V1/V2 outputs with hashes or a reproducible snapshot. Keep credentials and personal data out of any shareable archive.
- [ ] Implement in a separately identified development version without overwriting historical results. Choose its folder/branch name when implementation begins; this checklist does not create a new app copy.
- [ ] Update the architecture documentation to match the active router and planner. The current `ARCHITECTURE.md` describes an earlier question-oriented pipeline; the README and active planner describe the investigation-led workflow.

**Existing code to extend, not recreate:** `InvestigationBranch` already holds a mechanism, supporting/opposing findings, a gap, and a change reason. `EvidenceDirection` already records the information sought and its possible implications. The active planner already performs targeted consultation and publishes a partial position. The work is to make those mechanisms more explicit and reliable, not add them again under new names.

### A2. Make explanations and their evidence requirements explicit

- [ ] Extend each explanation with the precise event/transition it explains, required conditions, unresolved assumptions, and the observations that could distinguish it from alternatives. Keep stable identities across versions.
- [ ] Represent conditions that must hold **together**, separately from alternative explanations. A group of required causes is not interchangeable with independent arrows.
- [ ] Separate a recorded observation, an interpretation, and a proposed mechanism. Compare the incident with the applicable operating configuration, not automatically with normal production.
- [ ] Preserve entity, action/state, time or interval, location/configuration, and original source references when available. Do not require every observation to become a board node.

**Done when:** an explanation can be inspected as “this transition may have occurred this way; these conditions are established; these remain unknown; this evidence could change the assessment.”

### A3. Supply the evidence needed for the actual decision

- [ ] Assemble relevant original passages from multiple documents around an explanation or information need, including qualifications and challenging evidence. Do not rely solely on accumulated summaries.
- [ ] Ensure consequential new evidence reaches the explanation-update step. Record what was included, omitted, or unavailable; do not assume that a document being uploaded or extracted means its content was used.
- [ ] Reuse unchanged source reads and completed checks. Reconsider them when their source, scope, or dependencies change. Repeated retrieval of the same source must not count as independent corroboration.
- [ ] Keep default references, starter evidence, and later answer attachments separately attributed within each model's independent track. Never silently trim required evidence to fit a call.

**Done when:** a multi-document mechanism is assessed using the relevant original observations together, and a missing-information claim identifies the actual remaining gap.

### A4. Improve specialist, broker, and answering behavior

- [ ] Give specialists a concrete unresolved issue to investigate while retaining their ability to propose evidence-grounded alternatives and identify overlooked observations.
- [ ] Tie proposed questions to their investigative purpose. Allow foundation questions where understanding is missing, not only questions that favor existing hypotheses.
- [ ] Merge overlapping information needs while retaining all owners, different time scopes, and unanswered subparts. Return answers through the broker to every affected specialist and explanation.
- [ ] Distinguish answered, partially answered, conflicting, unavailable, and not yet searched. “No record found” must not become “the action did not happen.”
- [ ] Publish outstanding questions created during claim or connection review, not only the questions created during initial framing.

**Done when:** one useful answer reaches all relevant owners, previously answered portions are not repeatedly requested, and new review questions have a visible route to an answer.

### A5. Make revisions change the board, not only the status badges

- [ ] For consequential new evidence, record an explicit decision for affected explanations: supported, challenged, corrected, split/combined, withdrawn, or unchanged with a reason. These are update actions, not a requirement to select a final cause.
- [ ] Apply detected factual corrections to the saved claim text, dependent relationships, summary, and displayed board. Do not leave contradictory versions of the same statement within one snapshot.
- [ ] Reassess conclusions whose support was withdrawn. Preserve independent valid findings and the immutable earlier versions.
- [ ] Distinguish statement support, validity of its causal role, and support for its connections. A true observation does not automatically qualify as a barrier or prove causation.
- [ ] Check temporal direction and event identity. Require an identified protective function for barrier/prevention relationships. Do not prohibit legitimate feedback merely because the graph contains a cycle.
- [ ] Preserve partial support, contradiction, missing evidence, and invalid review as different states. Quarantine invalid individual proposals without stopping unrelated valid work; make unusable foundations explicit.

**Done when:** a reviewer finding a wrong timestamp produces a corrected timestamp or an explicitly unresolved claim, and new evidence can change the mechanism rather than just add nodes.

### A6. Keep the app inspectable and publish usable versions

- [ ] Keep the main routing entry clear, with separate modules for understanding, explanation management, specialist work, brokerage/answers, revision, review, and publication. Retain section-specific prompt folders.
- [ ] Explain each agent's investigative purpose in its prompt, what counts as evidence, how to handle uncertainty, and what it must return. Keep kickoff questions as examples, not an exhaustive script.
- [ ] Display observations, possible explanations, supported findings, open questions, and the V1→V2→V3 change history distinctly. Keep event/barrier labels as metadata rather than repeated sentence prefixes.
- [ ] Publish an accurate partial version when a useful position exists and further progress requires new evidence. No fixed number of questions or invented deeper causes is required to finish a version.
- [ ] Keep investigation tasks separate from corrective actions. Link proposed actions to established contributors and preserve human approval; the app must not issue or execute plant operating instructions.

### A7. Build the experiment interface without choosing the judge

- [ ] Add a versioned package loader and release manifest: original/default inputs, V1 documents, V2 additions, V3 additions, and independently stored private scenario/expectation files.
- [ ] Enforce the separation in retrieval and tool access. Investigator agents must not read future releases, the private scenario, the expected board, or grading notes. A “do not look” prompt is not the boundary.
- [ ] Add a reproducible runner for one model and one case at a time, with checkpoints, resume, explicit failures, and preserved partial results. Do not silently replace a failed model or manually repair its output in a scored run.
- [ ] Export a common review packet containing the evidence actually released, questions, answers, explanations, boards, revisions, source references, final stage outputs, prompt/configuration hashes, timing, and token/call usage. Save inspectable justifications, not a requirement to disclose private chain-of-thought.
- [ ] Keep external assessment records separate from the investigation. Support human or LLM assessments later, with evaluator identity/version, rationale, and unassessed items. The investigator's own review status is not an independent performance score.

### A8. Verify the changes in proportion to the risk

- [ ] Add focused regression checks for source isolation, merged-question routing, partial answers, changed-evidence delivery, applied corrections, causal-role/temporal semantics, partial publication, and version immutability.
- [ ] Perform normal build/type checks and move promptly to the first real-model pilot. A passing software test is not an RCA acceptance result; avoid another prolonged sequence of model-based preflight runs.

### Code navigation for implementation

These are inspected current locations, not a promise that every change belongs in exactly one file.

| Responsibility | Current location |
| --- | --- |
| Application entry | [main-router.ts](<Try 6/src/orchestrator/main-router.ts>) |
| Investigation state and output contracts | [types.ts](<Try 6/src/engine/investigation/types.ts>), [contracts.ts](<Try 6/src/engine/investigation/contracts.ts>) |
| Work selection and active dependencies | [planner.ts](<Try 6/src/engine/investigation/planner.ts>), [review-dependencies.ts](<Try 6/src/engine/investigation/review-dependencies.ts>) |
| Context and applying results | [context.ts](<Try 6/src/engine/investigation/context.ts>), [apply.ts](<Try 6/src/engine/investigation/apply.ts>) |
| Source registration and retrieval | [src/knowledge](<Try 6/src/knowledge/>) |
| Review and board projection | [src/engine/review](<Try 6/src/engine/review/>), [src/engine/board](<Try 6/src/engine/board/>) |
| Immutable model-local versions | [engine-repository.ts](<Try 6/src/server/engine-repository.ts>) |
| Stage prompts | [prompts](<Try 6/prompts/>): investigation-map, connections, targeted-consultation, evidence-resolution, map-refinement, claim-review, causal-verification, specialists |
| Dashboard and canvas | [app/incident](<Try 6/app/incident/>) |
| Storyteller, evaluated separately | [src/story-agent](<Try 6/src/story-agent/>) |
| Tests and experiment tooling | [scripts](<Try 6/scripts/>), [evals](<Try 6/evals/>) |

## B. Build the evidence packages

- [ ] Complete one development case from scenario to V3 before scaling package production. Choose additional cases to cover distinct industrial mechanisms and evidence challenges, not cosmetic variants of one accident.
- [ ] Record which details come from the historical row, which are synthetic, and which remain unknown. An incident author's preliminary or final conclusion is a reported finding, not automatically complete causal truth.
- [ ] Freeze the private scenario before writing model-visible documents. Specify the mechanism, interacting conditions, relevant controls, chronology, alternative explanations, and unresolved limits.
- [ ] Derive realistic documents from that scenario using the partner's samples for format only. Remove personal identifiers and identifying company details from synthetic/public artifacts; maintain internal provenance separately.
- [ ] Distribute causal information across documents where combining them is necessary. Avoid filenames, headers, annotations, or repeated explicit conclusions that reveal the answer accidentally.
- [ ] Define V1's defensible preliminary understanding, V2's discriminating evidence, and V3's deeper control/context evidence or correction. Do not require every version to increase certainty or every V3 to close the investigation.
- [ ] Include selected incomplete records, relevant contradictions, and misleading but attributable accounts. Preserve enough information to justify the expected response; an unresolvable ambiguity must remain an accepted outcome.
- [ ] Record expected changes, acceptable alternatives/evidence combinations, and forbidden overclaims before the run. Do not prescribe exact wording, exact questions, one drawing layout, or a fixed number of nodes.
- [ ] Check package consistency, difficulty, and solvability. We can check authored consistency ourselves, but without qualified external review we must not call the packages industrially validated.

**Deliverable:** one immutable case folder with model-visible releases, a private scenario/expectation record, and a source/synthetic provenance manifest.

## C. Produce the first controlled V1→V3 result

- [ ] Start with the existing Qwen model configuration, frozen for reproducibility. Use direct fixed document releases; keep the storyteller disconnected.
- [ ] Run V1, save the provisional board and open requests, then release V2 and V3 separately. Save each version before proceeding. Log any intervention, repair, rerun, or missing output.
- [ ] Examine whether the mechanism changes for the expected evidential reasons, whether contradictions are handled, and whether correct earlier work survives. Completion, a larger board, or a higher confidence label is not sufficient.
- [ ] Run the preserved baseline on the same new package and evidence schedule. Historical runs on different inputs are illustrative, not a controlled comparison.
- [ ] Fix general defects using development cases. Version any changed code or package and rerun the affected comparisons; never silently rewrite the answer key to favor an output.

**First milestone:** one reproducible investigation with three preserved versions and an inspectable account of what each evidence release changed. This is a development milestone, not proof of publication readiness.

## D. Choose the assessment method after the development pilot

- [ ] Decide whether semantic assessment is human, LLM-based, or combined. Freeze instructions and primary outcomes before looking at held-out results.
- [ ] Evaluate factual fidelity, supported mechanisms and joint conditions, uncertainty, information needs, revision quality, preservation of valid findings, and prevention relevance where evidence permits. Report cost and execution reliability separately from scientific quality.
- [ ] Keep mechanical checks distinct from semantic judgments. Valid IDs, citations, JSON, or a model-supplied label do not prove causal correctness.
- [ ] If humans judge, define the rubric, blind system identity where practical, double-rate a subset, and report agreement and disagreements. Researcher review is not automatically industry-expert review.
- [ ] If an LLM judges, disclose its model/prompt/settings, provide original evidence and the hidden reference, test order/style sensitivity, and audit a sample against our own assessments. Report model-judged results as such; do not claim expert validation.
- [ ] Define treatment of alternative valid findings, unassessable claims, empty boards, failed runs, and missing versions. Report evaluation coverage and denominators; do not score only successful runs.
- [ ] Agree any combined score and weights in advance, if needed. Prefer interpretable component results over an unexplained 100-point total.

**Not postponed:** private scenario, release manifest, evidence provenance, and expected changes. **Postponed:** the semantic evaluator and its implementation.

## E. Run experiments that can support a paper

- [ ] State research questions before the main study: does the mechanism improve evidence-supported RCA, does it revise appropriately as evidence arrives, and which components account for any gain?
- [ ] Separate development and held-out incidents before tuning. Keep all variants of the same historical incident in one split; avoid answer-pattern leakage through near-duplicate templates.
- [ ] Include meaningful baselines: a simple single-agent document-grounded investigator, the preserved Try 6 system, and the revised system. Use the same model and evidence for the primary mechanism comparison.
- [ ] Test specific components through ablations, such as explicit explanation/evidence requirements, joint-source evidence assembly, and applied revision handling. Change one component at a time where feasible; preserve a fair evidence supply.
- [ ] Expand across distinct incident families and model configurations after the pilot. Run models independently, not as ensembles or hidden fallbacks. Choose case counts and repeated runs using pilot variability and available resources before the main study; there is no magic paper-worthy number.
- [ ] Repeat stochastic runs, present variability and per-case outcomes, and calculate paired comparisons at the incident level. Multiple versions or variants of one incident are not independent incidents.
- [ ] Record tokens, calls, elapsed time, and hardware. Separate gains from extra evidence or extra computation; do not compare a cheap baseline with a much larger run without showing that difference.
- [ ] Test document reordering, duplicate sources, irrelevant context, and controlled contrary evidence while preserving the scenario's intended meaning. Include unchanged-input repeats to distinguish stochastic variability from sensitivity to a perturbation.
- [ ] Use a fixed evidence schedule for the main controlled comparison. If testing question-driven document acquisition separately, give systems the same document inventory and answering policy; record exactly what each obtained.

**Deliverable:** reproducible results across independent cases, with baselines, ablations, variation, costs, and a transparent failure analysis. A successful demonstration alone is not this deliverable.

## F. Reconnect the storyteller as a separate experiment

- [ ] Replace free invention with access to the frozen scenario and releasable documents. Preserve answer provenance and a memory of what has been disclosed. Unknown information stays unknown.
- [ ] Test answer fidelity, consistency, appropriate refusal to invent, and document-release boundaries independently of the RCA investigator.
- [ ] Only then run the combined loop. Keep results distinct from fixed-release experiments so a storyteller failure is not misreported as an investigator failure, or vice versa.
- [ ] Do not make successful storyteller integration a prerequisite for a paper whose main claim concerns the investigator under controlled evidence releases. Include it as a contribution only if its evaluation supports that claim.

## G. Make the paper's contribution clear

- [ ] Draft a precise contribution statement, for example: an evidence-revising industrial RCA method and a progressive-document evaluation setting. Treat this as a candidate claim until experiments establish what improved.
- [ ] Explain the language-processing contribution: combining dispersed documentary evidence, managing uncertainty and contradiction, selecting information needs, and revising causal explanations across turns.
- [ ] Compare with explicit industrial RCA methods and recent agentic diagnosis/evaluation work. Separate adopted ideas, engineering repairs, and genuinely new contributions. Multi-agent orchestration alone is not a demonstrated novel method.
- [ ] Describe dataset construction and the synthetic/real boundary thoroughly. Call scenario keys construction-defined references unless independently validated; do not present synthetic additions as discoveries about the original accidents.
- [ ] Prepare the core figures/tables: system workflow, evidence-release example, V1→V3 board progression, case composition, baseline results, component ablations, quality/cost trade-offs, and representative successes and failures.
- [ ] Support every headline claim with the appropriate experiment. If evidence supports only a narrow capability, narrow the claim rather than promise complete autonomous industrial RCA.

Working paper structure: **problem and contribution → related work → method → case construction → evaluation protocol → results/ablations → limitations and responsible use**.

## H. Reproducibility, privacy, and submission

- [ ] Establish what the partner permits us to use, transform, send to hosted models, and publish. Remove names, IDs, addresses, birth dates, internal URLs, and identifying details from releasable artifacts. Do not assume that a synthetic rewrite automatically removes confidentiality obligations.
- [ ] Document potential harms: incorrect causal attribution, unfair blame, language-related stereotyping, unsuitable corrective actions, and overreliance on an unvalidated tool. Human safety decisions remain outside autonomous model authority.
- [ ] Record model identifiers/digests, inference settings, prompts, code/package versions, release order, dependencies, compute, and all manual interventions. Provide safe reproduction commands and redistributable examples or generators where permissions allow.
- [ ] Document limitations: sparse historical records, unvalidated synthetic realism, evaluator dependence, limited case/model coverage, and no demonstrated safety certification or real-plant intervention benefit.
- [ ] Complete the applicable responsible-research checklist and disclose AI assistance in code, scenario/document creation, evaluation, and writing as required. Prepare anonymized artifacts for review.
- [ ] Verify the exact target venue, submission route, dates, format, and artifact rules from official sources. Do not schedule against the earlier October 12 reference without confirming its year and venue.

ARR explicitly assesses support for scientific claims and reproducibility; a working application is not a substitute for either. See the official [review form](https://aclrollingreview.org/reviewform), [Responsible NLP guidance](https://aclrollingreview.org/responsibleNLPresearch/), and [author checklist](https://aclrollingreview.org/authorchecklist). Submission requirements should be rechecked when the venue is selected.

## Execution order

1. **Code:** A, while constructing the first B package.
2. **Development result:** C, with no storyteller dependency and no need to settle the final judge first.
3. **Assessment protocol:** D, fixed before the held-out study.
4. **Paper experiments:** E. F is separate and included only if needed for the paper's claims.
5. **Paper and release:** G and H, with privacy/permission and research-question decisions addressed early rather than left until submission.

Not part of this phase: fine-tuning, model ensembles/fallbacks, production authentication/deployment, or generating a package for every historical incident before demonstrating that the approach works.

## Supporting material

- [Mechanism proposal](RCA_MECHANISM_REDESIGN_PROPOSAL.md): proposed investigation behavior and source distinctions.
- [Try 6 V1/V2 evidence review](<Try 6/evals/v1-v2-presentation-review/output/Try6_V1_V2_Evidence_Review.md>): recorded failure evidence, not speculation about model internals.
- [AgentRCA](https://arxiv.org/html/2607.22385v1): explicit hypothesis comparison; a diagnosis setting different from full accident investigation.
- [Cloud-OpsBench](https://arxiv.org/html/2603.00468v2): evidence milestones and alternative evidence routes in cloud RCA, adapted rather than copied as industrial ground truth.
- [CausalLink](https://aclanthology.org/2025.findings-acl.1147/): controlled causal environments make evaluation possible, but their results do not establish real industrial validity.

**Completion standard:** evidence that the system makes better-supported, appropriately uncertain, and correctly revised RCA findings across held-out cases—not merely that three versions execute successfully.

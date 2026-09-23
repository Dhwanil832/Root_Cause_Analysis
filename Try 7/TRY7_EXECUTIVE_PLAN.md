# Try 7 — Executive RCA System Plan

Prepared 20 September 2026. Consolidates the code-evolution plan, current-code findings, research rationale and verification requirements.

**Status: core Try 7 application changes implemented; full-plan acceptance is not yet complete.** The isolated app runs at http://127.0.0.1:3017. Previous versions and results remain untouched. See Section 10 for the implementation receipt, test evidence and explicit remaining work. A working app and passing scripted tests are not a claim of zero harness defects or improved model RCA accuracy.

## 1. The objective

Build a reliable industrial RCA system in which we can evaluate the model's ability to understand an incident, combine evidence, ask useful questions and revise causal explanations **without known harness defects distorting the result**.

The harness is responsible for faithfully delivering inputs, executing the intended workflow, preserving outputs, routing answers, applying accepted revisions and displaying the resulting investigation. The model is responsible for the semantic judgments: what a record means, which explanation fits, what remains uncertain, which question matters and whether a causal relationship is justified.

The target is therefore **correct harness execution with observable model behavior**, not simply removing software issues from the report or declaring every remaining failure a model error.

Absolute freedom from software defects cannot be guaranteed. Before a result is used to assess model behavior, the relevant execution path must have no known unresolved harness defect and must pass its integrity checks. A detected harness failure makes the affected conclusion **inconclusive for model attribution**. It remains visible in the experiment record and must be corrected; it is not charged to the model or silently discarded.

Industrial RCA remains the core task: understand the physical system, reconstruct events and conditions, examine interacting causes and protective controls, distinguish explanations, and seek evidence that resolves actual uncertainty. V1 need not identify a final root cause. V2 should make justified changes, not merely produce a larger board.

## 2. What counts as whose error?

| Observed failure | Attribution and treatment |
| --- | --- |
| The model produces a valid question but the application hides it or never routes its answer | Harness failure. Correct the execution path; do not count this as poor model questioning. |
| The model proposes a valid, source-bound correction but the application retains the old statement as current | Harness failure. Preserve the original response and repair revision application. |
| The expected evidence is delivered correctly, but the model misreads a timestamp, invents a fact or proposes an unjustified mechanism | Candidate model reasoning error under the frozen prompt and configuration; substantiate it from the supplied evidence and recorded output. |
| The model incorrectly declares two scoped questions equivalent and the application faithfully applies that proposal | Model judgment failure, provided the prompt/context and merge interface were adequate. Preserve the decision and its effects. |
| The model keeps two distinct question purposes, but application deduplication drops one | Harness failure, not a model merge error. |
| Evidence is absent, contradictory or insufficient in the supplied package | Evidence limitation. Uncertainty is appropriate, not automatically a failure. |
| A provider is unavailable or a request fails because of resource/configuration constraints | Execution/environment failure. Report separately from RCA reasoning quality. |
| The raw model response violates a valid, supported output contract | Model format/compliance failure, recorded separately from substantive RCA quality. First rule out a defective contract, transport truncation or parser error. |
| The record cannot distinguish these causes | Unattributed/inconclusive. Do not speculate. |

A passing unit test does not prove an actual run was correctly orchestrated. The run itself must preserve what was supplied, what the model returned, what the application accepted/rejected and what appeared in the published version. Likewise, correct execution does not isolate a model from all prompt and system-design effects: results describe that model **within the tested configuration**, not its universal capability.

## 3. Starting position

Try 6 already has model-local immutable versions, original-source references, explanation branches, targeted specialist consultations, separate node selection and connection proposals, caching, durable execution and partial publication. Keep these foundations.

Its active flow is source reading → incident framing/tags → selected-node connections → targeted consultations → question resolution/merging → refinement → premise review → connection verification → publication. The older separate tagging/specialist/broker execution chain is not the active planner, although shared helpers remain.

The audit reproduced six behaviors requiring correction before the affected outputs can support fair model assessment:

1. Some connection-review questions are stored but excluded from active question and resolver views.
2. Factual support can appear as a verified barrier without a separate role assessment.
3. Contradicting a wrong timestamp changes its status but provides no completed correction path for current wording.
4. Identical question text can collapse different investigative purposes and retain only the first implication.
5. Opposite strict-precedence proposals can coexist without an admission-time consistency warning; neither is thereby verified.
6. Generic framing retrieval can omit an underlying original document even while its extracted observation is in the notebook.

Additional code-confirmed work includes explicit evidence-impact accounting, answer-subpart coverage and delivery, post-review revision, automatic context decomposition, faithful conflict/status preservation, general release isolation and complete experiment exports.

The planning audit ran 20 existing workflow tests and six characterization probes successfully. The six probes demonstrated existing behavior, not successful fixes. They used deterministic inputs, not live model reasoning. A final comparison found no changes to the 268 fingerprinted Try 6 source/configuration/prompt/test files. These checks do not certify the harness as error-free or demonstrate RCA improvement.

## 4. The proposed investigation loop

1. **Receive the incident and authorized documents.** Preserve default references, starter evidence and later answer attachments as separate source categories within each model's independent track.
2. **Understand the incident.** Identify entities, aliases, functions, locations, time, configuration, reported events and unresolved foundations. Do not assume an unfamiliar component's design or protective function.
3. **Tag and form preliminary explanations.** Select relevant domains and plausible mechanisms. Each explanation records its assumptions, required conditions, evidence for/against it and observations that would distinguish it from alternatives.
4. **Consult relevant specialists.** Each specialist investigates a named uncertainty, but can propose evidence-grounded alternatives or identify an overlooked condition. Kickoff questions remain examples, not an exhaustive script.
5. **Broker the questions.** Combine genuinely shared information needs while preserving every specialist's purpose, scope, expected implication and unanswered subparts.
6. **Fetch answers from released knowledge.** The common answer-fetching stage searches across the specialist knowledge available within that model track. It records exact sources, partial coverage, conflicts and missing information.
7. **Return answers through the broker.** Deliver each answer revision to every affected specialist and explanation. Record receipt and remaining needs; a list of owners alone is not delivery.
8. **Assess evidence impact.** Identify which conditions, assumptions, explanations and existing judgments the new material affects. Record a change, a justified decision to retain, non-applicability or unresolved impact.
9. **Revise and review.** Propose source-bound corrections; apply valid revision operations; reassess factual support, causal roles and connections separately. Review feedback must have a route back into revisions.
10. **Publish the current position.** Preserve an immutable version containing supported observations, provisional explanations, board links, visible unresolved questions and a real before/after change record. Await material new evidence when further progress requires it.

An optional storyteller produces a candidate answer/document release separately. Only the authorized released payload enters RCA. Storytelling and investigation do not depend on each other running simultaneously.

## 5. Consolidated implementation checklist

### 1 — Preserve and isolate

- [x] Archive the actual baseline source, prompts, configuration and previous results, including uncommitted work. Use a consistent database export rather than an unsafe copy of live storage.
- [x] Create the application copy under Try 7 with independent storage, port, worker identity and cache namespace. Do not migrate or overwrite previous experiments.
- [ ] Preserve old snapshots through a conservative read adapter: new assessment fields are unassessed, never automatically successful.
- [ ] Keep credentials out of prompts, shared archives and exports.

### 2 — Make explanations testable

- [x] Extend existing branches with stable conditions, assumptions, applicability, alternatives and distinguishing observations.
- [ ] Preserve equipment/entity identity, aliases, time/interval, location, units and operating configuration as addressable fields.
- [ ] Separate design intent, recorded content, observed incident state and inference. Unknown normal operation becomes a foundation question, not an invented fact.
- [ ] Support explicit branch correction, split, merge, disfavor and withdrawal with lineage. Omission is not deletion; repetition is not corroboration.

### 3 — Bring related originals together

- [ ] Build purpose-specific evidence bundles from relevant source spans, changed evidence, definitions, topology, qualifications and contrary observations.
- [ ] Preserve original offsets, revisions, table headers, media references and source applicability. Summaries help navigation but do not replace the originals needed for judgment.
- [ ] Record what was available, searched, included, omitted, inaccessible and still required. Uploading a document does not prove a decision stage considered it.
- [ ] Extend lexical retrieval with entity/alias/scope/dependency lookup first. Embeddings are optional future work, not a prerequisite for this release.
- [ ] Decompose work exceeding native context capacity into source-bound assessments with explicit reconciliation. Do not silently truncate required evidence or pretend that incomplete joint context was sufficient.

### 4 — Preserve question intent and route answers

- [ ] Separate canonical requests from subscriber-specific investigative purposes. Merge only compatible observations and scopes; record reversible merge/split decisions and reject coverage cycles.
- [x] Track answer coverage per subpart. A supplied measurement does not automatically resolve calibration, configuration or timing questions.
- [x] Preserve answered, partial, conflicting, unavailable, not-found and not-yet-searched states distinctly.
- [x] Route each answer revision through the broker to all affected specialists/branches and retain delivery receipts.
- [x] Give questions from framing, specialists, claim reviewers and connection reviewers the same visible intake and answer path.
- [ ] Reopen affected parts when evidence changes without repeatedly requesting established information.

### 5 — Apply evidence-led revisions

- [ ] Create explicit impact records for new, changed or removed evidence and review feedback. Every identified material impact must be applied, retained with a reason, rejected as inapplicable or left visibly pending.
- [x] Add a focused post-review revision stage. A proposed factual correction must cite originals and receive review; it cannot certify itself.
- [x] Apply revisions against expected target revisions, preserving previous wording, reasons and lineage. Reject stale updates.
- [ ] Invalidate dependent role/link judgments and human approvals when premises change. Keep summary, explanations, board, answer coverage, report and export consistent.
- [ ] Handle missing-node requests and late reviewer questions as explicit work or visible deferrals rather than losing them at a phase boundary.
- [ ] Schedule by material evidence/feedback and target fingerprints. Identical inputs must not create endless reconsideration. Preserve unresolved work when no new basis exists.

### 6 — Separate three different judgments

- [x] Assess **factual support**: does the evidence establish the statement at its actual scope?
- [x] Assess **causal role**: is this an event, condition, protective function, action, requirement or context? A true status indication is not automatically a barrier.
- [x] Assess **connection validity**: are mechanism, direction, scope and alternatives justified? Two supported endpoints do not establish causation.
- [x] Add integrity checks for invalid endpoints, stale premises and contradictory strict precedence between the same event instances. Do not impose ordering when time is unknown or ban legitimate time-scoped feedback.
- [x] Represent joint physical conditions separately from alternative sufficient evidence bundles. Parallel arrows or a relation label alone do not establish an AND-cause group.
- [ ] Preserve partial, contradicted, conflicting, unknown and invalid-execution states. Flag inconsistent verdicts instead of silently changing their meaning. Human acceptance remains independent.

### 7 — Publish usable, honest versions

- [ ] Publish useful independent work even if another item fails. Quarantine the failed item visibly; never promote its evidence status to finish a version.
- [ ] Distinguish execution completion, a published working position, awaiting evidence and established RCA conclusions.
- [ ] Show current assumptions, conflicting evidence, outstanding questions, merged/skipped requests and why the board changed.
- [ ] When foundations are unusable, show the blocker. If displaying an earlier position, identify its version and stale dependencies explicitly.
- [ ] Keep event/barrier labels as metadata rather than sentence prefixes. Canvas layout changes must not regenerate analysis.
- [ ] Generate canvas, report and export from the same committed snapshot. Corrective actions stay linked proposals requiring human approval, not executable plant instructions.

### 8 — Control releases and export the whole experiment

- [ ] Add package/release manifests for default, starter and later evidence, including corrections and withdrawals. Later versions need not become more certain.
- [ ] Bind releases to model track, expected parent version and payload hash. Reject stale batches and make repeat application idempotent.
- [ ] Allow fixed document/answer releases without invoking the storyteller. Preserve storyteller candidates separately from released material when testing both systems.
- [ ] Export released originals/extractions, questions/subparts/merges, answers/deliveries, explanations, boards, revision operations, validations, errors and human decisions.
- [ ] Include source/model/configuration/prompt/schema identities, actual supplied evidence, raw stage outputs, accepted/rejected transformations, timing and usage. Keep private chain-of-thought unnecessary and secrets excluded.
- [ ] Replay saved outputs to verify application behavior without inference. Treat a fresh model rerun as a separate experiment, not guaranteed deterministic replay.
- [ ] Keep independent evaluation records separate. Human-versus-LLM assessment remains undecided; internal review badges are not external performance scores.

### 9 — Enforce private-answer separation

- [ ] Keep hidden scenario truth, expected outcomes, future releases and grading notes in controller-only storage/access paths.
- [ ] Admit only explicitly released inputs before registration, retrieval, media loading, caching and context construction. A “private” filename or warning prompt is not access control.
- [ ] Prevent investigator tools/routes from accessing controller storage or scenario endpoints. Do not rely on logical separation inside a shared application alone.
- [ ] Test cross-model isolation and private/future-evidence canaries in payloads, traces, exports, errors and browser-delivered content.
- [ ] Treat uploaded instructions as untrusted evidence; documents cannot grant access or change release policy.

### 10 — Verify the harness, then assess model behavior

- [ ] Retain baseline regression coverage and add focused checks for every changed execution contract.
- [ ] Test persistence, compatibility, source delivery, merge fidelity, partial coverage, routing, revisions, role/link states, partial publication and release isolation.
- [ ] Run normal type/build checks and targeted interface checks, then move promptly to the controlled model pilot. Avoid another prolonged sequence of unrelated model preflights.
- [ ] Freeze the model/prompt/package configuration. Run one model and incident at a time with no fallback and no manual correction of model verdicts in a scored run.
- [ ] Record the origin of each failure using the attribution rule in Section 2. Preserve inconclusive and invalid runs; do not conceal them or fold them into model RCA accuracy.
- [ ] Before held-out evaluation, freeze the independent assessment protocol. Deterministic integrity checks do not automatically judge arbitrary causal prose.

## 6. Code organization and integration responsibilities

Maintain one clear routing entry, separate responsibilities and section-specific prompts. A module does not imply a separate LLM agent.

| Responsibility | Existing foundation / proposed location under the application |
| --- | --- |
| Routing and durable execution | Retain `src/orchestrator/main-router.ts`, `src/engine/tasks/`, `src/server/engine-repository.ts`. |
| Incident framing and coordination | Extend active `src/engine/investigation/`, not the inactive legacy execution chain. |
| Scoped explanations and conditions | Add `src/engine/explanations/`; extend investigation/domain contracts. |
| Original evidence assembly | Add `src/knowledge/bundles/`; extend registry, retrieval and context planner. |
| Canonical needs, answer coverage and delivery | Add `src/engine/questions/`; integrate existing broker/resolver helpers. |
| Evidence impact and validated revisions | Add `src/engine/revisions/`; integrate finding history and dependency invalidation. |
| Role/link checks and structural integrity | Add `src/engine/validation/`; retain literal evidence review. |
| Consistent publication and UI | Extend `src/engine/board/`, `src/domain/types.ts` and `app/incident/`. |
| Released inputs and reproducibility | Add `src/experiments/`; extend artifacts/export; keep private controller access separate. |
| Optional simulator | Retain separate `src/story-agent/` queue and release flow. |

Keep prompts grouped by investigation-map, targeted-consultation, question-broker, evidence-resolution, evidence-impact, investigation-revision, claim-review, causal-role, connections and causal-verification. Each states the investigative purpose, trusted/untrusted inputs, allowed changes, uncertainty treatment, output contract and brief reviewable rationale. Examples guide style; they do not prescribe every question.

Whenever a contract changes, update its schema, prompt registration, task dispatch, reference binding, persistence, cache identity, projection and fixtures together. Preserve question IDs/attachment associations, invalidate affected human approvals, keep old snapshots readable, and update canvas/report/export status semantics together. These are integration obligations, not optional cleanup after the pilot.

## 7. Research informing the mechanism

The following source summaries were checked during the 20 September planning audit. Transfers to our setting remain proposals to test; cited preprints are not represented as peer-reviewed guarantees.

| Work | Mechanism to borrow | Boundary |
| --- | --- | --- |
| [AgentRCA](https://arxiv.org/html/2607.22385v1), 2026 preprint | Maintain explanations against evidence and interpret observations against applicable operating conditions. | Its hypothesis-table intervention did not help every model; its diagnostic tools and operating data differ from our records. Do not import a fault catalog, claimed accuracy or iteration limit. |
| [MA-RCA](https://link.springer.com/article/10.1007/s40747-025-02096-0), *Complex & Intelligent Systems* | Convert hypotheses into verification tasks, deduplicate shared evidence work and invalidate stale results. | Shared retrieval must preserve each hypothesis's purpose. Historical similarity is not proof of the current cause. |
| [Cloud-OpsBench](https://arxiv.org/html/2603.00468v2), 2026 preprint | Frozen evidence snapshots, dependencies and alternative admissible evidence bundles. | Its expert-reviewed annotations are not something we already possess. Hidden expected milestones must not guide the investigator. |
| [DiagGuard](https://arxiv.org/html/2608.21310v1), 2026 preprint | Separate grounding from verification; trace evidence that was unavailable, misread or not used. | Microservice fault-localization results do not establish industrial causal-board quality. |
| [LangGraph persistence documentation](https://docs.langchain.com/oss/javascript/langgraph/persistence) | Checkpointed state and durable recovery as infrastructure. | Try 6 already has a suitable persistence foundation. No framework migration or cross-model knowledge sharing is proposed. |

Our contribution to demonstrate is evidence-led **industrial causal investigation over successive releases**, not more agents, a particular library, a larger graph or successful JSON generation.

## 8. Execution order and acceptance gates

| Batch | Deliverable | Gate |
| --- | --- | --- |
| 1 | Isolated application copy, baseline preservation, versioned contracts and private/public boundary | Existing results unchanged; no private inputs enter investigator registration. |
| 2 | Scoped explanations and joint original-evidence delivery | Required evidence is supplied or an explicit limitation remains; assumptions are not silently facts. |
| 3 | Correct question merging, partial coverage and broker delivery | Different purposes survive; every affected owner receives the answer revision. |
| 4 | Revision processing and separate fact/role/link validation | Accepted corrections reach all current views; changed dependencies reopen; unaffected work survives. |
| 5 | Consistent publication, controlled releases and complete exports | Canvas/report/export agree; releases are scoped, idempotent and replayable. |
| 6 | Focused integration verification and actual RCA pilot | No known unresolved harness defect on the evaluated path; remaining failures are evidence-attributed, not assumed to be model errors. |

Focused regression scenarios must include: immutable old versions; interrupted-task resume; reviewer-question visibility; same wording with different scopes; shared subpart delivery; partial/conflicting/unavailable answers; multi-document evidence; native-context decomposition; sourced timestamp correction; condition-level impact; unchanged-input reuse; status-indication versus barrier role; opposite strict precedence; joint causes versus alternative evidence bundles; source withdrawal after human acceptance; inconsistent reviewer output; stale/duplicate releases; hidden canaries; export/replay consistency; and legacy snapshots with unassessed new fields.

Use scripted outputs to test whether the harness performs the intended transitions. Separately use real model outputs to test whether the model proposes the right transitions. Do not blur these two results.

## 9. Controlled pilot and what remains out of scope

The first development package should have a defensible preliminary V1 target, a discriminating V2 evidence release and a V3 correction/contradiction or deeper-context release. Expected outcomes stay private. Preserve which details come from historical records, which are synthetic and which are genuinely unknown; partner document examples guide format, not incident truth.

Success means the model accurately uses what is available, corrects or narrows explanations where warranted, preserves useful unaffected branches, identifies real residual uncertainty and does not invent deeper causes. An incomplete board can be correct. More nodes, more questions and higher confidence are not success measures by themselves.

Optimize through unchanged-read reuse, per-track shared evidence collection, dependency-based reconsideration, selected-premise review and scoped context. Preserve the full archive. Do not impose arbitrary question/claim/token quotas; physical context capacity and input-integrity safeguards still exist and must be handled transparently.

No fine-tuning, ensembles, silent fallback, case-specific production answers, forced canned question wording, mandatory storyteller, mandatory vector database or framework migration is included. Full production authentication remains separate from the necessary experiment-access boundary. The choice of human or LLM evaluator is deferred, not silently made by the harness.

**Bottom line:** correct the known harness defects and make execution auditable first; then evaluate model RCA behavior on that verified execution path. Never use “the tests passed” as permission to blame the model for an unexamined failure.

## 10. Implementation receipt — 20 September 2026

### Running application and preserved baseline

- App: `Try 7`, engine `try7.1.0`, port **3017**, independent project-local D1/R2 state and per-track cache. Start with `npm run dev` from this folder. The command applies only this app's local migrations and launches its web process and authenticated worker.
- Backup: `../.rca-baselines/try6-before-try7/` contains `source-and-results.tar.gz`, a consistent `investigations.sqlite` backup, a consistent `evidence-metadata.sqlite` backup, and `original-evidence-blobs.tar.gz`. Credentials were not intentionally copied into the application or exported inputs.
- Rechecked all **268** baseline source/prompt/configuration/test fingerprints against the planning manifest: **zero changes in Try 6**.
- Try 7 does not migrate old paused engine checkpoints. The legacy-migration test now explicitly verifies refusal and preservation, not an unsupported cross-engine recovery.

### Implemented behavior

1. **Scoped explanations:** applicability, assumptions, required conditions, distinguishing observations and successor lineage. Explicit withdrawal and split/combine predecessors remain recorded.
2. **Original evidence:** framing/refinement receive original passages, not just an extracted notebook. Other stages assemble target/branch/answer dependencies plus related retrieval. Source offsets, revisions, inclusion/omission and call-local reference bindings are preserved in traces.
3. **Question ledger:** same wording with a different decision is not silently collapsed. A semantic merge checks asset/location/time, preserves all owners, purposes, implications and parts, and rejects coverage cycles.
4. **Answer coverage and delivery:** answered subparts retain original citations; missing calibration/timing portions remain partial. Every answer revision has owner-specific delivery receipts and an implication response. Reviewer questions receive a late resolver pass; genuinely later requests remain visible, not silently answered.
5. **Evidence revision:** source-bound corrections use expected finding revisions, retain prior wording and reopen fact/role/link reviews and affected approvals. A correction disposition cannot claim success when the correction failed admission. A focused revision stage is followed by independent re-review.
6. **Separate judgments:** factual support, causal-role validity and relationship validity are distinct. A supported gauge reading is not automatically a verified protective barrier. Strict-precedence cycles are flagged; ordinary physical feedback is not banned. Joint condition groups have explicit member IDs and premise dependencies.
7. **Publication/UI:** useful partial positions survive independent failures. Canvas and reports display fact/role status; question cards display coverage, subscriber purposes and delivery receipts. Evidence-impact decisions and pending impacts are visible. Withdrawn documents are excluded from current-version views and later admission, while historical associations remain preserved.
8. **Controlled releases:** manifests bind track, expected parent, source inventory and payload hash. Repeated release IDs with the same payload replay the existing receipt; changed payloads and stale parents are rejected. `/api/tracks/:trackId/releases` supports controlled answer batches and source withdrawals.
9. **Experiment export:** `/api/tracks/:trackId/export` exports frozen inputs and extracted originals, snapshots, state, questions, revisions, task events, prompts/contracts, evidence packets, reference bindings, raw responses and usage. `?format=zip` also includes available original binary files with digest checks; missing originals are explicitly listed and mark the archive partial. Secret-valued configuration fields are redacted. Exports are explicitly unscored.
10. **Failure attribution:** known context-admission failures are reported as harness limitations, provider/connectivity failures separately, and generic exceptions remain unattributed. The execution gate can say `execution-inconclusive`; it never declares an arbitrary software exception a model reasoning defect.
11. **Private controller boundary:** automatic storyteller dispatch was removed. Private scenario/template endpoints return HTTP 410 and do not import scenario storage into the investigator route. Controller-only/future/cross-model sources are rejected before registration. The historical storyteller source remains preserved, but a separately hosted Try 7 controller is **not** implemented.
12. **Question identity versus wording:** follow-up directions have an explicit `existingQuestion` reference, separate from readable question text. Reuse preserves the original wording and all subscriber decisions; scope changes cannot silently reuse the same request. Known old Q/subpart references are bound through the exact call catalog rather than displayed as new question text. Genuinely added subparts reopen search and cannot retain a fully answered badge.
13. **Prompt consistency:** removed legacy instructions that restricted F/Q references to fields inconsistent with the active schemas. The shared prompt now explicitly distinguishes untrusted instruction authority from source credibility; source content must be judged at its actual scope, not rejected merely because it cannot issue instructions.
14. **Assignment-constrained generation:** resolver/recipient answer IDs are constrained to their actual assignments, while other canonical questions remain available only for context/equivalence. Covered requests no longer appear as new candidates. Output cardinality matches the assignment, not an arbitrary investigation-wide question limit.
15. **Revision bookkeeping and honest narratives:** correction grammars bind each finding to its saved expected revision. The stale-write reducer guard remains. If revision items are rejected, their generated success narrative is retained separately instead of becoming the current summary. Older snapshots show an explicit narrative warning rather than being rewritten. A new owner subscribed during revision receives its available answer before publication. The UI offers task retry only when a failed/blocked task actually exists.

### Verification record

The following are deterministic harness checks, not model performance scores:

| Check | Result |
| --- | --- |
| `npm run test:engine` | 20 passed |
| `npm run test:try7` | 24 passed |
| `npm run test:regression` | 37 passed |
| `npm run test:capacity` | 16 passed |
| TypeScript and application build | Passed |
| Lint | No errors; one inherited unused-variable warning in a preparation script |
| Local D1 migrations and worker startup | Passed on isolated port 3017 |
| Browser check | Home, installed model picker, isolated history and live investigation dashboard loaded; corrected question titles and export controls verified |
| Live HTTP checks | ZIP export returned HTTP 200 and a readable manifest; both private story/template endpoints returned HTTP 410 |

The **97 total checks** include 24 Try 7-specific cases and a full durable read → wrong timestamp → contradictory review → sourced correction → independent re-review → committed snapshot/export path. Both the original and corrected assertions are retained; the test does not count a source-bound correction as automatically supported. Other checks cover branch lineage, explicit joint requirements, merged partial answers, late reviewer delivery, binary export, question-reference reuse, assignment-constrained generation, audited reference-only checkpoint recovery, rejected-revision narrative handling, bound revision metadata and post-revision owner delivery.

A separate **unscored** Qwen smoke run was started with a short pneumatic-carriage incident to exercise the real provider, schema and dashboard path. It uses no injected provider output and no forced verdict. Track: `a86227ac-0690-4bfd-b5f7-749f002baed3`; V1 run: `5678abb7-4870-4ef6-b091-4bf6ac552aac`. It is not the historical incident benchmark.

The live check exposed a harness contract defect that scripted tests had not covered: the answer-recipient returned `Q1`/`Q2` in direction wording, and the reducer admitted them as new questions, displaying internal reference markers. This is not recorded as a model RCA failure. The contract and reducer now distinguish existing identities from new wording; three focused tests reproduce and verify the fix. The run was paused, the two unpublished reference-only duplicates were rebound on explicit resume, and original response/before-state records were retained. No causal judgments or supplied evidence were edited. One in-flight provider call was cancelled by that deliberate pause and remains in the trace.

Because code/prompt changes and a recorded checkpoint repair occurred during this development smoke run, it is **not a frozen-config performance experiment**, even if execution completes. Its execution outcome must be recorded separately; scripted tests above must not be substituted for that result.

The late-answer stage also returned unsolicited answers for catalog questions outside its assignment. The reducer rejected those extras and retained applicable siblings; it did not overwrite other answers. The generation grammar has now been narrowed to assigned answer/receipt IDs, with a regression test that preserves non-assigned equivalence candidates. These earlier rejected outputs remain in the smoke run's quarantine and are not retroactively relabeled successful.

#### Observed smoke outcome

Published at **20 September 2026, 8:17:54 PM America/Chicago** (`2026-09-21T01:17:54.909Z`). The run is terminal; it is not still processing.

| Observed item | Result |
| --- | --- |
| Scheduled tasks | 21 completed, 0 failed/blocked whole tasks |
| Version | V1 committed as **partial** |
| Board | 5 selected observations plus focal event; 0 causal links |
| Visible current questions | 3 |
| Rejected output items | 20 preserved |
| Answer delivery receipts | 1 pending in this historical snapshot |
| Gate | **execution-inconclusive**, not a model-performance score |
| Snapshot consistency | Final engine snapshot exactly matched the committed version snapshot |

Rejected items: 10 unassigned answer entries; 1 uncited answered subpart; 1 omitted assigned answer; 1 mismatched recipient response; 2 question-scope reuse violations; 4 stale expected-revision values; 1 attempted rewrite through an existing question identity. This is an observation log, not a blanket attribution of those failures to the model.

The final audit found that revision could subscribe a new owner after the earlier delivery phase; the one pending receipt exposed that harness gap. The planner now delivers at the post-revision stage as well, with a focused regression test. Four rejected corrections also exposed generated narration that falsely described success: future revisions now retain that narration separately, and the UI/report label historical narrative as provisional. Expected revision numbers are now bound in generation to the saved finding revision, rather than left to model bookkeeping. A retry control that could not act on a partial run with no failed whole task was removed in that situation.

These post-run fixes passed scripted checks but have **not** been validated by a fresh frozen-config model run. The committed smoke snapshot and its failures were not edited. The smoke validates that real provider calls reached partial publication and exposed actionable harness issues; it does not satisfy the controlled pilot gate or prove improved RCA quality. Some semantic judgments were also questionable—for example, the role reviewer rejected an event using the absence of a protective function as its rationale. Such behavior requires a separately frozen, evidence-grounded evaluation, not a manually substituted verdict.

### Explicit remaining acceptance work

This is a core implementation checkpoint, not completion of every checklist item:

- **Automatic native-context decomposition and reconciliation:** not implemented. Required joint originals currently fail closed when they exceed native capacity; they are not silently omitted. Very large packages therefore remain outside the verified path.
- **Separate storyteller/controller service:** intentionally not connected. Use released documents/answers directly; do not load private truth into the investigator app.
- **Question unmerge/split operations:** merges preserve constituent needs and history, but a first-class reversible split operation remains to be added.
- **Automated replay:** JSON plus a binary ZIP archive are implemented. A complete end-to-end saved-output replay command remains to be added; exporting raw responses is not itself proof of deterministic replay.
- **Broader semantic/state acceptance:** entity/alias/topology retrieval, condition-level dependency coverage, and revision consistency across all narrative fields need additional focused cases. Passing the timestamp case does not prove every revision is correct.
- **Controlled V1→V2 model pilot and independent evaluation:** not replaced by unit tests or the small provider smoke case. Freeze the actual package/model/prompt configuration before scoring.

Until these gates are addressed, do not describe Try 7 as having no harness gaps or attribute every remaining failure to the model.

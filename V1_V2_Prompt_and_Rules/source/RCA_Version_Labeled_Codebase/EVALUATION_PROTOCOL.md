# RCA V1 versus V2 evaluation protocol

## Research questions
Q1: With the same model/tool environment, do task-specific V2 prompts change compliant, source-grounded model outputs versus a basic five-agent prompting baseline?

Q2: Holding prompts constant, do V2 frontier/route/assessor procedures increase useful causal coverage or prevent inappropriate evidence commitments at comparable cost?

Q3: Are improvements robust to camera corrections, late records, unknown custodians, misleading operations manuals, partial responses, and genuinely unresolved roots?

## Execution protocol
1. **Freeze** the model ID/temperature/provider routing and record prompt hashes, source manifest hash, execution code revision, all actual HTTP responses, timestamps, cancellations and failed attempts. A model alias may change invisibly, so pin a provider snapshot when possible.
2. For each incident run each configuration from a fresh, identical initial report and identical permissible source/custodian environment. Hide future documents and reference RCA answers. Sources must be acquired by information need, not privileged source ID. Count unsolicited corrections separately.
3. Compare `prompt_only`, `prompts_only`, `methods_only`, `full`. Keep the model fixed per experiment. Repeat non-deterministic trials with matched budgets, and report calls/tokens/timeouts/latency/rejections rather than silently resampling.
4. Evaluate at two levels: **controlled one-step packets** with identical evidence for component ability; **connected investigations** with actual, potentially different subsequent evidence exposure. Do not conflate them.
5. Save the full run and `evaluation_report.json` (structural measurements only). Export `manual_review.csv` and have a reviewer blind to configuration inspect asset/time scope, quote-to-claim entailment, causal warrants, independence, missing needed conditions, evidence requests and unsupported root claims.
6. Compute per-incident rates (not per individual quotation as independent cases), paired comparisons across incidents and confidence intervals. Keep related versions of one incident clustered.

## Evaluation labels
- **Supported observation**: the source genuinely documents that an observation/report was made, within the appropriate scope. This is not necessarily physical causal truth.
- **Correct causal contribution**: the premises and warrant, including necessary joint conditions, support the indicated causal path at the represented uncertainty level.
- **Unsupported commitment**: a model/ledger claims a physical fact, direct causality or closure that the released evidence does not justify.
- **Correct revision**: corrected source support is withdrawn, independent support is preserved and corresponding information needs reopened when their coverage is invalidated.
- **Useful request**: an admissible, nonredundant, sufficiently scoped investigation that might test a real causal uncertainty; successful delivery and actual diagnostic value are distinct measures.
- **Access outcome**: request delivered, partial, unavailable, permission-blocked, exhausted or waiting; none equals physical refutation.

## Human review checklist
Review each output claim and causal link with *actual delivered source text*. Do not grant credibility just because the source quote exists, or because an LLM judged itself. For difficult physical-causation questions obtain a domain expert, not only an LLM judge. Record disagreements and reconcile without exposing the benchmark answer to the investigator.

## Baseline fairness considerations
The initial two-role non-generative baseline is not equivalent to the user's intended five-agent basic prompting setup. The new `prompt_only` profile invokes all five. Action counts and evidence exposure can still diverge; that difference is an outcome of the connected policy, not a controlled component-wise accuracy comparison. If prompt token lengths differ materially, additionally report token usage and provide a strong succinct baseline prompt written to the same schema.

## Corpus design after the prototype
Use independently sourced incident narratives with evidence appropriate to the mechanism; separate development and held-out industries; include late or corrected records, divergent reports, unavailable evidence and unresolved origins. Gold/reference conclusions remain author-only and must be engineering-reviewed. The current wet-floor fixture is a toy development case; its six invariant checks are not a statistical evaluation.

## Expected deliverables after real trials
- complete traces and source-release audits per model/run;
- fixed-input component scores with valid/invalid/held responses separated;
- incident-level causal support, unsupported-commitment, useful-request and revision scores;
- per-run tool/request/token/time budgets, refusal/rate limit failures and partial-status counts;
- ablations showing the marginal effect of prompts and each V2 mechanism;
- human-expert provenance/causal assessment, confidence intervals and documented counterexamples.

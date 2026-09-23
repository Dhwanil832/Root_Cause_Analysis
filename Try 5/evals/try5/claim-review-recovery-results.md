# Five-claim Qwen review diagnostic — observed results

Completed September 18, 2026, approximately 9:57 PM Central.

## Outcome

All five real model calls completed with valid structured responses, without a
timeout, truncation, repetition abort, reference-ID rejection or model fallback.
The same production executor, claim-review prompt, schema, retrieval and result
application were used. Model: `ollama:qwen3.5:latest`, frozen digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
Total provider time: 141.69 seconds.

**The reviewer failed to reject both overclaims.** It correctly supported three
narrow record observations, but also gave unsupported causal significance to one
of those. This is a small diagnostic, not an overall RCA score or model ranking.

The live application remains paused at generation 49 with 73 proposed findings,
16 questions, and no causal nodes/edges. Its input, state and snapshot hashes
are unchanged. The diagnostic did NOT commit these verdicts, supply answers,
modify evidence, or advance the live investigation. It tests the current reviewer
ahead of the 26 remaining specialist tasks, without changing their scheduling.

## Results against prewritten expectations

| # | Proposition being checked | Actual verdict / role | Assessment |
| --- | --- | --- | --- |
| 1 | No temporary instruction attachment is present | Supported / barrier | **Fail.** Equates a blank field with an absent attachment. It had both the cover and the convention explicitly saying the reason for an empty field needs other evidence. |
| 2 | Work package records exclude valve/pressure information | Supported / requirement | **Fail.** Treats a list of required contents as an exhaustive list. §5.1 requires ECP revision and acceptance status; it does not prohibit other records or establish their absence. |
| 3 | Work was still at preparation stage, not maintenance release | Supported / condition | **Evidence-verdict pass.** Cites the actual cover as well as the directory, repairing the specialist's insufficient citation. Preparation phase is supported; whether physical isolation was adequate remains unproved. |
| 4 | WO-527-E is blank at issue and is a field execution record | Supported / context | **Pass.** Preserves the recorded issue-time status and does not treat this document metadata as a physical incident cause. |
| 5 | Cover lists Revision 3 and a blank temporary-instruction field | Supported / condition | **Evidence-verdict pass; routing concern.** The statement is supported, but causalRelevance shifts to a potentially missing required safety document and non-compliance without establishing applicability or absence. |

The model's statuses and the production application's effective statuses were all
`supported`. Each response had at least one valid source ID and no opposing IDs,
so the application did not downgrade it. Valid reference IDs did not establish
that the cited text supported every part of the proposition.

## Concrete inconsistency in review 1

It asserts that no attachment is present is fully supported, then asks whether
the blank field indicates a missing attachment or an unapproved document. Its
question says that distinction is unknown without further evidence. The stated
uncertainty directly affects the absence claim being marked supported.

The question also says the cover notes either explanation. It does not: these
alternatives came from the earlier specialist's interpretation, included in the
target's qualifiers. This establishes misattribution in the output; it does not,
by itself, prove which input field caused the model's mistake.

Review 2 similarly asks whether the missing data was never recorded while still
approving the broad exclusion claim. Its summary explicitly relies on the idea
that the requirement list implies exclusion of other data. That implication is
not established by the source.

## What this establishes—and does not

- The output transport and scoped execution now complete this workload.
- For these two failures, the necessary original text and limiting conventions
  were present in the model packet. This is not explained by missing retrieval
  or a token ceiling in these calls.
- The reviewer can locate and cite direct record observations, including fixing
  an inadequate original citation in case 3.
- It cannot yet be relied upon to distinguish a narrow recorded fact from a
  stronger absence/exclusivity claim. It can recognize uncertainty in a question
  without reflecting that uncertainty in its verdict.
- Result application currently trusts the model's whole-claim verdict once source
  IDs resolve. It checks no structured list of unsupported claim parts or
  unresolved premises that should prevent full support.
- The causal mapper/verifier was not exercised here. Do not claim this diagnostic
  proves a bad final causal board; it proves these overclaims pass claim review
  and are eligible for downstream causal consideration.

## Next targeted change to test

Require claim review to separate the proposition into checkable parts, state what
the original evidence actually establishes for each part, and identify any extra
inference or unresolved premise. The application should derive full support only
when every necessary part is supported, instead of accepting an independent
top-level verdict that can contradict its own gaps. Keep causal-role assessment
from silently turning a document observation into a missing physical barrier.

This is a proposed change, not a proven solution. First test it against the same
five frozen cases (especially retaining correct support for cases 3–5), then
use independent absence, requirement-alternative and scope examples before
claiming generalized reliability. Do not patch in incident-specific word rules
or manually change these saved model verdicts.

## Reproducibility

- Expectations: `evals/try5/claim-review-recovery-expectations.md` (written before calls).
- Driver: `scripts/review-saved-findings.mjs` (read-only application DB).
- Full generated traces: `outputs/claim-review-check-Fk3szZ/`.
- Each `NN-request.json` records exact prompt, model, packet, selected original
  evidence, grammar, context and allowance. Each `NN-stream.txt` retains raw
  output; `NN-provider.json` and `NN-outcome.json` retain provider and effective
  application results. `manifest.json` and `summary.json` document state
  preservation. No expectation file or earlier diagnostic result enters a request.

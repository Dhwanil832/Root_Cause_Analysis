# Claim-parts review: criteria frozen before live checks

These are narrow reviewer behavior checks, not a new industrial RCA or a general reliability score. The fresh cases are fictional. Their inputs contain only neutral identifiers, a target statement and source text; this answer key is never passed to the model. Use the production prompt, context selection, provider, schema and application rule, with the same installed Qwen digest. No cross-case memory, cached result, storyteller or fallback model.

## Saved five-finding regression

The previously saved expectations in `claim-review-recovery-expectations.md` remain authoritative. Findings 1 and 2 must not be fully supported: blank documentation does not establish missing equipment/documents, and required record fields do not prove an exhaustive inventory. Findings 3, 4 and 5 should remain supported at their actual scope. Findings 4 and 5 describe record content and must remain context, not an established incident mechanism. Finding 3 requires the actual package/log evidence, not merely the generic directory.

## Fresh cases

| Case | Expected effective result | What must be distinguished |
|---|---|---|
| 01 | supported, actual condition | Direct observation supports a scoped negative. Do not reject all absence statements. |
| 02 | unknown (not supported) | Same negative wording, but only a blank field is supplied. |
| 03 | unknown (not supported) | An observation after intervening work does not establish the earlier state. Not contradicted: neither earlier state is established. |
| 04 | contradicted | A positive torque entry contradicts the claimed absence; minimum required fields do not exclude extras. |
| 05 | contradicted | An explicitly sufficient alternative was met. No temporary instruction is not, by itself, a breach of this OR rule. |
| 06 | supported, context | The log observation is established even though its cause is unknown. An exploratory why-question must not block it. |
| 07 | conflicting | Two unresolved measurements of the same port/time cannot establish one as the true pressure. |

No silent partial credit: report exact statuses and errors. Review quotations, coverage and causal role as well as whole-claim labels. Count a supported result as a failure when it rests on an unsupported inference, even if its JSON is valid. Conversely, rejecting every claim is a failure on the positive controls.

## Resume condition

All five saved cases and seven fresh cases must meet these scoped checks before resuming the application checkpoint. Otherwise preserve the traces, keep the investigation paused and diagnose the observed failure. These cases are necessary evidence for this change, not proof that all future reviews are correct.

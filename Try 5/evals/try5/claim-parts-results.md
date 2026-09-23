# Claim-by-claim review implementation and live Qwen evaluation

Date: 2026-09-19. This is a focused reviewer diagnostic, not a final RCA or a model ranking.

## Decision

**Do not resume the full investigation yet.** The latest five-finding regression still approves one overclaim. Valid structured output, valid source references and passing code tests do not establish semantic correctness.

The live investigation is preserved at run `da57d29d-cf54-4c29-85ae-54260ef92dcd`, track `28f74b32-2564-4765-852f-1f3fc0c8f367`, generation 49. It has 73 proposed findings, 16 questions and no causal nodes/edges. No diagnostic verdict has been committed to it, no new incident evidence supplied, and the storyteller remains disconnected.

## Implemented

- Independent reviewer input: exact target statement plus original evidence, without the producing agent's classifications, interpretations, approval labels or obsolete source IDs.
- A separate review of every necessary claim part, including narrower evidence meaning, counterexample, missing premises and prerequisite questions.
- Application-derived whole-claim status: all necessary parts must pass for full support. The model cannot override this with a separate summary verdict.
- Source/line references constrained during generation to existing, nonblank lines. The application copies original text, rather than asking the model to reconstruct quotations.
- Exact target-word coverage, preserving negatives and qualifiers. Invalid lines or a recognized unresolved premise cannot approve a part.
- Evidence-ledger display of individual parts and original lines; raw model traces retained separately from effective application decisions.
- Claim/evidence revisions invalidate stale reviews. A later causal verifier cannot promote a partially supported finding into a supported cause.

The review policy is `claim-parts-v3`. The checkpoint engine version stays `try5.2.1`; review policy, exact prompt and grammar participate in cache identity. Completed reading/tagging/specialist tasks are not discarded or rerun by this change.

## Fixed model and experimental boundary

All calls used `ollama:qwen3.5:latest`, digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`, context 32768, temperature 0, thinking disabled as in the preserved run. No fallback, model combination, manual approval or hidden answer key was used. Calls were sequential. The production executor/provider/schema/result application ran against cloned state; the application SQLite connection was read-only.

Expectations were recorded before the first live calls in `claim-parts-expectations.md`. The five original propositions and original sources were unchanged. The seven separate fictional cases initially served as fresh checks; after their first results informed revisions, they became regression cases. They must not be represented as an untouched held-out evaluation of the final prompt.

## Five saved findings: final policy

| Finding | Required result | Observed final result | Assessment |
|---|---|---|---|
| 1. No temporary instruction attachment is present | Not fully supported | supported / context | **Fail.** Still converts a blank field into an absence claim by interpreting the target as record content. |
| 2. Work package excludes valve/pressure records | Not fully supported | partial / context | Pass on the decisive distinction: required record fields and this excerpt do not establish all package contents. |
| 3. Preparation stage, not yet maintenance release | supported | supported / context | Evidence verdict retained. The reviewer classifies this as a record observation; causal-stage usefulness was not tested. |
| 4. WO-527-E blank at issue, field execution record | supported / context | supported / context | Valid record observation retained. |
| 5. Revision 3 shown and temporary-instruction field blank | supported / context | supported / context | Valid record observation retained without asserting the physical absence of an attachment. |

This is 4/5 expected whole-claim outcomes, **not** an 80% overall RCA score. The remaining failure is safety-critical for this evaluation: it is exactly the gap between absent documentation and an absent item.

In finding 1, the final model's reason says the blank field “corresponds to the absence of a temporary instruction attachment in the record.” But the original target says no attachment **is present**, not simply that none is recorded. Both parts were labeled entailed and the model supplied no blocking counterexample. Consequently the application gate had no recognized semantic gap to act on. The references resolve correctly; the error is the interpretation of the claim, not missing retrieval or an invalid source ID.

## Iterations retained, including failures

| Policy | Saved five, in order | Seven fictional cases, in order | Observed issue |
|---|---|---|---|
| claim-parts-v1 | partial, partial, supported, unknown, supported | supported, unknown, unknown, unknown, unknown, supported, unknown | Two overclaims blocked, but one mainly because Qwen spliced non-adjacent text into an invalid quotation. A valid table observation was also rejected. |
| claim-parts-v2 | partial, partial, supported, supported, partial | unknown, unknown, partial, unknown, unknown, supported, unknown | Original-line selection removed quote reconstruction, but unconstrained line numbers could be invented. A different-record hypothetical incorrectly blocked a valid same-record claim. |
| claim-parts-v3 | supported, partial, supported, supported, supported | supported, unknown, unknown, unknown, contradicted, supported, unknown | Closed source-line grammar fixes reference validity. Scope clarification restores the valid record claim but the physical-absence overclaim returns. |

The `partial` result on fictional case 3 identifies the reported movement as supported while leaving earlier bolt absence unproved. It is not the exact prewritten `unknown` label; it does **not** approve the timing overreach. Report both the decomposition and the label rather than counting it silently as an exact-match success.

Do not infer that one isolated prompt sentence caused every changed output: several general contract changes were tested together, and these are single executions, not controlled ablations or repeatability estimates.

## Seven separate cases: final policy

| Case | Expected | Effective outcome | Result |
|---|---|---|---|
| 01. Direct inspection proves absence at its own time/location | supported / actual condition | supported / condition | Pass. A supported negative survives. |
| 02. Blank identification field, no physical observation | unknown | unknown | Pass. The isolated missing-record/absent-object distinction is handled correctly here. |
| 03. Later inspection used to assert earlier absence | unknown | unknown | Pass. No transfer across the unobserved intervening period. |
| 04. Explicit torque entry contradicts claimed missing entry | contradicted | unknown | **Fail.** The model correctly explains the contradiction and outputs relation=contradicted, but supplies evidence=[]. The application correctly refuses an uncited definitive judgment; the overall task still fails to retain the established contradiction. |
| 05. Valid alternative satisfies an OR requirement | contradicted | contradicted | Pass. One necessary part is contradicted by the sufficient alternative, so the whole compound claim is false even though another part is unproved. |
| 06. Log records a stop; its cause remains unknown | supported / context | supported / context | Pass. Missing causal explanation does not invalidate the record observation. |
| 07. Two incompatible readings, no reconciled true value | conflicting | unknown | **Fail against the required conflict workflow.** The model notices both readings and appropriately withholds a true-pressure conclusion, but labels the result not-established rather than conflicting. The disagreement is in its prose, not a structured conflict status. |

Final results: **4/5 saved-case outcomes and 5/7 separate-case outcomes match the prewritten requirements (9/12 total)**. There are three remaining failures of different kinds: a false approval, a lost contradiction due to missing structured citations, and a conflict reduced to unknown. The acceptance condition is unmet; the full RCA was not resumed. The final model calls took 300.740 seconds combined. Across all three iterations, all 36 calls completed and their six summary files confirm the application remained unchanged.

## Code verification and scope of completion

- `npm run test:engine`: 33 passed, 0 failed. Includes source-line constraints, exact claim coverage, missing-premise/counterexample blocking, revision invalidation, immutable checkpoints and prevention of a later verifier promoting a partially supported finding.
- `npm run typecheck`: passed.
- Targeted ESLint over all changed TypeScript/TSX/JavaScript files: passed.
- `npm run build`: passed.
- Evidence-ledger projection is covered by automated tests; the new part-detail UI was compiled but not browser-exercised with a committed live review because no diagnostic verdict was written to the application.
- The main application run remains paused at generation 49. The new prompt was exercised through the production executor by the diagnostic driver. No server restart/resume was performed; restart the local application before any future authorized continuation so imported prompt assets cannot remain stale.

The code implementation and scoped experiments are complete. **Semantic acceptance is not complete.** Do not describe this as a successful full RCA or an eradication of the failure.

## Retained artifacts

| Policy | Saved-case traces | Fictional-case traces |
|---|---|---|
| Earlier whole-verdict reviewer | `outputs/claim-review-check-Fk3szZ/` | — |
| claim-parts-v1 | `outputs/claim-review-check-4rcHPG/` | `outputs/claim-review-fresh-QcqUcq/` |
| claim-parts-v2 | `outputs/claim-review-check-z0uWGU/` | `outputs/claim-review-fresh-X8y0u3/` |
| claim-parts-v3 | `outputs/claim-review-check-7yHnOK/` | `outputs/claim-review-fresh-g4qNLl/` |

Every directory contains a manifest and original request/stream/provider/effective-outcome files. Completed summaries include hashes proving the application input, state and snapshot were unchanged. Previous failed attempts were not overwritten or retroactively regraded as successes.

## What the results justify

The implemented gate removes reliance on an unsupported top-level approval label and makes the source comparison auditable. It cannot detect an unrecognized change in meaning when the same model also supplies the decomposition and interpretation. More schema restrictions alone cannot prove natural-language entailment.

The unresolved problem is specifically whether the reviewer tests the original assertion or silently substitutes an easier record-content assertion. A future change must distinguish those reliably while retaining correct approvals, including direct observations proving absence. Do not restart the full RCA, switch models silently, or hand-edit these verdicts to claim this acceptance gate passed.

Design guidance: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) distinguishes schema compliance from semantic correctness; [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) supports task-specific criteria, edge cases and preserved logs. The OpenAI documentation skill informed those implementation choices, not a change of runtime model.

# Literal-claim review correction — live evaluation record

Date: 2026-09-19. This is a claim-review experiment, not a full RCA pass. The production investigation remains paused; no diagnostic verdict is committed to it.

Current decision: **not accepted for an unattended full investigation**. The broken meaning-tree/ambiguity veto has been removed and seven semantic regression controls now pass with the explicit Qwen reasoning profile. An original compound work-package assertion still produces an inconsistent model judgment; the validator rejects it instead of admitting an unsupported fact. This is an improvement in failure containment, not a semantic pass for that claim.

## Confirmed failure mechanisms

The preceding `fixed-meaning-v4` test had 30 completed provider calls, six interpretation-validation failures, and multiple false unknowns. This was not an Ollama outage. Its evidence-blind interpreter split sentences into noun/time fragments and invented routine-word ambiguity. Our application then made those ambiguities permanent vetoes, even when the evidence reviewer correctly cited a disproof. See the unchanged `fixed-meaning-results.md` and its raw traces.

The correction removes that stage from the active scheduler. `literal-claim-v5` sends the complete original assertion directly to the evidence reviewer. It retains original-line citation requirements, independent source conflicts, invalidation of stale approvals, immutable versions and independent task failure handling. No model replacement, storyteller, hidden evidence, altered claim, or verdict repair is involved.

## Candidate A: same non-thinking runtime

Trace directory: `outputs/claim-review-check-rB1BGC`.

| Saved claim | Expected | Actual | Result |
|---|---|---|---|
| Supplied revision plus actual attachment absence | partial/unknown | supported | Fail: blank field substituted for actual absence. |
| Work-package content plus exhaustive absence of valve/pressure entries | partial/unknown | supported | Fail: excerpts and required record fields treated as complete package coverage. |
| Preparation-only boundary, not released | supported | supported | Pass; original work-stage scope retained. |
| Blank execution-record attachment at issue | supported context | supported context | Pass; table row directly cited. |
| Supplied revision/date and blank instruction field | supported context | supported context | Pass; record observation, no actual absence claim. |

All five calls completed (168.378 seconds summed provider duration, 1,811 output tokens). Application input/state/snapshot hashes are unchanged. The three false-unknown positive cases are recovered, but two false approvals remain: **candidate A is rejected**. Do not label this a correction of semantic accuracy merely because the execution is simpler.

## Candidate B: registered native-thinking ablation

The provider previously hard-coded `think:false`. The installed Qwen reports `thinking` in `/api/show`. Before this comparison, `literal-review-expectations.md` registered changing only this setting on the same five original claims. The first request confirms identical prompt, schema, selected evidence, model digest and output allowance. The thinking option is now explicit in the request/cache identity. Default production behavior has not yet been changed based on an unverified hypothesis.

Trace directory: `outputs/claim-review-check-LHhuZ8`. **Rejected operationally:** case 1 used its 12,587-token output allowance without any answer content; the provider returned a length error. Case 2 began before the first failure was inspected, then was explicitly interrupted. Cases 3–5 were not attempted. Neither interrupted execution nor absent output is a semantic unknown. The comparison does not establish what a completed thinking-mode judgment would have been. No thinking default was enabled for production.

## Candidate C: contrastive prompt, original non-thinking settings

Policy `literal-claim-v5.1`; trace directory `outputs/claim-review-check-PB52s3`. Before its first call, the expectations file registered adding matched examples of record content versus physical attendance and excerpt coverage versus full-invoice contents. Includes supported record and direct-observation examples as positive controls. No fixture answer keys or incident-specific identifiers enter the prompt. Original documents and model were unchanged, but inspection found that prompt length changed context selection (four passages became three in saved case 1), which also changed the source-bound schema and output allowance. This was NOT a pure fixed-packet prompt ablation.

**Rejected:** both overclaims remained supported. Case 2 also invented a source-conflict record without genuinely opposing accounts. Cases 3–5 were supported with the expected record/condition distinctions. The application remained hash-identical.

## Candidate D: compact contract

Policy `literal-claim-v5.2`; trace directory `outputs/claim-review-check-EfjRQi`. One response shape replaces four repeated schema branches; citation grammar is retained and cross-field consistency is checked before applying an answer. For saved case 1, schema size fell from 21,093 to 8,296 characters, and the original-evidence packet grew from three to seven passages. This is a contract/context-efficiency change, not a claim that prompt length alone explains accuracy.

Observed states: supported, partial, supported, supported, supported. **Rejected:** case 1 still promotes a blank field into actual absence, and case 5 is wrongly routed as an actual condition instead of record context. Case 2 now correctly withholds full support, although its rationale is still too ready to treat a requirement as evidence of actual contents. Cases 3–4 retain direct support. All five calls completed; the application remained unchanged.

## Candidate E: one-case Qwen sampling-profile diagnostic

Trace directory `outputs/claim-review-check-Bn9Ygn`. Same prompt, schema, evidence packet, model and output allowance as candidate D case 1 (verified by direct comparison). Thinking=true; explicit sampling temperature=1, top_p=.95, top_k=20, min_p=0, presence_penalty=1.5, repeat_penalty=1, seed=42. The profile follows the [model-card Quickstart](https://huggingface.co/Qwen/Qwen3.5-9B), not an invented optimum. The one queued call completed in 218.361 seconds, returning **partial** and correctly distinguishing a blank field from physical absence. No conflict invented; unresolved physical presence is handed back as a question. App hashes unchanged.

Citation caveat: its selected S1 lines include the blank field but omit line 11 containing the ECP listing. The decisive uncertainty distinction is recovered, but this is not a perfect whole-claim citation result or an acceptance pass. A single fixed-seed observation cannot establish reliability or attribute the change to temperature alone. No production default was changed.

### Prose feasibility probe

`outputs/claim-prose-probe-cAQyi9`: same original evidence packet, same Qwen digest, non-thinking temperature zero, short ordinary-prose task and no schema. Completed in 13.794 seconds. **Failed:** it still claimed the blank field confirmed actual absence and additionally conflated WO-527-E with the temporary-instruction field. This means removing JSON alone did not recover the crucial distinction in this probe; it does not prove that output format never affects other cases.

The native-thinking/sampling profile is being extended to the frozen regressions before any release decision. No new transfer inputs have been tuned against observed results.

### Frozen seven-case regression extension

Trace directory: `outputs/claim-review-fresh-d7R2sU`. Same v5.2 prompt/contract and explicit thinking/sampling profile, no cross-case model history. **All seven completed and matched their frozen truth/conflict/context expectations.** Original selected citations were inspected. Total provider duration: 1,034.964 seconds (17.25 minutes). App input/state/snapshot hashes remained unchanged. This is a seven-case regression pass, not the full 24-case gate or a complete RCA.

| Case | Expected | Observed | Audit |
|---|---|---|---|
| Direct complete bolt inspection | supported condition | supported condition | Correct original inspection citation; no invented conflict. |
| Blank bolt-identification field | unknown | unknown | Preserves record/physical distinction; no conflict. |
| Later inspection asserted as earlier condition | unknown | unknown | Preserves 09:50 versus 10:21 and intervening work; no conflict. |
| Log contains explicit torque entry | contradicted | contradicted context | Cites line 2 with 7.8 N·m; no source conflict invented. |
| Authorized OR alternative | contradicted | contradicted | Cites rule, current revision and inventory (all three lines); no invented conflict. |
| Log reports stop, cause unknown | supported context | supported context | Does not invent a cause or withhold the established log observation. |
| Simultaneous disagreeing pressure accounts | unknown + open conflict | unknown + open conflict | Both original same-port/time readings retained; neither selected as physical truth. |

### Non-thinking sampling ablation

`outputs/claim-review-check-taGkla`: same v5.2 prompt/schema/evidence/model and explicit sampling/seed as candidate E, but thinking disabled. Completed in 11.948 seconds and **failed**: the physical-absence overclaim was again marked supported/context. The faster profile is rejected; no seed search or silent fallback. The successful seven-case profile remains native thinking plus the documented sampling configuration. Remaining saved controls and transfer tests are still required for qualification.

### Remaining original claims

`outputs/claim-review-check-7MajNw`: native thinking with the same explicit sampling profile, excluding the already-tested first original claim. This batch started under v5.2; the later v5.3 runtime-profile declaration does not change its loaded code or saved request.

| Original case | Outcome | Assessment |
|---|---|---|
| 2: work-package contents and exhaustive absence | Incomplete | Qwen listed a missing exclusivity premise but still selected entailed and treated excerpts/record-type conventions as exhaustive actual contents. Parse-time consistency validation rejected it. Do not convert this into a passed unknown or silently repair its verdict. |
| 3: preparation-only, not released | supported condition | Direct incident text and operational log support preserved. |
| 4: blank execution-record attachment | supported context | Direct table row cited, with no physical-absence inference. |
| 5: supplied revision/date and blank field | supported context | Correct record-only scope; S1 lines 11 and 16 directly support both clauses. |

The batch completed at 2026-09-19 19:01:03 UTC. Its saved summary confirms `applicationRunUnchanged: true`. Across the five original claims, three pass cleanly, one recovers the correct partial judgment but has incomplete citation coverage, and one is rejected as internally inconsistent. Together with the seven regression controls, this is ten clean results out of twelve attempted cases—not a full acceptance pass. The other twelve cases in the frozen 24-case gate remain untested.

Because case 2 fails the frozen gate, the additional six transfer regressions and six new transfer inputs are not run in this candidate. They remain untested, not passed. Independent original controls were allowed to finish; no failed case was repaired or retried.

## Implemented runtime candidate and release boundary

- Active policy is now `literal-claim-v5.3`: complete original claim, compact schema, cited evidence, independent source conflicts and explicit incomplete execution. The new policy prevents older review approvals/caches being treated as current.
- `src/engine/review/inference-profile.ts` declares native thinking plus the recorded sampling profile for Qwen 3.5 **claim review only**. Other models and stages retain prior behavior. This is the better-tested candidate setting, not a statement that the full gate has passed.
- Explicit diagnostic overrides remain available and are recorded in trace/cache identity. `--runtime-defaults` exercises the real stage defaults; a unit integration test verifies that Qwen uses the declared mode without changing tagging or other models. No hidden model fallback or seed search.
- New provider attempts count received thinking characters separately; deliberation text is not mixed into answer JSON, evidence or future context. Earlier traces without that field are not retroactively filled in.
- The application investigation stays paused at its existing checkpoint. No source package, answer, model digest, prior version or causal board is rewritten. The local app must load the new code/prompts before any future explicit continuation.

The remaining problem is concrete: this tested Qwen setup can recognize an unproved premise and nevertheless state a contradictory conclusion, especially for compound/exhaustive claims across documents. More schema validity alone cannot make that reasoning correct. The engine must retain the failure and keep that claim out of established facts; it must not turn every other claim into unknown or block unrelated completed work. A production-level/full-RCA acceptance claim is not justified by these results.

## Verification and limits

39 deterministic engine tests passed, including direct scheduling, isolation of failed reviews, authentic citations, original-target preservation, stale-approval invalidation, distinct source-conflict handling, mode/sampling cache separation and actual runtime-profile selection. Type checking, targeted lint and the final production build passed. These engineering checks do not replace semantic acceptance.

A final read-only inspection confirmed the original investigation remains paused at generation 49, phase 4, with 73 findings, 16 questions and no causal-board nodes or edges. These diagnostics did not resume it, create a new version, or commit test judgments to the investigation.

The official [Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs) and [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices) informed separating software validity from semantic acceptance. [Ollama's thinking documentation](https://docs.ollama.com/capabilities/thinking) informed the explicit provider comparison. None of those documents certifies this model or guarantees correct RCA conclusions.

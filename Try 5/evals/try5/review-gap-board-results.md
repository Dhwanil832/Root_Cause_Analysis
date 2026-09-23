# Review-gap correction and bounded board pilot

Date: 2026-09-19. Production investigation remains paused. Bounded pilot and
single-document comparison completed. Overall result: operational progress,
partial semantic result; not accepted as full RCA.

## Implemented

- Active `literal-claim-v5.5` retains the previous generation prompt/shape. The
  attempted v5.4 citation-map field was rejected and removed after live tests
  showed a false approval and an additional false rejection. Its historical
  outputs remain preserved; citation coverage is not claimed solved.
- Cross-field validation remains mandatory at application time. An inconsistent
  verdict stays failed/incomplete. Validly sourced proposed missing premises can
  be preserved as deduplicated questions, routed through the normal broker and
  answer-fetching stages, without becoming facts or repairing the verdict.
- Recovery keeps original specialist ownership and target-claim provenance,
  including when questions merge. Malformed output, changed targets or forged
  citations cannot supply recovered questions.
- No new model, model fallback, story agent, hidden answer, or blanket “unknown”
  rule was added. All failed candidates and the original checkpoint are retained.

## Live original-claim comparison

Trace: `outputs/claim-review-check-AauEoE`. Five unchanged original claims,
production review defaults, frozen Qwen digest, one attempt each. v5.4 changes
prompt/schema and may change context selection; it is not a one-variable ablation.

| Case | Observation | Semantic assessment |
|---|---|---|
| 1: physical attachment absence | supported/context; cites ECP row and blank field | **Fail.** Rewrites physical absence as record content; citation coverage alone did not fix reasoning. |
| 2: exhaustive package contents | entailed proposed, rejected for generated wording map | **Fail.** Still treats required fields and record conventions as exhaustive contents; no missing premise/question generated. |
| 3: preparation-only state | correct entailed judgment, rejected for generated wording map | **Fail operationally.** Added field rejected a legitimate finding. |
| 4: blank execution form | supported/context | Pass; original table row directly cited. |
| 5: revision/date and blank field | supported/context | Pass; record scope and both source lines preserved. |

The first case already fails the unchanged full semantic gate. No seven-case or
transfer extension is queued for this candidate. Completing independent original
controls does not turn the failed candidate into an accepted one.

All five calls completed, and the summary confirms the original app hashes are
unchanged. Candidate v5.4 is rejected. v5.5 restores the earlier generation
prompt and shape and retains only application-time failure/question separation.

Offline replay `outputs/review-gap-replay-GXFsIK` re-applied the unchanged saved
v5.2 contradictory output against its original request text. The verdict remained
proposed/incomplete, zero new facts were added, and one evidence request was
preserved with equipment-specialist ownership and target-claim provenance. No
model call or DB write occurred. This passes failure containment, not semantics.

## Bounded board pilot

The selection and expected boundaries were frozen before inference in
`board-pilot-selection.json` and `board-pilot-expectations.md`. The pilot uses a
clone of the existing checkpoint, real production executor/application logic and
the same model. It must not be represented as a production version, a complete
RCA, or success on the 24-case gate. Only individually reviewed supported claims
from its explicit three-finding scope may enter causal analysis. Every proposed
node and relationship gets a separate verification call and an original-source
audit. The failed attachment-absence claim is not admitted to the pilot.

### Baseline pilot completed and audited

`outputs/audited-board-pilot-3pGfR3`: seven real calls (three claim reviews, three
causal dispositions, one node verification), no failed calls, original app
hash-identical. All three selected findings were supported with directly relevant
original citations. The generation prompt hash matches the earlier stable prompt.

The resulting diagnostic board contains the focal incident and **one preparation
condition marked partial by the node verifier, zero links**. The verifier explicitly
says the condition is documented, but downgrades it because its causal link is
unproved—even though the node does not assert that link. This is a concrete
node-versus-relationship scope failure, not a successful board audit. Air-low and recovery
observations remain in the evidence notebook; causal analysis asks for mechanism
evidence instead of promoting those observations into causes. This is an initial
investigation map, not an explanatory causal chain or root-cause conclusion.

Audit caveats: the preparation condition is administrative context, not a proven
contributor. One generated question asks what authorization gap existed, which is
leading; the sources do not establish a gap. No such gap became a finding/node.
Question quality is not fully accepted. With zero links proposed, this pilot has
**not exercised real-model relationship verification**; unit tests alone do not
fill that gap.

The single-document comparison was briefly started at
`outputs/audited-board-pilot-p9ZS9X`, then interrupted during its first review when
the baseline verifier defect was identified. Do not count its unfinished call or
use it as a completed comparison. No app data was modified.

Correction: explicit node/relationship routing and separate verification prompts.
Node verification judges whether the stated condition/event is established;
relationship verification judges the connecting mechanism (or temporal order for
a preceded link). Before any new call, expected result for this exact saved node
is supported, with causal role still unproved and no links fabricated. Reverify
only the saved node on the same evidence; do not repeat completed claim reviews.

Node-only retest `outputs/audited-board-pilot-wpypKU` completed in one real call:
the same node is now supported, with zero links proposed and original app hashes
unchanged. The support is for the documented state, not causal contribution.
The three earlier claim reviews were retained, not rerun or counted as new passes.

The interrupted comparison recorded failed/aborted tasks but no successful new
judgments. The diagnostic runner now exits immediately on cancellation and rejects
failed parent pilots, so such an interrupted result cannot seed a comparison.
The next comparison explicitly uses the corrected `wpypKU` baseline and the same
single IA-P01 document, not the interrupted output.

### Single-document comparison — completed and audited

`outputs/audited-board-pilot-BiUUCI` starts from `wpypKU` and adds only the existing
IA-P01 selected pressure/alarm extract (SHA-256
`9b9a6662b5de2efa0e77e12ede0b50129a711702a3fcfa5937d3400058090db4`).
The model receives the verbatim document, not evaluator expectations. This pilot
reconsiders the same three claims; it does not run full document extraction or
create an app version.

Six real calls completed: three claim reviews, two causal dispositions, one node
verification. No failed tasks, no retry, no quarantined items. The comparison took
about 13 minutes 43 seconds. Original input, state, snapshot and generation are
unchanged. Findings, node identity and prior questions are preserved in a separate
diagnostic snapshot, not committed as a new app version.

| Check | Observed result | Assessment |
| --- | --- | --- |
| Retain the three established claims | All three still supported, statements unchanged | Pass on factual retention |
| Use the new pressure record | Recovery review cites selected P-R values returning to 6.8 bar; air-low review adds the alarm row | Partial: record is used, but the alarm citation needs narrower scope |
| Retain a documented condition without demanding its cause | Same preparation-only node ID and label remain; node verifier returns supported | Specific scope fix holds; expanded detail still needs review |
| Preserve stable claim scope | Recovery changes from actual-state/condition to record-observation/context | Fail: changes downstream eligibility without a changed assertion |
| Advance the causal investigation from new evidence | Two causal calls mostly ask again about interruption location and crew valve actions; no links | Limited progress, not an explanatory causal board |
| Avoid unsupported mechanisms | No asserted compressor trip, valve state, flow, continuous pressure, or alarm input mapping becomes a finding/node/link | Pass within this small scope, not a general hallucination guarantee |
| Original application integrity | Hash-identical, paused generation 49 | Pass |

Detailed caveats:

- The air-low claim remains supported by its original log and incident account.
  The reviewer also cites the COMP FAULT alarm row. That row establishes the
  displayed alarm, not its input mapping or a compressor fault. It is not
  independent proof of the air-low condition without the mapping.
- The recovery claim remains supported and its review now cites actual selected
  P-R recovery values. However, its claim type changes from `actual-state` to
  `record-observation`, causing its causal role to change from condition to
  context. The literal statement did not change; stronger evidence did not
  justify downgrading its scope to record content. This is a classification
  inconsistency and affects routing, even though the supported status survives.
- Both causal packets contain the full new pressure/alarm extract. Nevertheless,
  the air-low proposal repeats that supporting records are pending and does not
  use the P-U/P-R sample contrast to make its location question more specific.
  This observed underuse is not explained by the document being absent from its
  packet. A recovery review used the readings, but stronger evidence did not
  produce a correspondingly stronger causal investigation in these two calls.
- Three new question IDs were added; these overlap the baseline questions. The
  pilot intentionally does not run broker/answer stages, so the duplicate count
  is not a broker test. Their text generally remains exploratory, but an intent
  introduces an unsupported example of M-102 opening as upstream failure.
  No such operation became a fact; the example still needs evidence rather than
  being treated as equipment knowledge.
- The revised preparation node adds: “meaning the system state could be
  incomplete.” The cited requirement concerns incomplete knowledge of the event
  sequence, not an established incomplete physical state. The verifier approves
  the whole node while its explanation primarily supports the preparation/signoff
  portion. Thus the node's main condition is grounded; its full expanded prose
  is **not** accepted as a clean evidence-only statement.
- Generated prose retains call-local S references. In the causal packet S1 is the
  work-package cover; in the next verification packet S1 is the requirements
  document and S2 is the cover. The structured span IDs remain available, but the
  inherited prose references are not remapped. The verification explanation also
  calls the cover S1 once. This is a concrete provenance-presentation defect;
  do not treat those inline aliases as stable document identifiers.
- The one condition is not a proven contributor, and zero links were proposed.
  Real-model relationship verification therefore remains untested. There is no
  root-cause conclusion, human acceptance, corrective-action validation or
  storyteller run in this pilot.

### Retained result and next boundary

Retain the failure/question separation and the node/relationship verification
split. Reject v5.4's citation-map experiment; do not blend its scores with this
pilot. The original compound-claim false approvals remain unresolved and the
24-case gate has not passed.

Before expanding the run, the remaining directly observed problems are claim-scope
classification changing downstream routing, incomplete checking of expanded node
prose, call-local aliases escaping into persistent statements, and weak causal use
of newly supplied measurements. Preserve these exact failed examples for a bounded
regression check. Do not restart the storyteller or force links onto the board.
No additional inference is left running after this comparison.

## Engineering verification

43 deterministic tests passed, including separate node/relationship routing,
after fixing a timestamp-tie ordering assumption in
the test's trace lookup and making the routing fixture keep two distinct questions
separate. Tests use a labeled deterministic adapter, not Qwen semantic scores.
Type checking, targeted lint and the production build passed with the retained
generation shape and separate verification prompts. The baseline, node-only retest
and controlled-document comparison are complete. No deterministic test success is
being counted as a Qwen semantic pass.

Official [Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs)
informed keeping schema/coverage validity separate from semantic correctness.
The [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
informed frozen case expectations and stage-by-stage inspection; neither promises
that this Qwen configuration can perform reliable RCA.

# Controlled inquiry result — 2026-09-19

## Decision

**Engineering checks pass. Semantic acceptance does not.** The focused task
noticed a consequential pressure contrast missed by the earlier causal task,
but its explanations and question implications still overreach the evidence.
Keep the focused task experimental; do not automatically resume the full RCA or
storyteller. Do not promote this output into factual nodes or causal links.

The expectations were written before the calls in
[focused-inquiry-expectations.md](focused-inquiry-expectations.md).
All three calls used the same Qwen3.5 digest, sequentially, with one attempt each.
No model fallback, hidden answer key, additional progressive document or database
write was used. This is a task-design diagnostic, not an app V2 or a complete RCA.

## Real model results

| Test | Duration | Observed result | Acceptance |
| --- | ---: | --- | --- |
| Exact saved causal request, native thinking + documented sampling | 231.6 s | Recognized the receiving pressure drop, but not its contrast with P-U. Repeated the broad origin question. Called the unknown root cause “upstream.” | Fail |
| Exact saved verification request, same native profile | 319.2 s | Changed blanket support to partial and detected stale source numbering. Did not adequately resolve the added “system state could be incomplete” language. Added largely generic questions. | Partial diagnostic improvement, not a pass |
| Focused explanation comparison, same original evidence | 254.7 s | Identified P-R dropping while P-U stayed nearly steady in the selected samples. Preserved sampling limitations. Produced three evidence requests, but several proposed implications were unjustified. | Partial progress; fail overall acceptance |

The profile comparisons preserved the saved system prompt, evidence packet,
output contract, context and output allowance. The replay's draft-7 wire schemas
were checked against the production serializer and matched. Thinking and sampling
changed together: these are profile comparisons, not isolated thinking-toggle tests.

The focused comparison deliberately changed the task, prompt and output schema.
It supplied the same three reviewed claims, the same eight original passages,
and 23 existing relevant questions. All eight passages were included; none were
omitted. It used 10,079 input tokens and returned 1,606 output tokens as reported
by Ollama, with an output allowance of 17,978. These counts are not an estimate of
private deliberation tokens. No pressure-specific answer was inserted into the
task objective. Evidence ordering and context composition differ from the exact
replay, so this is not proof that one particular prompt sentence caused improvement.

## Source audit of the focused output

Useful observations:

- IA-P01 records P-U at 6.8–6.9 bar while P-R declines to 2.1 bar and recovers in
  the selected samples. The model found this contrast without being told to do so.
- It retained the warning that samples are not continuous and acquisition
  quality is not sensor accuracy.
- Preparation-only status and a pending acceptance signature were kept distinct
  from actual valve positions.

Remaining errors:

1. **Evidence compatibility becomes evidence for an allegation.** An incomplete
   log does not support a claim that the crew opened a line or breached isolation.
   A general change-document requirement does not establish that a routing change
   actually existed or was undistributed.
2. **Uncertainty is mislabeled as opposition.** The initial account's unknown
   interruption origin does not oppose a distribution-failure hypothesis. The
   administrative cover record does not refute a physical field action.
3. **Proposed answer implications do not follow.** Finding a valve operation would
   not by itself establish a procedure deviation or training gap. Correct current
   drawings and valve operation would not establish valve failure. Eliminating one
   documentation issue would not establish a mechanical cause.
4. **Document identity slipped.** The temporary-instruction field is on the work
   package cover, not established as a field on the WO-527-E execution record.
5. **The pressure contrast did not drive a sufficiently precise next question.**
   The first question still broadly asks what caused the loss. The conclusion
   localizes the interruption too firmly without current topology, point mapping
   and sensor validity. The source directory explicitly is not a current piping
   diagram. RUN status is not a flow measurement.

The proposal's facts, source passages and existing board stayed unchanged. Its
three new questions have durable source references and inquiry ownership, but
their being structurally accepted is **not** semantic endorsement. Zero
quarantined rows means valid structure, not correct causal reasoning.

## Implemented code changes

Engine version is now `try5.2.2`. Old checkpoints are not silently resumed under
the changed engine contract.

- Factual node labels come from the exact reviewed finding. Generated alternative
  wording is retained as an audit-only proposal, not node detail submitted as fact.
- Original review quotations retain immutable span identity, source revision,
  document label and the original call-local reference. Generated commentary binds
  known source/finding aliases at ingestion. Raw model output remains available.
- Scope classification history is retained and exposed in evidence review. A
  reviewer changing an observation to “record-observation” no longer silently
  excludes it from causal consideration. Explicit context findings remain context;
  supported record content is not thereby promoted into a physical cause.
- An experimental `inquiry` task compares explanations and asks for evidence with
  stated answer implications. It uses the production executor, source selection,
  provider and task application path. Its observations/explanations stay proposed
  and cannot directly change findings, board nodes or links.
- Its questions use the existing broker/answer path. Merging a question retains
  inquiry ownership and evidence, and the answer remains available to both requests.

The focused task is intentionally **not the default planner strategy** yet. It is
invoked through the controlled pilot until question quality passes evaluation.
No new ensemble, training workflow or autonomous investigation was added.

## Verification and preservation

- 48 deterministic engine tests passed. These verify contracts and routing, not
  Qwen's factual accuracy.
- TypeScript and targeted ESLint passed; application build passed.
- Original run `da57d29d-cf54-4c29-85ae-54260ef92dcd` remains paused at generation 49.
- Original input, state and snapshot hashes match the preserved pilot manifest.
- The existing compound-claim/negative-claim semantic failures are not declared
  solved, and the 24-case review gate has not been passed by these three calls.

## Narrow next experiment

Retain the pressure contrast as a proposed observation to be reviewed against
IA-P01. Then test **one** next-evidence decision: what current point mapping,
connection diagram and sensor validation are needed before interpreting that
contrast as a physical location clue? Any claim about a valve action, change
history or procedural deviation needs its own incident evidence.

The next acceptance condition is not “more hypotheses.” It is a request whose
possible answers change the assessment for a defensible reason. Do not rerun the
whole archive or storyteller to test that skill.

## Inspectable artifacts

- [Causal profile replay](../../outputs/profile-replay-uicQy1/result.json)
- [Verification profile replay](../../outputs/profile-replay-eTXGyz/result.json)
- [Focused output and durable proposal](../../outputs/focused-inquiry-pqwCwb/result.json)
- [Exact focused request](../../outputs/focused-inquiry-pqwCwb/request.json)
- [Focused prompt](../../prompts/causal-analysis/inquiry.md)
- [Controlled pilot](../../scripts/focused-inquiry-pilot.mjs)

The evaluation guidance used here influenced the separation of engineering checks
from semantic acceptance, frozen inputs, and explicit source-audited expectations:
[OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
The inference profile follows the [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B).

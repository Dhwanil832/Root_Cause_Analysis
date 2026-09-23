# Next-evidence experiment — results

## Outcome

**Both calls completed; neither passed the reasoning criteria.** The remaining
problem in this test is the model's proposed inference from a possible answer,
not a crashed or blocked RCA engine. The original investigation and causal board
were not changed.

The initial experiment asked Qwen to turn its pressure contrast into one useful
evidence request, with possible answers and what each would and would not permit
the investigation to conclude. The generic prompt did not name the desired
document. [Acceptance criteria](next-evidence-expectations.md) were saved before
the run, kept out of its packet, and verified unchanged afterward.

## Results

| Condition | Time | Input tokens | Actual result |
| --- | ---: | ---: | --- |
| With 23 existing questions | 203.8 s | 11,074 | Repeated an existing valve-record question. Treated no recorded valve changes as support for equipment failure. |
| Same request, question history removed | 155.9 s | 8,731 | Added a correctly unresolved missing-record outcome, but still attributed a leak, rupture or upstream fault if valves stayed open. |

Both used `ollama:qwen3.5:latest`, digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`,
native thinking and the same saved sampling profile. Each made one attempt.
The second condition preserved the system prompt, original evidence and ordering,
findings, nominated observation, schema, context and 19,017-token output allowance.
Only `evidencePacket.existingQuestions` was removed. It was a separately declared
diagnostic condition, not an automatic retry or edited answer.

The second call used about 21% fewer input tokens and completed about 24% faster
in this paired sample. That is not a general latency benchmark or evidence of
improved overall reasoning reliability.

## What the failure looks like

The first request was:

> What specific valve positions or isolation states were recorded in the field execution record (WO-527-E) at the time of pressure loss?

That is a reasonable record to request. The failure is what Qwen proposes doing
with the answer:

- First condition: no change **found in the record** → equipment failure/leak.
- Second condition: valves **recorded open** → pressure loss attributed to a
  leak, rupture or upstream supply fault.

Neither inference follows from that answer alone. Missing records cannot rule out
an action. Even an adequately verified valve position only constrains a specific
valve-closure explanation; it does not establish the other proposed causes.

The source documents explicitly say the log is incomplete, the directory is not
a current piping diagram, observed valve position differs from internal condition,
and good acquisition quality is separate from sensor accuracy/full time coverage.
The outputs did not carry those necessary conditions into their causal updates.

Removing old questions improved one unknown-record branch, but did not remove the
underlying overreach. We cannot explain this failure solely as copying old questions.
This is a narrower diagnosis than saying the whole pipeline is broken.

## What should happen next

Keep these as rejected **inference proposals**, not board facts. Separate a useful
evidence request from permission to update a causal conclusion. The next target to
validate is the answer-to-inference boundary: a sourced answer may establish a
recorded fact without authorizing a mechanism or excluding every alternative.

Do not restart the full RCA or reconnect the storyteller on the strength of these
results. Do not keep changing prompts until this one case happens to pass. These
two failing outcomes are now concrete regression cases for any proposed fix.

## Preserved state and implementation scope

- Original run `da57d29d-cf54-4c29-85ae-54260ef92dcd` remains paused at generation 49.
- Input/state/snapshot hashes match the saved pre-experiment manifest.
- No production application code, database version, facts, links, model selection,
  or scheduler behavior changed this turn.
- Added one experimental prompt, two standalone diagnostic scripts, frozen
  expectations and source audits. The scripts reuse the existing context planner
  and/or provider. Syntax and targeted ESLint checks passed. No full rebuild or
  broad preflight suite was needed for these isolated diagnostic additions.
- The previously reported 48 engine tests were not rerun or claimed as new model
  acceptance. The 24-case claim-review gate remains unresolved.

## Inspect the evidence

- [First raw output and reference bindings](../../outputs/next-evidence-jTDF1s/result.json)
- [First source audit](../../outputs/next-evidence-jTDF1s/semantic-audit.md)
- [No-history raw output](../../outputs/next-evidence-no-history-gVu9Mb/result.json)
- [No-history source audit](../../outputs/next-evidence-no-history-gVu9Mb/semantic-audit.md)
- [Exact initial request](../../outputs/next-evidence-jTDF1s/request.json)
- [Exact comparison request](../../outputs/next-evidence-no-history-gVu9Mb/request.json)
- [Generic experimental prompt](../../prompts/causal-analysis/next-evidence.md)
- [Prespecified context comparison](next-evidence-history-ablation.md)

The OpenAI Docs evaluation guidance influenced the frozen criteria and separation
of runtime success from source-audited reasoning quality:
[Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
It does not establish the correctness of these RCA judgments; those were checked
against the supplied synthetic incident documents.

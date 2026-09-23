# Try 6 implementation record

## Intent

Change what work is generated and when the first investigative position becomes available. Do not solve runaway expansion with a fixed number of questions or by declaring the RCA finished early.

The previous ledger could grow from reading, specialist extraction, and answer extraction, then wait for all those findings to be reviewed. Try 6 has one source-observation producer: original evidence reading. Other roles reference the notebook. Explanations, consultations, evidence directions and verified propositions are separate types.

## Execution contract

`read → frame → targeted consultations → grouped evidence resolution/brokerage → refine → selected-premise review → connection verification → publish`

The frame itself creates a provisional board. All source observations remain accessible, but only selected premises are reviewed. Questions from the reader remain notes; they do not enter an executable queue. Final review gaps remain evidence requests. The planner has no backward transition that automatically rereads answers, re-extracts findings, or regenerates an expanding question queue.

This is a publication dependency graph, not a fixed number of permitted questions. The regression fixture with 17 directions resolves them in one branch-level search without creating more findings. This demonstrates routing behavior, not the quality of 17 model-authored questions.

## V2 and later

- Source spans keep content-based identities. Only new or changed passages are read.
- Prior observations and branches retain identities. Omitted branches remain available; omission cannot silently close them.
- A consultation is reused when its purpose, mechanism/gap and referenced finding revisions are unchanged.
- A new source causes conservative re-review of selected map premises because it could contradict them, even if their wording is unchanged. This intentionally costs more than narrowly assuming an old claim remains true.
- An obsolete premise can be explicitly retired after dependent arrows are withdrawn. It leaves the active map/review queue, not the notebook or old snapshots.
- Original evidence, model identity/digest and immutable version boundaries remain track-local.

## Evidence and failure boundaries

- Branches remain possible explanations; branch status never makes a root cause verified.
- The map selects existing statements rather than rewriting them with type labels or stronger assertions.
- Hypotheses cannot become factual nodes or established causal premises.
- A complete causal assertion requires original supporting evidence, supported premises/endpoints and a separate relationship check. Temporal order alone is not a causal verdict.
- The common resolver cannot add findings. Uncited answers remain requests for evidence. Semantic question merges must point to an earlier canonical question; scope differences are not valid duplicates.
- The inherited literal reviewer retains exact-target and original-line checks and the narrow `None` formatting guardrail.
- Malformed reading or framing pauses dependent work. Optional consultation or individual claim-check failures remain local, with a partial published position when independent work can finish.
- Failed responses, quarantine records and traces remain inspectable. Recovery does not erase a prior failure audit; a recovered version can still carry a partial execution label.
- Provider outages and identity mismatches pause, rather than triggering model substitution or endless retries.

## Verification on 2026-09-20

- 15 new workflow/integrity tests pass, including two different incident types progressing through V1 and V2, and source-removal invalidation.
- 37 applicable inherited component regressions pass: source preservation, context accounting, leases, literals, citations, formatting, uncertainty, model sampling, answer ownership and provider streaming.
- TypeScript checking and bundle compilation pass. The copied historical preparation script has one pre-existing unused-variable lint warning; no lint errors.
- Read-only context-sizing check used the stopped Try 5 run's 87 original-reader observations. The compact map packet fit a 32,768-token configuration using the declared conservative byte estimator. This was not inference or a resumed run.
- Try 5 run `4866969b-2dea-41ed-9b45-acb2de6fba9c` remained paused at generation 1226 during the check.
- Try 6 starts separately on port 3016 and discovers the installed Ollama models. Its experiment storage starts empty. No hosted API keys, experiments, uploads, or evaluation packages were copied.

The tests do not establish model reasoning accuracy, production readiness, or guaranteed latency. A real Qwen V1→V2 acceptance run remains to be performed.

The subsequent [capacity-policy update](try6-capacity-policy.md) removes the fixed 32K context, application generation caps/deadlines and file/media size caps. It adds 16 passing capacity tests (68 tests total). The earlier 32K sizing observation above is a historical test configuration, not the new application default.

## Design guidance

OpenAI's current [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) informed explicit role contracts and call-local ID schemas. Schema validity is not treated as semantic truth.

The [agent evaluation guide](https://developers.openai.com/api/docs/guides/agent-evals) informed preservation of stage-level traces and behavioral regression tests. This app remains provider-independent; no OpenAI SDK migration, hosted tracing upload, model ensemble or fine-tuning loop was introduced.

## Deliberately unresolved

Semantic prioritization still depends on the selected model. Large notebooks can exceed context; this version reports that limitation rather than claiming arbitrary-scale understanding. Retrieval remains lexical, and separate model judgments are not independent sources. Storytelling remains separately enabled and was not exercised during this implementation.

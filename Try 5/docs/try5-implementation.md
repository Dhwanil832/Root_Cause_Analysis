# Try 5 implementation record

Date: 18 September 2026. This records code delivery, not a successful scientific RCA evaluation.

## Replacement boundary

queueInvestigation freezes incident/model/document/answer inputs; runInvestigationTask executes one leased task. Browser APIs enqueue work and return. A separate process drives the worker with a server-only token. SQLite/D1 transactions guard commits by lease and generation. An expired request may need repeating if its result was never committed; committed work is reused when prompt, schema, model/configuration, evidence packet and inventory keys match.

Final snapshots cannot be overwritten. A failed-task retry makes a new revision; an outage resumes the same unfinished revision. Earlier paused revisions block later revisions of that track. Generated interpretations and task caches are track-isolated. Model digest/configuration is frozen; changed Ollama identities cannot silently enter an existing track.

## Evidence and reasoning

Original sources use exact offset spans; decimal points do not split passages. Markdown headers and table headings remain contextual, not fabricated quotations. Content-hash extraction reuse is separate from model-result reuse. Source indexes are reused while a track's inventory is unchanged.

Each responsibility has a prompt/schema/task contract. No task receives the full previous board by default. Questions retain all owners; brokered equivalents use a canonical question, and reviewed answers route back to every owner. Answer completeness is separate from support for individual assertions.

Application-assigned finding IDs survive explicit revisions. Nodes/links are local proposals, followed by separate verification. A link cannot be supported while underlying findings or endpoint propositions lack support. Withdrawn proposals remain unresolved rather than surviving as proven links. Changed evidence triggers lexical/domain relevance checks; ambiguous relevance is conservative. Negative answers and reviews depend on evidence inventory, not only their previous citations.

Invalid items are quarantined while valid siblings and other tasks survive. Connectivity/configuration failures pause work. Failed execution is never converted into a scientific unknown. Human decisions remain separate from evidence verdicts; changed accepted propositions reopen. Review APIs reject stale versions and unfinished revisions. Corrective-action proposals require a supported, accepted causal target and a supported relationship.

Visual markers are not transcriptions. Original media must be attached to a compatible model request. Missing/unsupported media fails locally, with no model fallback. Human confirmation of visual observations remains separate from model interpretation.

## Storyteller separation

The fixed scenario, hidden truth, jobs and release history stay outside RCA evidence tables. The story model sees one question, bounded available passages and relevant released memory, not the evaluator answer key or board. Each question has a durable lease/result/error. Successful answers survive failures; a partial batch can release only successful answers or retry failures. RCA starts only on explicit batch release. Quotations are copied from exact selected spans. Released answers remain labeled simulated testimony and undergo normal evidence review.

The storyteller answers from supplied scenario records; it does not invent new scenario documents. The same model identity is checked against its track.

## Prompt design

Instructions are separated from untrusted evidence. Each role defines purpose, input/output meaning, uncertainty and completion rules. Kickoff tables remain non-exhaustive examples. Local references avoid archive-sized output enums. Brief decision summaries are retained, not private chain-of-thought. These choices reflect the separation of schema adherence from factual correctness in [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and the instruction/example/context organization in [prompt engineering guidance](https://developers.openai.com/api/docs/guides/prompt-engineering).

## Checks performed

- TypeScript, ESLint, application build, and migration/schema consistency checks.
- Fourteen regressions using real SQLite transactions and a deterministic adapter: source preservation, growing-archive context, bad-item isolation, immutable V1/V2, reuse, stale leases, track/credential isolation, partial answers, causal support gates, provider outage recovery, private story-source boundaries, story retries, missing media rejection, and short-answer attribution.
- All migrations applied to fresh Try 5-local storage. Separate web/worker processes started; authenticated idle polling verified.
- Browser checks of intake, installed-model discovery, provider settings, navigation and isolated empty history, without observed browser-console errors.
- Historical launchers targeting Try 4/port 3000 disabled; Try 5 uses port 3015 and its own runtime state.

No new Qwen RCA inference, hosted-provider inference, visual interpretation trial, four-version experiment, or held-out scientific evaluation has been run in these checks. Copied evals/r3-* records are historical, not Try 5 results.

## Explicit limits

- Retrieval is lexical plus source/context neighborhoods; semantic retrieval quality needs evaluation.
- Context estimation uses UTF-8 bytes and modality reserves. Provider refusal is authoritative. Arbitrarily large required premise sets remain explicit local failures; automatic arbitrary-size premise synthesis is not implemented.
- A revision includes one late-question follow-up pass, then publishes its state with further questions open. There is no limit on total questions across evidence revisions and no automatic investigation closure.
- Source-quality assessment is integrated into claim review and attribution. Legacy standalone source-adjudication cards are not populated by the new engine yet.
- Candidate neighborhoods are bounded; important cross-document joins require controlled positive-discovery tests. There is no learned entity resolver or exhaustive semantic graph search.
- Human action/branch decisions are records, not proof that a plant control was implemented.
- Production authentication/security, fine-tuning, ensembles, vector infrastructure and autonomous four-version scheduling remain outside this implementation.

Next acceptance gate: a controlled Qwen V1→V2 with private expected changes, assessed for both operational completion and scientific correctness. A completed ledger alone does not meet that gate.

# What each problem must achieve for the full framework

Written 2026-10-30 from the audit (`FRAMEWORK_AUDIT.md`), your description of how
the system should behave, and a second round of research. Nothing here is
implemented. Numeric targets are proposals: I will fix them only after we have a
baseline from the scorecard on the fixed simulator.

## The overall goal

Given an incident and documents that arrive at any time (with the incident, in
answer to the system's own requests, or unprompted), the framework keeps
investigating with whatever it has and maintains an RCA board such that:

- **G1 Grounded.** Every statement on the board traces to a source sentence.
- **G2 Honest.** The board separates what the evidence shows from what is only
  proposed or unresolved, and never declares a root cause the evidence does not
  support. A missing record is never treated as a finding.
- **G3 Responsive.** A document arriving at any moment is checked against every
  existing claim; only what it touches is redone.
- **G4 Asks well.** It requests the evidence that would change the board, once,
  and does not wait idle for the reply.
- **G5 Order-independent.** The same documents in a different order or at different
  times give the same board, up to model noise.
- **G6 Comparable.** Two local models can be compared on a fixed simulation, scored
  against the reference board.

The reference board's own statuses are the target vocabulary: observed event,
reported interpretation, proposed mechanism, unresolved premise; support status
supported / proposed / unresolved; combination AND / OR / unspecified. Our board
today has claim kinds and an incident status, not these. That mapping is part of T10.

## Task list

Each task: what it must achieve, how we would know, what the research offers, what
is uncertain.

### T1 Retrieval: find the right sentences (G1, G3)
- **Must achieve:** for each claim, the sentences that bear on it are in the
  candidate set, and few others are.
- **Acceptance (proposed):** recall of 100% on the key sentences the reference board
  needs (starting with the 3 valve sentences and the sealing-test sentence); share of
  assessments with nothing extracted falls well below the current 82%; measured on
  real queries from saved runs before any live run.
- **Research:** hybrid BM25 plus dense with MMR to cut redundancy
  ([TRUST Agents](https://arxiv.org/pdf/2604.12184)). [MERMAID](https://arxiv.org/html/2601.22361)
  keys evidence by entity, recalls BM25 top-3 chunks then re-ranks sentences
  semantically (top 20), de-duplicates, applies a diversity filter and a token cap;
  hybrid recall beat BM25-only (Macro-F1 0.76 to 0.80 on BingCheck). Local
  cross-encoder rerankers exist for Ollama
  ([guide](https://www.codewords.ai/blog/ollama-reranker)); vendor claims of
  double-digit gains, no claim-verification test found.
- **Plan implied:** stopwords plus a 2-shared-term floor (cheap, offline-testable),
  entity-keyed lookup (valve ID, component names, times), then an optional reranker
  only if the gold set shows the lexical stage still leaves noise. Neighbour window:
  untested in the literature, so we decide on our own data.
- **Uncertain:** a reranker or embedding model is a download; neighbour-window
  benefit is unmeasured anywhere I looked.

### T2 Absorb a new document (G3, G5)
- **Must achieve:** a new document, however it arrives, is checked against every
  existing claim; findings are incorporated; if nothing matches it simply joins the
  pool; unrelated work is not marked stale.
- **Acceptance:** zero stale jobs caused by a document that matches no claim; every
  claim shows a recorded check against every document (or a recorded skip reason);
  shuffled-arrival runs (T9) give the same board.
- **Research:** [AGM-Bench (ICLR 2026)](https://iclr.cc/virtual/2026/10017503):
  models violate minimal change and preservation, with "belief inertia" and
  "collateral damage" under repeated revision, so selection of what to redo belongs
  in deterministic code. A cheap screening gate before costly extraction removed
  15-30% of papers in one literature pipeline, with fail-open handling of parse
  errors ([2607.22574](https://arxiv.org/pdf/2607.22574)), but LLM relevance
  judgements can be fooled ([2601.08919](https://arxiv.org/abs/2601.08919)).
  No 2026 paper found on re-checking earlier claims as evidence arrives.
- **Plan implied:** per-claim retrieval over the new document (T1), judge only
  matches, record the result. Any model gate must fail open.

### T3 Settle, stop, budget (G4, G5)
- **Must achieve:** with the current documents the system reaches a state where
  nothing is left to do, says so, and waits; the budget is a runaway guard only.
- **Acceptance:** `settled_awaiting_input` reached on the full packet; no queued
  work left at the end; budget counted in model calls.
- **Research:** [HALT](https://arxiv.org/abs/2608.02009) stops only when every
  required claim is covered. A small verifier (Qwen2.5-3B plus adapter) labels each
  claim-sentence pair match / partial / null and keeps the strongest label seen, so
  coverage only grows. With claims generated from the question it cut search loops
  by 17% / 18% / 2% on three benchmarks with exact match preserved; with gold claims,
  20-45%. In an open corpus it fired on only 6.4% of questions and abstained
  elsewhere. Generated "required claims" matched gold only moderately (F1 0.455 to
  0.701). QA benchmarks, not RCA.
- **Plan implied:** per-claim coverage status (match / partial / none), monotone as
  documents accrue; settled means every open claim has a status against every
  available document. Expect the stop to fire rarely on real cases; that is fine.

### T4 Judge support, contradiction, insufficiency (G1, G2)
- **Must achieve:** "supports" and "contradicts" only when a sentence really bears
  on the claim; otherwise "does not address" or "insufficient"; an absent record is
  never a contradiction or a resolution.
- **Acceptance:** on a gold set stratified by case type (direct support, direct
  contradiction, silent, related-but-insufficient, absence-of-record), error rate
  reported per type, not only overall; repeat judgements agree with each other and
  with the gold.
- **Research:** [NEI paper](https://arxiv.org/abs/2605.26663): insufficient-evidence
  skill does not transfer across how cases are built, aggregate scores hide it,
  models confidently pick support or refute; report by construction type.
  [Abstention-aware reasoning](https://arxiv.org/abs/2602.14189): split into
  minimal conditions, check each, abstain when short; abstention controlled error.
  [Local judges](https://arxiv.org/abs/2609.13824): `qwen2.5:7b` and LLaMA-3-8B were
  92-97% self-consistent but correlated only 0.28-0.34 with humans (general scoring).
  [Assessors study](https://arxiv.org/abs/2601.08919): LLMs cannot replace human
  assessors.
- **Mixed evidence on decomposition:** retrieval often covers only some fact units
  ([SUCEA](https://arxiv.org/pdf/2506.04583)); gains depend on method and can add
  noise; sub-claims need decontextualisation (which outage, which time). Our split
  claims (valve closed / checklist completed) lack that context.
- **Plan implied:** build the gold set first (T9); give the assessor an explicit
  abstain path; attach time and component context to split claims; measure whether
  splitting helps on our data.

### T5 Requests (G4)
- **Must achieve:** ask only for evidence that would change the board and is not
  already held; do not repeat a question; record why any request was rejected.
- **Acceptance:** no duplicate open requests; every rejection stores the rule that
  fired; absence-of-record statements never close a request.
- **Research:** [InfoGatherer](https://arxiv.org/pdf/2603.05909),
  [Ask or Assume?](https://www.alphaxiv.org/abs/2603.26233),
  [PROPER Agents](https://www.alphaxiv.org/abs/2601.09926): ask when the gap blocks
  progress, highest-value first, capped, otherwise proceed on stated assumptions
  (abstracts only). NASA event-and-causal-factor practice: do not eliminate a cause
  without solid data
  ([overview](https://oneuptime.com/blog/post/2026-07-31-five-whys-vs-causal-tree/markdown),
  blog; primary NASA documents not retrieved).
- **Uncertain:** HERA's post-checks overrode at least 4 of 9 "eligible" replies;
  which checks fired is not recorded, so we cannot yet say they are wrong.

### T6 Claim hygiene (G1, G6)
- **Must achieve:** one claim per proposition; later proposals reuse or supersede.
- **Acceptance:** no two live claims with the same normalised text; superseded
  claims keep history.
- **Research:** exact match, then semantic match above a threshold, or a three-way
  update / no-op / add decision over candidates sharing a tag; mark old items invalid
  rather than delete ([AIM](https://arxiv.org/pdf/2609.12320),
  [Mem0](https://arxiv.org/pdf/2504.19413), [PlugMem](https://arxiv.org/pdf/2603.03296)).
- **Plan implied:** deterministic match first; model only for borderline pairs.

### T7 Output reliability (G1)
- **Must achieve:** a single bad model reply costs one job, and common slips are
  prevented, not only contained.
- **Acceptance:** zero ID-class failures; every prompt rule has a matching validator
  and test.
- **Research:** constrained decoding guarantees shape, not values; small models err
  inside valid structure (blog posts, anecdotal)
  ([example](https://shop.zimaspace.com/blogs/tech-ai-hub/small-local-models-hallucinate-json-output)).
- **Plan implied:** per-call schema with the valid IDs as an enum, which removes the
  `mat_` slip by construction; prompt-versus-validator audit of every role.

### T8 Custodian simulator (G4, G5, G6)
- **Must achieve:** answers any question from a fixed fact sheet built from the
  incident description and final RCA findings; says "unknown" where the reference
  board has an unresolved condition; independent of the model under test; also
  returns uncooperative replies and delivers documents mid-work.
- **Acceptance:** the same question gets the same answer in every run; both models
  face identical knowledge; trace saved.
- **Research:** a fixed profile or script makes agents comparable
  ([SimulBench](https://arxiv.org/pdf/2409.07641)); naive user prompting is verbose
  and unrealistic ([MirrorBench](https://arxiv.org/html/2601.08118v1)); grounded
  simulators are harsher by about 3 points
  ([RealUserSim](https://awesomepapers.io/papers/2605.20204)).
  [MERMAID](https://arxiv.org/html/2601.22361) found a fixed evidence memory built by
  a stronger model lifted LLaMA-3.1-8B from 0.54 to 0.65; so the custodian's help
  must not leak the answer, or it will mask model differences.
- **Uncertain:** realism against real custodians is unvalidated.

### T9 Ground truth, scoring, repeat runs (G5, G6)
- **Must achieve:** a number for "how close is this board to the reference", stable
  across runs.
- **Acceptance:** rubric from the reference board (35 nodes, links, 11 open
  questions); scoring for node coverage, link coverage, unsupported claims, and
  unresolved items kept unresolved; N repeated runs per configuration; "same board"
  defined as same claims with evidence on the same key sentences.
- **Research:** [ORCA-bench](https://arxiv.org/abs/2607.28545) (software oncall):
  best accuracy 25.3% medium, 10.0% hard; weakest model hallucinated an implausible
  cause in 40% of reports; shows why unsupported-claim rate must be scored.
  Failure taxonomies exist ([Kim 2026](https://cloudintelligenceworkshop.org/papers/aiops26-Kim.pdf)).
- **Ground truth (resolved 2026-10-30):** the human CauseLink report
  `01 - Original Supplied R3 RCA Chart.pdf`, transcribed and confirmed in
  `ground_truth/r3_human_rca_chart.json` (23 nodes, 8 solutions). The gold evidence
  map for E01-E16 is `ground_truth/evidence_map_draft.json`, also confirmed. The
  Downloads HTML board is a produced chart, not the truth; do not score against it.
  Nodes with no evidence in the packet (G14, G15, original design intent) must stay
  unresolved, not be filled in.

### T10 Board vocabulary and quality (G2)
- **Must achieve:** nodes carry the reference statuses (observed, reported
  interpretation, proposed mechanism, unresolved premise) and links carry
  AND/OR/unspecified; the board proposes the central chains and marks them unresolved
  when evidence is missing.
- **Research:** NASA practice separates what evidence says occurred (event and
  causal factor tree) from possible causes (fault tree)
  ([overview](https://oneuptime.com/blog/post/2026-07-31-five-whys-vs-causal-tree/markdown));
  reports separate proximate, root and contributing factors. Nothing found on
  generating such charts from industrial documents.
- **Uncertain:** whether the Specialist's rules can reach the hydraulic chain at all;
  not yet checked (audit "not yet checked").

### T11 Observability and hygiene (G6)
- **Must achieve:** each override, rejection and skip records its reason; outputs
  are small enough to keep; the environment is checked before a run.
- **Acceptance:** reason fields present; output under a few MB without raw
  responses (stored separately); a startup check for the interpreter and `clingo`.

## Order that the dependencies suggest
T9 and T8 first (fixed simulation and a gold set, so every later change is measured),
then T1, T2, T3 together (they interlock), then T4, T5, T6, T7, T10, T11.

## Not found in research
Re-checking earlier claims as evidence arrives; measured gains from
neighbouring-sentence windows; cause-and-effect charts built from industrial
incident documents. "Not found in two rounds of search", not "does not exist".

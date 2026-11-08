# Research brief — one task per problem (searched 2026-10-30)

How to read this: I ran 14 searches and opened 5 papers (arXiv abstract pages).
Everything marked "abstract" comes from the abstract or search snippet only; I did
not read the full papers. Where sources are blog posts rather than papers I say so.
Nothing here has been tried in our harness. Several of our problems have no direct
2026 research; I say where.

## T1 Retrieval noise and context window (F5)
- **Standard recipe:** hybrid lexical + dense scoring over overlapping passages,
  with Maximal Marginal Relevance to cut redundant evidence
  ([TRUST Agents, arXiv 2604.12184](https://arxiv.org/pdf/2604.12184), abstract).
- **Sentence-level choice:** a 2025 shared-task study compared top-3 BM25 sentences
  with top-3 embedding sentences, and with whole documents, which kept context but
  added off-topic text ([ClaimIQ, arXiv 2509.11492](https://arxiv.org/pdf/2509.11492)).
- **Neighbouring-sentence window ("sentence window", "small-to-big"):** described
  in tutorials and glossaries only. I found no measured precision result for
  evidence verification; the sources themselves say to measure before adopting
  ([example](https://barkingiguana.com/writing/parent-document-retrieval-small-chunks-big-context/)).
- **For us:** stopwords + minimum overlap is within normal practice, and our offline
  replay on real queries is the right way to tune it. Adding dense scoring needs a
  local embedding model (a download; I would ask first). MMR targets our repeated
  identical sentences. The window must be measured on our own queries.

## T2 Documents arriving late: re-check only what is affected (F1, F4)
- **No 2026 work found** on streaming re-verification of earlier claims when new
  evidence arrives. Closest: iterative retrieve-and-verify loops (FIRE, 2024),
  persistent evidence memory reused across claims
  ([MERMAID, arXiv 2601.22361](https://arxiv.org/pdf/2601.22361)).
- **Belief revision:** [AGM-Bench (ICLR 2026)](https://iclr.cc/virtual/2026/10017503)
  reports LLMs show "belief inertia" (keeping retracted information) and
  "collateral damage" (retracting beliefs the new evidence did not touch)
  (snippet). A 2026 survey traces dependency-tracked updating back to truth
  maintenance systems ([arXiv 2608.14567](https://arxiv.org/pdf/2608.14567)).
- **For us:** this supports your design. Decide what a new document touches in
  deterministic code (retrieval per claim plus dependency tracking), not by asking
  a model which beliefs to drop. CFERP's dependency invalidation is already of this
  kind; it fails only because unprompted documents arrive with no known dependencies.

## T3 Settling and the budget (F2, F3)
- **Stopping on evidence coverage:** [HALT (arXiv 2608.02009, Findings of EMNLP
  2026)](https://arxiv.org/abs/2608.02009) stops searching only when accumulated
  evidence supports every required claim, and stops without a confident answer when
  coverage cannot be verified. It reports less redundant search with exact match
  largely preserved; the abstract gives no figures.
- **Cost-aware stopping:** [CAM-DF, arXiv 2607.27083](https://arxiv.org/pdf/2607.27083)
  (tool acquisition, offline replays); semantic early stopping
  ([arXiv 2606.27009](https://arxiv.org/abs/2606.27009)).
- **Practice:** layered termination (hard budget, step cap, completion signal) —
  opinion posts, not studies
  ([example](https://tianpan.co/blog/2026-05-07-tool-call-convergence-agents-stopping-criteria)).
- **For us:** define "settled" as every claim either covered, or checked against
  every available document with nothing found; keep the budget only as a hard guard
  and count model calls. A result of "stopped, coverage unverified" is legitimate.

## T4 Judging: support, contradict, or not enough information (F6, F10)
- [Evidence Absence Is Not Evidence Insufficiency (arXiv 2605.26663, Findings of
  EMNLP 2026)](https://arxiv.org/abs/2605.26663): the ability to say "not enough
  information" does not transfer reliably between ways of constructing such cases;
  a good aggregate score can hide it. Report results by construction type.
- [Abstention-Aware Scientific Reasoning (arXiv 2602.14189)](https://arxiv.org/abs/2602.14189):
  split a claim into minimal conditions, check each with NLI, abstain when evidence
  is insufficient. Abstention, not model choice, controlled error.
- A small NLI verifier showed not-enough-information recall of only about 44–47%
  ([model card](https://huggingface.co/DeliVali/AIDAM_VREAL_279M_V1.0.0); not a paper).
- [Local judges (arXiv 2609.13824)](https://arxiv.org/abs/2609.13824): LLaMA-3-8B and
  Qwen2.5-7B were 97.3% and 92.3% self-consistent but correlated only 0.275 and 0.340
  with human ratings. Small study, general answer scoring, not stance labelling.
- **For us:** self-consistency is not accuracy, so we need a small human-labelled gold
  set (from your reference board). Splitting compound claims into conditions matches
  what our Specialist already does. The assessor needs a real abstain path and a rule
  that a missing record is not a contradiction or a resolution.

## T5 Requests and information gaps (F9–F11)
- Common design: detect the gap, judge whether it blocks progress, ask only the
  highest-value question, otherwise proceed on stated assumptions, cap questions
  ([InfoGatherer, arXiv 2603.05909](https://arxiv.org/pdf/2603.05909);
  [Ask or Assume?, arXiv 2603.26233](https://www.alphaxiv.org/abs/2603.26233);
  [PROPER Agents, arXiv 2601.09926](https://www.alphaxiv.org/abs/2601.09926);
  all abstract/snippet).
- **For us:** request dedupe, a "blocks progress" test and a cap are standard. The
  resolved-by-absence mistake is the T4 problem again. Our own override rules need to
  record which check fired.

## T6 Duplicate claims (F7)
- Memory systems use exact match, then semantic match above a threshold; or a
  three-way LLM decision (update / no-op / add) over candidates found by shared tags;
  conflicting items are marked invalid, not deleted
  ([AIM, arXiv 2609.12320](https://arxiv.org/pdf/2609.12320);
  [Mem0, arXiv 2504.19413](https://arxiv.org/pdf/2504.19413);
  [PlugMem, arXiv 2603.03296](https://arxiv.org/pdf/2603.03296)). A quoted 0.92
  similarity cutoff comes from a how-to page and is unverified.
- **For us:** normalised-text and entity match first, model only for borderline pairs;
  supersede, never delete (CFERP already has a superseded state).

## T7 Structured output and the ID slip (F13)
- Constrained decoding guarantees shape, not correct values; small models still err
  inside valid structure; retry only the failed part (blog posts, anecdotal)
  ([example](https://shop.zimaspace.com/blogs/tech-ai-hub/small-local-models-hallucinate-json-output)).
- **For us:** put the valid IDs in the schema as an `enum` per call, so the grammar
  rules out `mat_…` where `cl:…` belongs. No benchmark for small Ollama models found.

## T8 Simulated custodian and fair comparison (F12–F13)
- Fixed profile or frozen script makes agents comparable
  ([SimulBench](https://arxiv.org/pdf/2409.07641)). Naive "act as a user" prompting
  is verbose and unrealistic ([MirrorBench, arXiv 2601.08118](https://arxiv.org/html/2601.08118v1)).
  Simulators grounded in real behaviour are harsher: about 3 points lower task success
  than cooperative ones ([RealUserSim, arXiv 2605.20204](https://awesomepapers.io/papers/2605.20204)).
  Simulators reached ρ≈0.7 with human judgements on two tasks
  ([SimulatorArena](https://preview.aclanthology.org/setup/2025.emnlp-main.1786)).
- **For us:** the fact-sheet design with a pinned model fits. Include uncooperative
  replies (partial, irrelevant, "we don't have it"), since cooperative simulators
  overstate success. Simulator realism stays unvalidated against real custodians.

## T9 Measuring RCA quality (F14–F15, F8)
- [ORCA-bench (arXiv 2607.28545)](https://arxiv.org/abs/2607.28545), latest version:
  1,079 oncall tasks; best accuracy 25.3% on medium and 10.0% on hard; weakest model
  proposed an implausible root cause in 40% of reports. The search snippet gave 884
  tasks and 48.8%, so versions differ; trust neither without reading the paper. It is
  software oncall, not physical incidents.
- Failure taxonomies: 12 pitfall types on OpenRCA ([Kim 2026](https://cloudintelligenceworkshop.org/papers/aiops26-Kim.pdf));
  16 multi-hop reasoning failures (Riddell, FORGE '26).
- Event and causal factor trees record what evidence says occurred; fault trees
  explore possible causes; AI is described as automating evidence gathering, not
  judgement (blog posts: [one](https://oneuptime.com/blog/post/2026-07-31-five-whys-vs-causal-tree/markdown)).
- **For us:** score against your reference board and label our run failures with a
  taxonomy. Keep the board from declaring a root cause, as it does now.

## T10 Symbolic search (SAHS)
- LLMs writing ASP with self-correction loops
  ([arXiv 2604.27960](https://arxiv.org/pdf/2604.27960)). No 2026 study of our
  combination found. Low priority.

## Gaps in this search
No direct 2026 research found on: streaming re-verification (T2), measured gains for
neighbour-sentence windows (T1), or building cause-and-effect charts from incident
documents in industrial settings (T9). That means "not found in 14 searches", not
"does not exist".

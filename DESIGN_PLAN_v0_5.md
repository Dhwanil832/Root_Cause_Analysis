# Design plan v0.5: fixing the loop, not the symptoms

Written 2026-11-11. This is a plan for discussion. No code has changed.

## Why

The recent gpt-oss runs fail in many ways: the claim cap, neutral assessments,
duplicate claims, missing evidence, no cause chain. Most of these trace back to three
gaps in how the Lead runs the loop. The figures below are from
`fix4_reserve32k_gpt-oss-20b_fixedcustodian_run1.json`, the best run so far.

| Gap | In the code | What it causes |
|---|---|---|
| **1. Assessments never become a status.** | A claim's status is set once when it is created (`cferp/workflow.py:443`). A link is always `candidate` (`:478`). Nothing in the pipeline changes either afterwards. Assessments are stored as notes only. | The board cannot say what the evidence shows, so no cause chain can appear: 39 of 40 claims are `not_applicable` and all 34 links are `candidate`. The Lead cannot tell which claims matter, so it revisits after every note (114 revisits, 70% of assessments neutral). |
| **2. Only claims already on the board drive work.** | Work starts from the Specialist's own needs. A new document is searched only for needs already open (`register_material`, `:1363`). After the first 4 jobs, every Specialist job was a revisit of an existing claim. | Evidence that fits no current claim never reaches the Specialist, for example "seepage with the handle closed" and "only one keeper". Results depend on arrival order. |
| **3. Cause links are never checked.** | All 185 need targets were claims. The Evidence Worker and Assessor handle only claim–sentence pairs. | Nothing asks whether the evidence shows A led to B. |

The remaining failures follow from these:
- **Claim cap:** the Specialist's 40-claim limit counts the whole board (`sahs/engine.py:116`). Nothing merges or retires claims, so late Specialist jobs fail.
- **Contradictory times:** two claims give different times for the backup-roll removal, and both sit on the board unresolved. Nothing turns a contradiction into a visible conflict.

Underneath all three, the Evidence Worker's search never returns about a third of the
gold sentences, however many results it takes (Step 5).

Only one failure is a true one-off: the Assessor sometimes cites text outside its
packet. Python rejects it correctly. The fix is to give the model the list of IDs it
may use.

## What stays the same

- **Five roles:** the same five, each with the same job.
- **Python decides status:** the model proposes and judges single passages, and deterministic code decides what a claim's or link's status is.
- **No declared root cause:** nothing declares a root cause. A missing record is a gap, never a finding.
- **Fixed custodian:** stays deterministic and independent of the model under test.
- **Old behaviour stays available:** every change below is behind a switch that is off by default, so v0.4 runs can be reproduced.

## Step 0: measure properly first (no model calls)

Without this we can't tell whether any step helps.

1. **Count a support only on the right claim.**
   - **Today:** "expected supports" credits a support given to any claim (`score_against_truth.py:133`).
   - **Change:** count it only when the supported claim matches that sentence's chart node.
   - **Also report:** supports on the wrong claim, which catches cases like "carrier not raised" supporting "carrier raised".
2. **Check claims that aren't on the chart.** For each one, report whether it cites a sentence that really appears in a document. You said such claims aren't failures, so the measure is grounded or not.
3. **Score links.**
   - **Edges:** compare the board's links with the chart's 22 cause-and-effect pairs, using the matched nodes at each end. (Done: `score_against_truth.py`.)
   - **Unsupported nodes:** check that nodes the packet can't evidence (G14, G15, the design-intent nodes, G22) are never shown as supported.
4. **Score status once Step 1 exists.**
   - For each chart node, report the board's status alongside what the evidence map says.
   - "Insufficient" sentences must not produce a "shown" status.
5. **Re-score every saved run** with the corrected scorer, so v0.4 has a fair baseline.
6. **Measure noise.** Repeat the best v0.4 setting at least once more (~5 h) with `run_repeats.py`, so we know how big a difference counts.

## Step 1: a status for every claim and link (Gap 1)

A new deterministic module in the Lead (`cferp/status.py`). It reruns after every
committed result and records its output as an event.

**A support must cover the whole claim.** Many claims join several facts, such as "Valve
IV-RB3-17 was isolated at 11:10". A passage can support one part (the B supply was
isolated at 11:10) and leave another open (that this valve was the one). So:

- **Parts are fixed when the claim is made.** The Specialist lists a claim's parts when it proposes it, for example `valve IV-RB3-17` / `was isolated` / `at 11:10`. Python checks that each part is a phrase from the claim, and that together they cover all of it.
- **The Assessor marks parts.** For each passage, it says which of those listed parts the passage supports, contradicts or leaves open. Because the list is fixed, assessments from different passages can be combined.
- **Status follows the parts.** A claim is `shown` only when every part is shown, by one passage or several. Otherwise it is `partly shown`.
- **Missing parts become needs.** Each part still missing becomes a need automatically, so the next search targets what's missing.

**The Assessor's answers become** `supports`, `consistent_with`, `insufficient`,
`not_relevant`, `weakens`, `contradicts`, replacing the single `neutral`:
- **`consistent_with`:** the passage fits the claim but doesn't show it.
- **`insufficient`:** the passage bears on the claim but can't settle it. This includes a record saying something wasn't measured or can't be told.

- **`not_relevant`:** the passage doesn't bear on the claim at all, which is usually retrieval noise. It doesn't count as checking the claim, and the count of these is a measure of retrieval noise for Step 5.

Old runs keep `neutral` as it is when re-scored, since it can't be split after the fact.

**Independent sources.** A support counts once per original source:
- **Origin records:** Intake records where each document says it comes from. For example, E16 says "Prepared from workshop record VAL-17. No additional examination…".
- **Matching:** Python matches that identifier to the document that carries it, so VAL-17 matches E08.
- **Counting:** supports from E08 and E16 count as one source.
- **Unknown origin:** a document whose origin is unknown counts as independent, and the status view shows that the count assumes it.

**Claim status**, from the current (not superseded) assessments:

| Status | Rule |
|---|---|
| `shown` | Every part of the claim is supported, and there is no current `contradicts`. |
| `partly shown` | Some parts are supported and none is contradicted. The missing parts are listed. |
| `contested` | A current `supports` and a current `contradicts` on the same part. |
| `contradicted` | Current `contradicts` and no `supports`. |
| `open` | Only `consistent_with`, `insufficient` or `weakens` so far: checked, but not settled. |
| `unchecked` | No assessment yet, or only `not_relevant` ones. |

Each status also carries the number of independent sources behind it. The reported
incident claim stays `reported`.

**Link status:**
- **Provisional rule:** until Step 3 exists, a link is `proposed`, or `both ends shown` when both its claims are `shown`.
- **After Step 3:** a link becomes `shown` only when an assessment supports the link itself.
- **General mechanisms:** a passage that only describes a general mechanism makes the link a `possible mechanism`, never `shown`.

**Chain view.** Starting from the incident claim, follow the links backwards to list each
path and its weakest point. That is what the Lead aims work at in Step 4.

**When the investigation is settled.** Every claim and link on a path is either `shown`, or
`open` after being checked against every document. Running out of budget stays a
separate outcome, `stopped, coverage unverified`, and is reported as that.

**First check.** Run the module on the saved 32k board with no model, and read what it says
before going further. Old boards have no claim parts, no origin records and only
`neutral`, so this check treats each claim as one part, each document as its own source,
and `neutral` as `open`. It tests the rules and the chain view, not the new Assessor answers.

**First check, done (2026-11-11).** `cferp/status.py` with `scripts/board_status.py`, on
the saved 32k board:
- **Claims:** 5 shown, 7 contested, 3 contradicted, 1 open, 23 unchecked, plus the incident.
- **Links:** 34 in all; 4 have both ends shown.
- **Chains:** 15 paths lead back from the incident, and 24 claims are on none.

The rules work as written, but they show that many current assessments are wrong:
- **Absence read as support.** "No branch hydraulic pressure is visible" supports "pressure dropped". It should be `insufficient`.
- **Misreading.** "The examination was carried out after removal" contradicts "backup rolls were removed".
- **Traps taken as contradictions.** E13 (the replacement configuration) contradicts "keeper bolted"; E16 (a recap) contradicts "valve status unknown".
- **One passage supporting both a claim and its opposite.** E05 and E12 support both "raised at the fall" and "not raised at the fall".

The last one can be caught in Python: when the Specialist proposes a claim that denies another, it records the pair, and a passage that supports both is flagged for review. This is added to Step 1.

**Order (decided 2026-11-11):** each role first, the Lead last.

**Assessor, done (2026-11-11), in `hera1/`:**
- **New answer `consistent_with`:** it needs a cited statement and a bridge sentence, like a support.
- **New `not_recorded` modality:** set by Python when a quote says something was not recorded, not visible, not measured or can't be told. Such a statement can't support or contradict a claim unless the claim is itself about what was recorded or known; it becomes `insufficient_or_unclear` with a flag.
  - "No gross fracture … was recorded" is an inspection's finding, so it is left out of this rule.
- **IDs filled from the packet:** a quote's material IDs come from the packet when the model miscopies them, but only if exactly one packet material holds the quote. This replaces the "cited material outside the assigned packet" failure (5–6 per run).
- **Prompt:** defines each answer and how to judge the parts of one claim separately. It also says a record of a different object or configuration is not about the part (the E13 trap). That last point is guidance only, with no Python check.

**Specialist, done (2026-11-11), in `sahs/`:**
- **Parts:** each proposition now lists its `parts`. Python checks that each part is a phrase of the text (ignoring case and spacing), that no two overlap, and that together they cover every content word. Parts that fail are reported, and the claim is kept as one part, the strictest reading. One part, or none, means the whole claim.
- **Denials:** a proposition can name the propositions it `denies`, from the same proposal or the board. An unknown ID or a self-denial is dropped and reported, and the claim is kept.
- **Model answer:** the format schema now requires both fields, so the model always fills them. Python still accepts answers without them.
- **Prompt:** explains parts, with the valve example, and denials.

**Intake, done (2026-11-11), in `piris/origins.py`:**
- **Origin sentences:** Python finds each sentence in which a document says where it comes from ("prepared from", "compiled from", "copied from", "based on", "Source:" and similar), keeps it word for word with its offset, and lists the identifiers it names, such as `VAL-17`.
- **Matching:** each identifier is matched to the one other document that carries it, outside that document's own origin sentences, so two recaps of the same record don't match each other. A longer code (`VAL-170`) doesn't match. Two candidates leave it ambiguous and unmatched; none leaves it unresolved.
- **Arrival order:** matching runs over the whole case each time it is asked (`IntakeEngine.case_origins`), so a recap that arrives before its original is matched once the original arrives. A version replaced by a revision is left out.
- **Output:** a map from derived to original document, the shape `cferp/status.py` takes as `origins`, plus the unresolved, ambiguous and unnamed origin sentences. On the 16 documents it finds one match, E16 → E08, and no false ones. E16's other origin sentence ("from the hydraulic maintenance summary supplied on Day +3") names no identifier and is reported as unnamed.
- **Rule-based for now:** Step 2's model-tagged origin findings can feed the same matcher later. The pattern is the same for both models, so the comparison stays fair.

**Lead, done (2026-11-11), in `cferp/`:**
- **Claims carry parts and denials.** `sahs_result_to_cferp` copies `parts` and `denies` onto board claims. A denial naming an unknown claim or the claim itself is dropped; when a claim is folded into an existing one, denials pointing at it are renamed.
- **The Assessor gets each part.** A claim with two or more parts goes to the Assessor as one part each, with the whole claim beside it as `claim_text` (one prompt line tells the Assessor to judge the part alone). Each assessment row records its `part`.
- **No more folding.** The Lead keeps `consistent_with`, `insufficient` (from `insufficient_or_unclear`) and `not_relevant` (from `does_not_address`, and for a passage with nothing extracted). `neutral` stays valid so old boards load. The Specialist's prompt drops `not_relevant` annotations first, as it did `neutral`.
- **Claim types.** `component_state` and `unknown_condition` go to the Assessor as `incident_fact`.
- **Status on the board.** After each Assessor result the Lead works out the touched claims' status by the rules above, records each change as a `claim_status_changed` event, and opens a need for each missing part of a `partly shown` claim (`part:<claim>:<n>`, never opened twice), which queues a search for it.
- **Origins.** The Lead and `board_status.py` work out origins from the materials' text by Intake's rule. On the saved 32k board this finds E16 prepared from E08.
- **Denial conflicts.** The status view lists each passage that supports both a claim and one it denies. The saved boards have no denials, so this shows on new runs only.

**Not yet:** a part need is not closed when its part is later supported (the need resolves the usual way, by its search and review). Links are still `proposed` or `both ends shown` until Step 3.

## Step 2: documents drive work too (Gap 2)

1. **Intake findings.**
   - **Extraction:** when a document arrives, Intake uses the model to list its findings. Each finding is the exact sentence plus a tag: observation, measurement, record, statement, absence, or origin. Origin covers a statement of where the document comes from, such as "Prepared from workshop record VAL-17", and is used for independent sources (Step 1).
   - **Checks:** Python rejects any quote that isn't in the document.
   - **What Intake still doesn't do:** judge relevance or write claims, so its existing boundary holds.
   - **Already tested:** this captured 23 of 23 key sentences with no invented quotes, in about 10 minutes per run.
2. **One Specialist job per document.**
   - **Job:** the Lead queues one "review this document" job, with the document and its findings.
   - **Instruction:** propose claims for anything that matters and that no claim accounts for, and list what's missing as information gaps.
   - **Prompt size:** the job sees the board's claim text only, which keeps its prompt small.
3. **Catch-up passes for findings nothing uses.**
   - **The problem:** a document reviewed early saw a small board. A finding that seemed unimportant then may matter once later documents arrive.
   - **Re-reading everything isn't the fix:** reviewing every document again costs another 16 Specialist jobs per pass, and mostly repeats work.
   - **What the Lead does instead:** it works out which findings are still unaccounted for. Python can do this exactly, with no word matching: a finding is accounted for when some claim cites its sentence or some assessment has used it.
   - **The pass:** after the last document wave, one Specialist job gets only the unaccounted findings, grouped by document, with the claim text of the board.
   - **When to stop:** repeat while the last pass added a claim, up to 2 passes. If findings are still unaccounted for after that, the run reports them rather than hiding them.
   - **Also mid-run:** the Lead runs the same catch-up whenever a document arrives that adds a new claim, but only for documents reviewed before that claim existed.
   - **Check:** run the same case in two different arrival orders and compare the boards. This is the first real test of order independence (goal G5).
4. **Duplicates:** new claims go through the existing duplicate folding (`_fold_duplicates`).

**Already tested:** directing the Specialist at a document gave 21–29 new claims grounded in
the source, against 1 claim with no source. Not yet tested: whether these claims then get
assessed and form a chain.

## Step 3: links can be checked (Gap 3)

- **Needs:** a causal link becomes a target the Evidence Worker can search for, like a claim. The search is built from the cause, the effect, and the link's conditions.
- **Assessor question:** "Does this passage show that A led to B in this incident, describe the mechanism in general, or neither?"
- **Status:** the answer feeds the link rules in Step 1.
- **Contracts:** the existing ones stay. A link ID becomes an allowed target, and the Assessor gets one new answer field for "general mechanism".
- **Links have parts too:** cause, effect, and each condition. A link is `shown` only when the passages cover all of them, by the same rules as claims.

## Step 4: the Lead owns priorities and board size

- **Revisit only on change.** Revisit a claim only when its status changes, not after every assessment. This alone should free a large share of the 114 revisit jobs.
- **Aim at weak points.** Order work by the chain view, so the weakest point on each path to the incident goes first. Requests to the custodian follow the same order.
- **Move the cap.** The Specialist's limit applies to what one proposal adds, not to the whole board. The Lead keeps the board in shape:
  - it folds duplicates;
  - it marks `contradicted` claims so they stop drawing work, without deleting them;
  - it turns conflicting claims, such as the two backup-roll times, into one explicit `contested` question.
- **No pruning for relevance.** Claims aren't removed because they look off-topic, so exploring outside the chart stays allowed.

## Step 5: retrieval that finds what the claims need

The Evidence Worker's search is how a claim or link meets its evidence. Step 2 lowers
that dependence, because a claim born from a document already cites its sentence.
Step 3 raises it, because checking links relies entirely on search. So weak retrieval
caps everything else.

**Where it stands.** `scripts/retrieval_bench.py --default` queries with the chart node
texts and scores against the evidence map, with no model:

| Top K | Gold sentences found | Share of results that are gold |
|---|---|---|
| 4 | 39% | 21% |
| 8 (as in runs) | 46% | 13% |
| 16 | 63% | 12% |
| 32 or 64 | 65% | 11% |

- **A hard ceiling with two causes.** The default search is already word matching plus BM25, but it returns at most 8 documents with 4 passages each, so about a third of the gold sentences are never returned however large K is.
  - **Lifting the document limit:** 16 documents with 8 passages each raises the ceiling to 75%. That costs nothing, but it raises noise unless the ranking also improves.
  - **What's left:** the remaining quarter share no words with the query at all, so word search can't reach them. For example, "Yoke drifted but carrier beam did not" doesn't match the documents' own wording. This is a matching problem, not a ranking one.
- **Noise:** most results aren't gold.
- **In the 32k run:** 46 of the 114 assessed passages were not sentences from the evidence map, and 31 of those came back neutral.

The node texts are terser than real claim queries, so this benchmark is harsher than a
run. The ceiling is still real.

**Plan.** Each part is measured with the benchmark before the next is added:
1. **Real queries:** build a second benchmark set from the queries the saved runs actually sent, paired with the gold sentences those claims needed. This is the honest test.
2. **Document limit:** test 16 documents with 8 passages each, which gives 75% instead of 65% at large K, against the noise it adds.
3. **Entity and time lookup:** match equipment IDs (IV-RB3-17, RB-3), component names (keeper, yoke, link arm) and times (11:10, 13:03) directly. This needs no model.
4. **Dense search added to word search:** `HybridRetriever` and `DenseVectorRetriever` already exist in `ewv3/retrieval.py` but need an embedding model. That's a download, so I'd ask first. This should close the vocabulary gap.
5. **Redundancy filter:** use maximal marginal relevance so repeated sentences, like E16 restating E08, don't fill the top K.
6. **Wider net, model filter:** take more candidates (K = 16), and let the Evidence Worker's model choose among them. Check that this doesn't just move the noise to the Assessor.

**Target, to be confirmed after Step 0:** close to 100% recall on the key sentences, with the noise passing through to the Assessor going down, not up.

## Step 6: small fixes

- **Assessor IDs:** pass the allowed material IDs to the Assessor as an `enum` in its output schema.
- **Search limit:** look at why the Evidence Worker reaches its query limit (2 failures).

## Order and checks

| Order | Step | Check before moving on | Needs a model? |
|---|---|---|---|
| 1 | Step 0, scorer | Old runs re-scored, numbers explained | No |
| 2 | Step 1, status | Status of the saved 32k board read by hand, unit tests | No |
| 3 | Step 4, revisit only on change | Replay shows fewer revisits, unit tests | No |
| 4 | Step 5, retrieval parts 1, 2, 3 and 5 | Both benchmarks improve | No |
| 5 | Step 5, retrieval part 4 (dense) | Both benchmarks improve | Embedding model, ask first |
| 6 | Step 2, document trigger | Unit tests, then one full run | Yes, ~5–6 h |
| 7 | Step 3, links | Saved-prompt test on a few links, then a full run | Yes |
| 8 | Step 6 | Unit tests | No |
| 9 | All on | Repeats against the v0.4 baseline | Yes, several runs |

The first four need no model and can be checked on saved runs or the benchmark. Each step gets its own
switch and its own tests in `V3_Neurosymbolic_Inspired/tests/`.

## What success would look like

Targets are set after Step 0 gives a real baseline. The measures:
- chart nodes covered;
- chart edges covered with a link;
- key supporting sentences landing on the right claim;
- "insufficient" sentences that produce `shown` (should be 0);
- nodes the packet can't evidence shown as supported (should be 0);
- claims off the chart that are grounded in a document;
- job failures;
- how far two runs agree.

## Decisions (2026-11-11)

1. **Status names:** `shown / partly shown / contested / contradicted / open / unchecked`. A support counts for `shown` only for the parts of the claim it covers, and every part must be covered (Step 1).
2. **Neutral is split** into `consistent_with`, `insufficient` and `not_relevant` (Step 1).
3. **Independent sources:** supports count once per original source, using the origin statements Intake records (Step 1).
4. **Final pass:** catch-up passes over unaccounted findings only, repeated while they add claims, up to 2. Not a full re-read (Step 2).

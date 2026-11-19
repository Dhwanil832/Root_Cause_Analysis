# Handoff: where v0.5 stands (2026-11-19)

The plan is `DESIGN_PLAN_v0_5.md`. Roles: PIRIS = Intake, CFERP = Lead, SAHS = Specialist,
EWV3 = Evidence Worker, HERA1 = Assessor. All 501 unit tests pass.

## What v0.5 Step 1 added
- **Specialist (`sahs`)**: optional claim `parts` and `denies`. Rule `modality` is fixed to the values
  `possible` and `conditional` in the output schema, because gpt-oss left it empty and the rules were dropped.
- **Assessor (`hera1`)**: `consistent_with`, `insufficient_or_unclear` and `not_relevant` replace
  `neutral`. It also has a `not_recorded` statement modality and repairs miscopied material IDs by
  matching the quote.
- **Evidence Worker (`ewv3`)**: gpt-oss grades the retrieved passages (`ewv3_grade_candidates`).
  Word search gained BM25, stemming and a cap of 8 documents x 4 passages.
- **Intake (`piris/origins.py`)**: detects which documents were prepared from others, for counting
  independent sources.
- **Lead (`cferp`)**:
  - `status.py`: the board status (shown / partly shown / contested / contradicted / open).
  - Merges duplicate claims and needs.
  - Passes earlier candidate links to the next Evidence Worker pass.
- **Custodian**: a fixed word-overlap custodian (`orchestration/custodian.py`) replaces the
  model-driven one, so it does not depend on the model under test.
- **Scripts**: `board_status.py`, `judge_claim_nodes.py`, and labels in `ground_truth/claim_node_labels*.`

## Last runs (outputs are not in git)
- **Run 1**: completed with 9 job failures.
- **Run 2**: crashed with "EWV3 passage source/version is outside the Lead snapshot", and had
  0 links on the board (the empty-modality bug, now fixed). Counts before the crash:

  | Measure | Count |
  |---|---|
  | Claims | 16 |
  | Assessments | 38 |
  | not_relevant | 26 |
  | supports | 4 |

- **Run 3**: stopped by the user. No full result.

## Open decisions (waiting on the user; do not implement without agreement)
1. **Scheduler fix.**
   - **The bug:** `V3PackageBridge.run_ready()` starts queued jobs without the stale-manifest
     refresh that `workflow.schedule()` does, so an old job can run on an out-of-date snapshot.
   - **Proposed fix:** refresh or replace an out-of-date job in `workflow.start_assignment()`, so a
     held investigation looks at what is available when it runs.
   - **Then:** remove the temporary snapshot filter in `cferp/integration.py`
     (`ew_assignment_from_cferp`, `prior_link_rows`). The user said to keep it for now.
2. **Move meaning judgments from code to gpt-oss.** In the user's order of concern:
   1. **Assessor regexes** in `hera1/validation.py`:
      - `_says_not_recorded` and `_has_clear_negation` overwrite the model's statement modality;
      - `_clear_time_mismatch` overrides the model's relation.
   2. **Duplicate claim and need folding** by word sets: `statement_meaning` and `_fold_duplicates`
      in `cferp/workflow.py`.
   3. **Search.** Only word matching decides what the model sees: `ewv3/retrieval.py`
      (min_shared=2, word lists, the 8-document cap) and `_topic_terms` in `ewv3/engine.py`.
      The user wants a model-based search; the proposal is for gpt-oss to read the documents for
      each need.
   4. **Origin detection by regex** in `piris/origins.py`.
   5. **Prompt trimming** by fixed order: `_fit_to_budget` in `sahs/prompt_builder.py`.
   6. **Word-coverage check on claim parts** in `sahs/validation.py`.

   Rules that only combine the model's own labels, and the status counting, stay in code.
3. **Predictable gpt-oss runs.** Temperature is already 0. Add a fixed seed, run one request at a
   time, and record and replay the real model calls (they are already saved in the run JSON under
   `model_calls`).
4. **The user mentioned new things they want to integrate.** Ask what they are before starting
   any of the above.

## Earlier conversation logs
`.claude/transcripts/` holds the two Claude Code session logs (main session and its fork), with the company, plant, address, email and screenshots removed. Search them for detail; HANDOFF.md above is the summary.

# Closed-loop V3 scenario runbook

This file is the operator guide for running and troubleshooting the V3 synthetic
R3 workflow. The implementation is in `V3_Neurosymbolic_Inspired/`; this guide
describes the control path and where to inspect behavior.

## What this run does

1. PIRIS receives the opening case packet and opening documents.
2. CFERP Lead builds/updates the investigation board and queues work.
3. The V3 bridge runs Specialist, Evidence Worker, and Assessor jobs within the
   configured job limit. Role calls use the configured model client.
4. Only requests that reached Assessor approval are dispatched by the runner.
5. The synthetic custodian sees only the current later-material wave. Its model
   call may select fixture document IDs and slot IDs; Python rejects unknown,
   duplicate, or extra values.
6. Selected documents are submitted as request-linked material through PIRIS.
   Other documents in the wave enter as unrequested uploads.
7. The role queue runs again. Later material can invalidate dependent work and
   trigger reassessment through the ordinary CFERP lifecycle.
8. After the fixture waves, unanswered requests get one bounded search across
   the fixture corpus per loop round. A no-match note explicitly says it is not
   proof that the requested record does not exist.
9. A hard round limit stops an unbounded sequence of newly generated requests.

The simulation does **not** decide the incident cause, mark a case closed, or
send messages to a real person. Human response and actual external dispatch
remain operator responsibilities in a real investigation.

## Files to know

| Path | Purpose |
|---|---|
| `V3_Neurosymbolic_Inspired/scripts/run_v3_closed_loop.py` | Scenario driver, dispatch/reply loop, output snapshot |
| `V3_Neurosymbolic_Inspired/orchestration/fixture_outward_responder.py` | Constrained model call and Python validation of selected IDs |
| `V3_Neurosymbolic_Inspired/orchestration/v3_runtime.py` | PIRIS-to-CFERP material registration and role queue boundary |
| `V3_Neurosymbolic_Inspired/cferp/` | Lead, queue, board, request lifecycle, versioning, and invalidation |
| `V3_Neurosymbolic_Inspired/sahs/` | Specialist candidate generation/search |
| `V3_Neurosymbolic_Inspired/ewv3/` | Evidence search and packet production |
| `V3_Neurosymbolic_Inspired/hera1/` | Assessor review |
| `V3_Neurosymbolic_Inspired/piris/` | Intake registration, extraction, indexing, and request linkage |
| `V3_Neurosymbolic_Inspired/tests/` | Role, lifecycle, integration, and closed-loop responder tests |
| `V3_Neurosymbolic_Inspired/examples/r3_synthetic_case.json` | Self-contained scenario definition relative to this archive |

## Run

From the combined archive root, install the V3 requirements and ensure Ollama
is running with a model already installed:

```bash
python -m pip install -r V3_Neurosymbolic_Inspired/requirements-sahs.txt
ollama list
python V3_Neurosymbolic_Inspired/scripts/run_v3_closed_loop.py \
  --provider ollama_native \
  --model <exact-tag-from-ollama-list> \
  --base-url http://localhost:11434 \
  --max-jobs 64 \
  --max-rounds 12 \
  --output outputs/r3_closed_loop.json
```

OpenRouter can be used instead by setting `OPENROUTER_API_KEY` in the shell and
omitting `--provider ollama_native`:

```bash
python V3_Neurosymbolic_Inspired/scripts/run_v3_closed_loop.py \
  --model <OpenRouter-model-id> \
  --output outputs/r3_closed_loop.json
```

If using the separate `R3_Synthetic_Example_Bundle.zip`, extract it and pass its
`r3_synthetic_case.json` path with `--case`. Its material paths are relative to
that JSON and remain inside the extracted bundle.

## Read the output

The JSON contains:

- `board`: current claims, causal links, branches, assessments, requests,
  needs, and registered materials;
- `work` and `assignments`: role queue state, including unfinished work;
- `lead_events`: ordered state changes from the Lead workflow;
- `intake_submissions`: each opening, response, and unrequested upload handled
  by PIRIS;
- `model_calls`: provider call records, including the synthetic custodian task;
- `closed_loop_simulation.outward_trace`: request dispatch, response source IDs,
  slot IDs, unrequested material arrivals, and round-limit events;
- `run_metadata`: provider/model label, job budget, completion status, and any
  caught failure.

`run_status: completed` means the runner reached its bounded end without an
exception. It does not mean every request was answered or the case is ready to
close. Inspect `board.requests`, `board.needs`, `work`, and the final case state.

### Run status, job failures, and exit codes

| `run_status` | Exit code | Meaning |
|---|---|---|
| `completed` | 0 | Reached its bounded end; no role result was rejected. |
| `completed_with_job_failures` | 2 | Reached its bounded end, but at least one job was rejected and recorded (below). |
| `failed_or_partial` | 1 | Aborted by an exception; `run_metadata.failure` says which. |

When a role's own engine reports that it rejected its output (SAHS, EWV3 or HERA
returned a failure status), the job ends `FAILED`, nothing from it is committed,
and the run continues. Each one is listed in `run_metadata.job_failures` (and at
the top level as `job_failures`) with the role, status, targets, and the engine's
reason, and the event log has an `assignment_failed` entry. The claim or passage
that job covered **stays unassessed**; a failed job is never evidence. The runner
stops with `failed_or_partial` once `--max-job-failures` (default 25; 0 aborts on
the first) is exceeded.

These still abort the run, because they point at the harness rather than one bad
reply: commit-gate errors from CFERP (for example unknown rule IDs), adapter
`IntegrationError`s, HERA/CFERP disagreeing about staleness, and code errors.

`completed_role_jobs` and `role_jobs_remaining` come from the bridge's own
counter, so they are correct even when a run aborts mid-queue. Outputs written
before this change show `[]` and a full remaining budget on aborted runs; do not
rely on those two fields in old files.

### Scoring runs

```bash
python V3_Neurosymbolic_Inspired/scripts/score_run.py outputs/run_a.json outputs/run_b.json
```

It prints reliability (status, what aborted it, job failures), efficiency (jobs
executed, model calls, extraction calls per assessor job, repeat work), evidence
signals (assessment mix, share with nothing extracted, distinct claim-and-sentence
pairs), and how far the loop got (requests dispatched and answered, waves arrived),
plus a completion tally across files. Use `--json` for machine-readable numbers.
These are workflow signals on synthetic fixtures. "Nothing extracted" is a proxy
for retrieval noise, not a measure of truth, and `neutral` can be correct.

### Fixed custodian (default)

`run_v3_closed_loop.py` now defaults to `--custodian fixed`. The simulated custodian is
deterministic and never uses the model under test, so two models can be compared on
the same simulated world. It lives in `V3_Neurosymbolic_Inspired/orchestration/custodian.py`
and is configured by `ground_truth/custodian_holdings.json` (documents it holds, when each
becomes available, when each arrives unprompted, and a few prepared statements).

- Time is a clock of completed role jobs; while the system is idle the clock jumps to
  the next due event, modelling waiting. Jobs run in small chunks (`--custodian-chunk`,
  default 3) so documents can arrive while work is still queued.
- A request is answered by word overlap with each document's topic words (at least two
  shared words): the matching document, a prepared statement, an explicit "no record"
  note, or, for every third unmatched request, an unrelated document. A held document
  that is not yet available is waited for, not refused.
- `--custodian model` keeps the older behaviour, where the model under test picks the
  documents. Do not use it to compare models.
- This is a scenario simulator. Its realism against real custodians is not validated.

### Scoring against the ground truth

```bash
.venv/bin/python V3_Neurosymbolic_Inspired/scripts/score_against_truth.py outputs/run.json --matches
```

It compares the board with `ground_truth/r3_human_rca_chart.json` and
`ground_truth/evidence_map_draft.json`: chart nodes covered (word-overlap match, listed
with scores so you can audit it), key sentences assessed and whether their stance is
sensible, nodes the packet cannot evidence that were wrongly filled in, which critical
documents were reached, and the packet's designed traps (a recap counted as a second
source, the replacement configuration used for the original). Node matching is crude;
read `--matches` before trusting a coverage number.

### Repeating a run

```bash
.venv/bin/python V3_Neurosymbolic_Inspired/scripts/run_repeats.py \
  --model gpt-oss:20b --runs 3 --output-prefix outputs/exp_name
```

Runs the same configuration N times, scores each, and reports mean, minimum and maximum
plus how much the runs agree (same nodes covered, same key sentences assessed). Raw model
responses are dropped from the saved files unless `--keep-raw` is given.

Use the project interpreter (`.venv/bin/python`, which has `clingo`). Run the Ollama
adapter tests with `PYTHONPATH=V1_V2_Prompt_and_Rules/source/RCA_Version_Labeled_Codebase`.

## Troubleshooting

- **Ollama connection refused:** start Ollama, verify `ollama list`, and use the
  exact installed model tag and local API URL.
- **Clingo import/solver error:** install `requirements-sahs.txt` in the same
  Python environment used to run the script. SAHS does not silently replace the
  configured solver.
- **Malformed custodian response:** inspect the `synthetic_custodian_response`
  call in `model_calls`. The runner requires exactly two arrays and rejects IDs
  outside the supplied item/slot lists.
- **Provider error or timeout:** inspect `run_metadata.failure` and the last
  model call. The runner preserves a diagnostic snapshot where possible; it
  does not invent a role result to continue.
- **Open work after execution:** inspect `role_jobs_remaining`, `work`, open
  needs, and requests. Increase `--max-jobs` or correct the concrete role or
  queue failure; do not interpret a bounded run as an RCA conclusion.
- **Round budget reached:** inspect the requests created in the last round.
  This guard indicates repeated request creation, not successful closure.
- **Unexpected causal claim:** inspect its candidate/assessment provenance and
  the role result that introduced it. The Specialist proposes candidates;
  Evidence Worker retrieves and packages material; Assessor evaluates it; Lead
  owns shared board changes.

## Validation

Run the V3 tests from its package directory:

```bash
cd V3_Neurosymbolic_Inspired
python -m unittest discover -s tests -p 'test_*.py' -v
```

The closed-loop responder's unit tests verify its output contract and ID bounds.
An end-to-end live run still requires a configured local or hosted model. The
fixture documents are synthetic research material, not authenticated R3 records.

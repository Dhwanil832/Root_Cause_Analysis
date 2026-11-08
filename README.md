# Root Cause Analysis with cooperating LLM roles

A research harness for building an incident root cause analysis (RCA) from documents,
using five cooperating roles driven by a local or hosted language model. It is tested
on one synthetic industrial incident and scored against a human-made RCA chart for
that incident.

The question it studies: can a model, split into bounded roles with Python checks
between them, keep investigating as documents arrive at any time, check each document
against every claim, ask for missing evidence, and build an RCA board without
declaring a root cause the evidence does not support?

This is research code (v0.4). It is not a product, and the results below come from
single runs on one case.

## The test case

**R3 carrier beam fall.** A raised delivery carrier beam on a rolling-mill roughing
stand fell into the mill pit and struck an equipment sled and a temporary scaffold.
Nobody was hurt. The case has 16 documents (E01–E16): the incident notice, functional
descriptions, inspection notes, test results, logs and statements. All of them are
synthetic research fixtures, not real company records.

Documents arrive in waves: some with the incident, some only when the system asks for
them, and some unprompted.

## How it works

| Role | Package | What it does |
|---|---|---|
| Intake | `piris/` | Registers each arriving document, extracts and indexes its text, and links replies to the request that asked for them. It does not judge evidence. |
| Lead | `cferp/` | Keeps the investigation board (claims, causal links, requests, open needs), queues work for the other roles, and redoes only the work a new document affects. |
| Specialist | `sahs/` | Proposes candidate causes and mechanisms as typed propositions and rules. Python validates them, and Clingo (answer set programming) composes candidate explanations. |
| Evidence Worker | `ewv3/` | Finds the sentences in the documents that bear on a claim and builds an evidence packet. |
| Assessor | `hera1/` | Judges each packet: supports, contradicts, or not enough information. It also approves outward requests for missing evidence. |

One closed-loop run goes like this:

1. Intake receives the incident notice and the first documents. The Lead builds the board.
2. The Specialist, Evidence Worker and Assessor jobs run, up to a job limit.
3. Requests the Assessor approved go to a **simulated custodian**, which releases the
   documents it holds. By default it is deterministic and never uses the model under
   test (`ground_truth/custodian_holdings.json`), so two models face the same world.
4. Released documents re-enter through Intake. The loop repeats until the waves run
   out or a round limit is reached.

The model proposes and judges. Python decides what a claim's status is, rejects
references to IDs that don't exist, and never lets the run mark a root cause on its
own. A missing record is treated as a gap, not as a finding.

## Ground truth and scoring

`ground_truth/` holds what runs are scored against:

- `r3_human_rca_chart.json`: a transcription of the human RCA chart for the case
  (23 cause nodes, 14 cause links, open questions and proposed solutions).
- `evidence_map_draft.json`: which sentences in E01–E16 bear on each chart node, plus
  designed traps such as passages that look relevant but settle nothing.
- `custodian_holdings.json`: which documents the simulated custodian holds and when it
  releases them.

`V3_Neurosymbolic_Inspired/scripts/score_against_truth.py` reports how many chart
nodes the board covers, whether the key sentences were assessed with a sensible
stance, and whether the traps were avoided. Node matching is by word overlap, so it
lists every match for you to check.

## Results so far

gpt-oss:20b on Ollama, 256 role jobs per run, fixed custodian, one run each. The
**context** column is the Ollama context window; "6k kept free" means 6,000 tokens
of it were reserved for the Specialist's reasoning and answer, with its prompt
trimmed to fit the rest.

| | Earlier fix | 16k, 6k kept free | 32k | 32k, low effort | 32k, medium effort |
|---|---|---|---|---|---|
| Key supporting sentences found | 3/14 | 5/14 | 5/14 | 2/14 | 3/14 |
| Key sentences assessed | 17 | 17 | 19 | 17 | 20 |
| Documents used | 14 | 14 | 16 | 14 | 15 |
| Overclaimed sentences | 5 | 5 | 2 | 1 | 3 |
| Claims on the board | 24 | 35 | 40 | 30 | 40 |
| Failed jobs | 14 | 4 | 13 | 3 | 14 |
| Cut-off answers | 41 | 0 | 0 | 0 | 0 |
| Run time | – | ~3¾ h | ~5⅓ h | ~1¾ h | ~4 h |

What this shows so far:

- Keeping room for the answer removed cut-off answers.
- A larger window let more documents reach the Specialist and cut overclaiming.
- Lower reasoning effort was faster but found less. High effort was too slow to finish
  (about 15 jobs an hour).
- **The board still rarely reaches the causes on the chart.** The Specialist only
  looks at documents through the claims already on the board, so evidence that fits
  no current claim never steers it. Directing it at one document at a time is being
  tested as the next step.

Caveats: each column is a single run, so differences of one or two may be noise.
The "supporting sentences" count is generous, because it credits a support on any
claim. Run outputs (50–110 MB each) are not in this repository.

## Repository layout

| Path | Contents |
|---|---|
| `V3_Neurosymbolic_Inspired/` | The current five-role system, its runners, scorers and tests. [Its README](V3_Neurosymbolic_Inspired/README.md) covers each role in detail. |
| `V1_V2_Prompt_and_Rules/` | Earlier versions kept for comparison: V1 is prompt-only, V2 adds research-inspired methods and rules. They share one codebase and are selected by profile (see [VERSION_GUIDE.md](V1_V2_Prompt_and_Rules/source/RCA_Version_Labeled_Codebase/VERSION_GUIDE.md)). The R3 documents live in its test fixtures. |
| `ground_truth/` | The human RCA chart, the evidence map and the custodian holdings. |
| `scripts/` | Launchers that run V1, V2 and V3 on the same case. |
| `tests_ollama/` | Tests for the Ollama client. |

## Setup

Tested with Python 3.13. Clingo is the only V3 dependency:

```bash
python -m pip install -r V3_Neurosymbolic_Inspired/requirements-sahs.txt
```

For local models, install [Ollama](https://ollama.com) and pull a model first, for
example `ollama pull gpt-oss:20b`. For hosted models, set `OPENROUTER_API_KEY` in your
shell. See `.env.example` in the V1/V2 codebase; never commit a real key.

## Run

All commands run from the repository root.

One closed-loop run on a local model:

```bash
python V3_Neurosymbolic_Inspired/scripts/run_v3_closed_loop.py \
  --provider ollama_native --model gpt-oss:20b \
  --num-ctx 32768 --answer-reserve 6000 \
  --max-jobs 256 --call-timeout 600 \
  --output outputs/r3_closed_loop.json
```

Several runs of one configuration, with the spread between them:

```bash
python V3_Neurosymbolic_Inspired/scripts/run_repeats.py \
  --provider ollama_native --model gpt-oss:20b --runs 3 \
  --num-ctx 32768 --answer-reserve 6000 \
  --output-prefix outputs/gptoss_32k
```

Score a run against the ground truth, and check its workflow health:

```bash
python V3_Neurosymbolic_Inspired/scripts/score_against_truth.py outputs/r3_closed_loop.json
python V3_Neurosymbolic_Inspired/scripts/score_run.py outputs/r3_closed_loop.json
```

Run the tests, which use scripted model replies and need no model:

```bash
cd V3_Neurosymbolic_Inspired
PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py'
```

`--help` on any script lists every option. To run V1, V2 and V3 on the same case,
use `scripts/run_r3_all_versions_live.py` (see [OLLAMA_ADAPTER.md](OLLAMA_ADAPTER.md)).

## Further reading

- [CLOSED_LOOP_RUNBOOK.md](CLOSED_LOOP_RUNBOOK.md): how a run works, its output, exit codes and failures.
- [FRAMEWORK_TASK_GOALS.md](FRAMEWORK_TASK_GOALS.md): the goals (grounded, honest, responsive, asks well, order-independent, comparable) and the tasks toward them.
- [FRAMEWORK_AUDIT.md](FRAMEWORK_AUDIT.md): the problems found in earlier runs.
- [RESEARCH_BRIEF.md](RESEARCH_BRIEF.md): related research for each problem.
- [OLLAMA_ADAPTER.md](OLLAMA_ADAPTER.md): the native Ollama client.
- `CHANGELOG_v0.2.md` to `CHANGELOG_v0.4.md`: version history.

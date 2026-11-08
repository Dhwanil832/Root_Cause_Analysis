# V3 Neurosymbolic-Inspired Pipeline

This directory contains the standalone V3 role packages and a runnable
Intake-to-Lead runtime. PIRIS registers and indexes each submission, the V3
runtime forwards versioned materials to CFERP, and CFERP routes work through
SAHS, EWV3, and HERA1. Outward request dispatch and human responses remain an
operator action.

| Role | Package |
|---|---|
| Lead | `cferp/` |
| Specialist | `sahs/` |
| Evidence Worker | `ewv3/` |
| Assessor | `hera1/` |
| Intake | `piris/` |

## Live OpenRouter run

Run from this directory after installing Clingo:

```bash
python -m pip install -r requirements-sahs.txt
export OPENROUTER_API_KEY="your-key-in-your-shell"
python scripts/run_v3_case.py \
  --case examples/r3_synthetic_case.json \
  --model nvidia/nemotron-3-ultra-550b-a55b:free \
  --include-later-materials \
  --output outputs/r3_openrouter_v3.json
```

The default pins a currently listed free model; `--model` can select another
OpenRouter model. Free endpoints are rate-limited, and `--max-jobs` caps role
jobs rather than individual model calls. The case example marks the R3 materials as
synthetic research fixtures. Its later material waves enter PIRIS as
unrequested uploads; the Lead and role pipeline then process the arrivals.
The runner saves the board, work, Intake events, and provider call records to
the output JSON. It does not auto-send outward questions.

The runner uses one OpenRouter model for PIRIS metadata suggestions, the
optional CFERP semantic helper, SAHS, EWV3, and HERA1. CFERP's hard rules,
version gates, queue, and branch decisions remain Python-owned. Free endpoints
may rate-limit or become unavailable, so the run stops on provider errors and
keeps the completed output only when the process reached report writing.

## Closed-loop synthetic R3 replay

`scripts/run_v3_closed_loop.py` adds the outward request/response leg missing from
the basic staged-material runner. It dispatches requests that passed Assessor
review, asks a constrained synthetic custodian to select only IDs from the
currently released fixture wave, sends selected documents back through PIRIS,
and resumes the normal Lead/Specialist/Evidence Worker/Assessor queue. Documents
not selected as replies arrive as ordinary unrequested uploads. At the end, a
bounded search may return a labeled “no matching fixture record” note; this is
not treated as proof that a record does not exist. The Lead still owns request
closure, and the runner does not declare the investigation complete.

Run with local Ollama:

```bash
python scripts/run_v3_closed_loop.py \
  --provider ollama_native --model <installed-model-tag> \
  --base-url http://localhost:11434 \
  --output outputs/r3_closed_loop.json
```

Or use OpenRouter by setting `OPENROUTER_API_KEY` and omitting `--provider`:

```bash
python scripts/run_v3_closed_loop.py \
  --model nvidia/nemotron-3-ultra-550b-a55b:free \
  --output outputs/r3_closed_loop.json
```

This is a full **workflow simulation of the supplied synthetic R3 fixture**;
it is not grounded in authenticated incident records, and the synthetic
custodian is not a human. The output records the simulated-response trace and
that no human was contacted. The package does not send real outward messages.

## Local Ollama run

The combined archive also provides a native Ollama adapter. From the combined archive root:

```bash
ollama pull <model-tag>
python V3_Neurosymbolic_Inspired/scripts/run_v3_case.py \
  --case V3_Neurosymbolic_Inspired/examples/r3_synthetic_case.json \
  --provider ollama_native \
  --model <model-tag> \
  --base-url http://localhost:11434 \
  --include-later-materials \
  --output outputs/r3_ollama_v3.json
```

Use the exact tag shown by `ollama list`. The adapter calls Ollama's native `/api/chat` endpoint and requests JSON output for structured role calls. See the combined archive's `OLLAMA_ADAPTER.md` for V1/V2/V3 launcher instructions and tests.

## Tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py' -v
```


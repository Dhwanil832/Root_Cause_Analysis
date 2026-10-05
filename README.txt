BENCHMARK HARNESS — THE SCORED FALLBACK

This is the exact repaired runtime used for the scored GPT-5.5 fallback and
the Qwen/Granite/Hermes/Mistral comparison. All 26 frozen runtime files are
unchanged. Only launcher and report paths were adjusted to make this folder
self-contained. The later translator and deterministic-mapping prototypes
are not part of this version.

Start here
----------
Open REPORT.html for the existing scored results, stage breakdowns, all 96
expected-versus-observed annotations per model, and original model answers.
MANIFEST.json identifies the source, version and packaging changes.

Verify the package without running a model:
    bash RUN.sh verify

Run one fresh connected R3 investigation with a selected recorded profile:
    bash RUN.sh qwen
    bash RUN.sh gptoss
    bash RUN.sh granite
    bash RUN.sh hermes
    bash RUN.sh mistral
    bash RUN.sh gpt

These commands make model calls. No new calls were made while packaging.
Each model has its own runs/MODEL directory. A failed or rejected existing
attempt is preserved; the launcher will not silently start a replacement.

Dependencies and configuration
------------------------------
Use Python 3.10 or later. The JSON R3 benchmark uses Python's standard library.
Optional PDF ingestion in the runtime requires pypdf.
Local runs require a running Ollama service at http://127.0.0.1:11434 with the
version and model digests recorded in settings.json and profiles.json.
Those checks intentionally reject silent model/backend substitution.
Granite and Hermes allow documented CPU offload at native 131k context;
the other recorded local profiles require full GPU placement.
GPT uses the unchanged Codex adapter, a saved ChatGPT login, and the Codex CLI.
That adapter retains its tested macOS /private/tmp path; this is not a new
Linux deployment package. No API keys or login credentials are included.

Contents
--------
runtime/          Exact frozen engine, controller, schemas, role prompts and UI.
benchmark/        Frozen R3 synthetic research package, clean inputs and rubric.
profiles.json     Recorded local-model settings, context sizes and digests.
run_local.py      Ollama launcher; writes new cases under runs/.
run_gpt.py        GPT-5.5 via Codex launcher; writes under runs/gpt/.
deliver.py        Submit a reviewed evidence-custodian response batch.
review/           Frozen score aggregation; requires manual semantic annotations.
scored-results/   Original scored states, model answers and 96-row reviews.
provenance/       Previous run plans, setup diagnostics and comparison record.
runs/             New investigations only; initially empty.

Evidence and scoring
--------------------
Initial model input contains D01, D02, D04 and D15. Follow the supplied
benchmark/R3-investigation-v1/custodian-policy.json for later documents at
genuine evidence pauses. Custodian matching remains supervised.
    python3 deliver.py MODEL /absolute/path/to/reviewed-batch.json

The private evaluator and expected answers are for scoring only, never model
inputs. They remain separated from public incident records in the package.
After reviewing a run against all 96 criteria and saving annotations.json
and stage-windows.json in that run folder, aggregate with:
    python3 score.py runs/MODEL

Scope of the saved scores
------------------------
GPT fallback: 82/96 expected-content presence, 81/96 consistent; partial board
with 12 nodes and 5 edges, including a known unsupported procedure-to-block-
absence causal connection. Qwen: 17/96. Granite: 3/96. Hermes: 3/96.
Mistral: 2/96. These four local-model runs committed no board and left 74
checks unreached. Raw expected content can earn credit even when the batch
is rejected. Unreached reasoning is not an observed wrong answer.
These are single unblinded reviews, not proof of general RCA reliability.

The README inside runtime/prototype is an unchanged historical file and
mentions tools from the larger research workspace. Use this top-level README
and RUN.sh as the entry points for this packaged snapshot.

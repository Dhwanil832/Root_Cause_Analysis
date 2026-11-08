# Native Ollama adapter

This adapter lets the combined V1/V2/V3 archive use models already installed in a local Ollama server. It implements the shared `ask(task, system, payload) -> dict` port using Python's standard library; it adds no Python package dependency.

## Quick start: all three versions

1. Install and start Ollama using its official instructions.
2. Pull a model that fits the machine and the workload: `ollama pull <model-tag>`.
3. Confirm the exact tag with `ollama list`.
4. From the combined archive root, run:

```bash
python scripts/run_r3_all_versions_live.py \
  --provider ollama_native \
  --model <exact-local-tag> \
  --base-url http://localhost:11434 \
  --check-only

python scripts/run_r3_all_versions_live.py \
  --provider ollama_native \
  --model <exact-local-tag> \
  --base-url http://localhost:11434 \
  --output outputs/r3_ollama
```

The combined preflight checks that Clingo is installed, the fixture files exist, the Ollama server responds to `/api/tags`, and the exact model tag is installed. No API key is needed. To use a server on another machine or port, pass its host origin with `--base-url`.

The full V3 pipeline can be run independently:

```bash
python V3_Neurosymbolic_Inspired/scripts/run_v3_case.py \
  --case V3_Neurosymbolic_Inspired/examples/r3_synthetic_case.json \
  --provider ollama_native \
  --model <exact-local-tag> \
  --base-url http://localhost:11434 \
  --include-later-materials \
  --output outputs/r3_ollama_v3.json
```

V1/V2 alone can be run with the corresponding options to `scripts/run_r3_v1_v2_live.py`.

## Direct Python use

Add `V1_V2_Prompt_and_Rules/source/RCA_Version_Labeled_Codebase` to `PYTHONPATH`, then:

```python
from shared.llm.ollama_client import OllamaChatModel

model = OllamaChatModel(
    model="<exact-local-tag>",
    base_url="http://localhost:11434",
    timeout=300,
    retries=1,
)
model.check_model()
result = model.ask("example_task", "Return one JSON object.", {"input": "..."})
```

`shared.llm.factory.create_model_client(provider="ollama_native", ...)` constructs the same adapter. V1/V2 model construction, V3 archive configuration, and the standalone V3 runtime use this factory when `provider` is `ollama_native`.

## Request and failure behavior

- Uses Ollama's native `POST /api/chat` endpoint, with `stream: false`, system/user messages, JSON response mode, and configurable temperature.
- Uses `GET /api/tags` for local model discovery. Model selection must exactly match an installed tag.
- Parses only a JSON object for the research package's structured model port. On malformed JSON or transient request failures, it retries only up to the configured bound; it does not replace a failed model call with scripted answers.
- Records model name, provider label, latency, token counts, and Ollama timing fields in the existing call record. It does not record secrets.
- The provider makes direct HTTP calls to the configured Ollama host. The archive's existing `provider: ollama` option remains the OpenAI-compatible `/v1/chat/completions` route; `ollama_native` selects this native adapter.
- A successful JSON response is not a quality or safety certification. Local model size, available VRAM/RAM, quantization, context length, and generation speed vary by machine and model.

## Test the adapter

From the combined archive root:

```bash
PYTHONPATH="V1_V2_Prompt_and_Rules/source/RCA_Version_Labeled_Codebase" \
  python -m unittest discover -s tests_ollama -v
```

These tests use a local mock HTTP server. They verify native request formatting, model discovery, usage capture, a bounded JSON-format retry, and missing-model errors without requiring a running Ollama service.

## Official API references

- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama local model tags API](https://docs.ollama.com/api/tags)

# RCA Harness

Local dashboard for comparing LLM performance under the same RCA methodology, seeded facts, queue rules, and causal-board controls.

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

The default provider is local Ollama at `http://localhost:11434/v1`. Enter an Ollama model name in the dashboard, for example `qwen3.5` or `qwen3:8b`. When you run the harness, a missing Ollama model is downloaded locally before the run begins.

For an API provider, add its OpenAI-compatible `/v1` base URL in the dashboard and provide the name of an environment variable that holds its key. For example:

```bash
export OPENAI_API_KEY="..."
```

The key is read only on the server. It is not persisted in SQLite or sent to the browser.

## Current v1 scope

The database is seeded with the Indiana Harbor R3 Exit Carrier Beam neutral incident and ten verified fact rows. The harness uses the selected model for sections 2.1, 3A, 5.1, 5.2, 5.5, 5.6, 5.7, and 6.1–6.3. Board/queue state, referees, the prevent/interruption decision, and causal graph integrity are code-owned.

Document parsing, fact extraction, document requests, new-record update loops, edit learning, formal evaluation rubrics, and multi-model-per-role routing are intentionally deferred.

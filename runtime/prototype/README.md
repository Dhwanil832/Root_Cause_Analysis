# Supervised RCA prototype — repaired contract

The current harness uses runtime contract `2026-10-04-dependency-repair-2`. It retains the hypothesis → evidence → assessment → lead review → upstream investigation design. GPT and Qwen share the engine, prompts, schema and controller.

The [repair record](audits/REPAIRS_2026-10-02.md) maps all 19 audit findings to implementation and checks. The [current contract](CONTRACT.md) describes behavior. Existing R3 results and frozen snapshots describe the earlier harness and remain unchanged.

The October 4 repair separates request bookkeeping from physical proof dependencies, schedules stale-record reassessment before stopping, and defers closure when a valid update makes its explanation stale. It also preserves proposal review after duplicate jobs are skipped. Exact saved R3 failure inputs and responses are retained in `tests/fixtures/dependency-repair`; offline replay exercises the unchanged model answers under the repaired mechanics. This is not a new model run or a causal-accuracy score. Repair evidence is saved under `audits/dependency-repair-2026-10-04`.

## Offline verification

```sh
python3 verify_repairs.py
```

This runs populated operation, lifecycle, recovery, diagnostic, UI-policy and localhost HTTP regression tests. It makes no model calls. The HTTP tests need permission to bind a temporary loopback port; Node is used for the pure UI-policy checks. Passing these checks does not certify causal reasoning or live model compatibility.

`verify_qualification.py` verifies the old execution lock and will correctly fail the current-source comparison after these changes. Its stored model probes are not new qualification. Historical `qualify_runtime.py`, `qualify_native.py`, and `audit_token_capacity.py` no longer execute live probes through their CLI under this changed runtime. The old comparison launcher remains guarded by its frozen qualification; do not bypass the guard to mix versions.

## Create and inspect a new case

```sh
python3 harness.py init cases/my-new-incident --provider gpt --description 'Observed event and investigation objective' --document /absolute/path/initial-record.json
python3 harness.py serve cases/my-new-incident --port 8765
python3 harness.py status cases/my-new-incident
```

Open http://127.0.0.1:8765. The inbox separates user questions, internal work and retained request history. The graph labels stale and human-rejected findings. Rejected model prose is separate from the accepted investigation report. Submission of text and a document is atomic. Submit/review after the current run pauses; its lock lasts for the entire invocation.

The following command makes model calls; it was **not** run as part of the repair:

```sh
python3 harness.py run cases/my-new-incident
```

There is no default call-count cap. `--max-calls N` is an optional operator checkpoint, not causal closure. Native provider profiles remain unchanged: Qwen uses the pinned Ollama/model with 262,144 context, `num_predict=-1`, no shift/truncation; GPT uses its pinned snapshot, medium reasoning and 128,000 output maximum. Neither has a client generation deadline. Native capacity failures remain separate from reasoning scores.

## Submit and correct evidence

```sh
python3 harness.py submit cases/my-new-incident --request REQUEST_ID --answer 'A scoped answer or availability statement'
python3 harness.py submit cases/my-new-incident --request REQUEST_ID --document /absolute/path/record.pdf
python3 harness.py submit cases/my-new-incident --document /absolute/path/corrected.json --corrects SOURCE_ID
```

Omit `--request` for unsolicited evidence. Correction preserves request links and source identity, increments its version, and reopens dependent assessment. Receipt alone does not mark a request answered or a cause proved. Coverage explanations and reviewer notes persist in later agent inputs.

## Inspect and recover a failed attempt

```sh
python3 harness.py inspect-failure cases/my-new-incident
python3 harness.py retry-failed cases/my-new-incident --reason 'Explain the inspected problem and why a fresh attempt is justified'
python3 harness.py run cases/my-new-incident
```

The retry command only schedules work; it does not call a model. Original attempt files and errors remain intact, and the new attempt has a new directory. A completed saved answer must instead recover with `run`; it cannot be resampled using retry. A rejected lead batch without a pending transport failure already has a repair assignment queued; inspect its detailed feedback and resume deliberately.

`reapply-last` remains an exact saved-response structural tool for a same-runtime, unchanged-input rejected lead batch. It is not an answer editor or a means of reinterpreting a wrong causal judgment. New code/prompt fingerprints require a new case, so earlier experiments cannot be silently continued under changed rules.

## Scope and credentials

The API key is read server-side from `../.env.local` or `OPENAI_API_KEY`; credentials are excluded/redacted from diagnostic messages. The evidence inbox binds only to loopback and checks Host/Origin. It is not a multi-user production service.

Uploads accept JSON, text, Markdown and text-based PDF. PDF requires `pypdf`, available in the bundled Python at `/Users/dhwanilchauhan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`. Scanned OCR and live internet reference search are not implemented. Lexical retrieval returns full matched documents and explicitly reports its limitations.

The engine contains no expected R3 answers or gold graph. Structural acceptance does not validate causal reasoning. Future experiments must freeze this repaired version and use it consistently across compared models; previous results remain previous-version results.

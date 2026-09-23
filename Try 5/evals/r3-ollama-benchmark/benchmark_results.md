# R3 carrier-beam Ollama benchmark results

Date completed: September 8, 2026

## Outcome

Qwen 3.5 was the strongest investigative model in this test, but no tested local model produced a mature, evidence-complete RCA that should be accepted without expert review. The main failure mode was not lack of words; it was failure to transform available records into a defensible causal structure with explicit failed barriers, competing hypotheses, source-quality conflicts, and system-level corrective actions.

DeepSeek R1 and Granite 3.3 failed the operational gate: each exhausted the 30-minute ceiling and committed no analysis version. Qwen 2.5 completed only 18 seconds before that ceiling. Llama 3.1 was the cleanest structured-output run, but its analysis was too shallow.

## Ranking and score

The analytical score follows the predeclared 100-point rubric. Runtime is shown separately and is not silently folded into the analytical score; a no-version timeout receives zero because there is no usable artifact to grade.

| Rank | Model | Incident comprehension /10 | Tags /10 | Questions /15 | Evidence targeting /15 | Provenance and contradictions /15 | Causal reasoning /20 | Actions /10 | Calibration and trace /5 | Total /100 | Operational result |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | qwen3.5:latest | 9 | 8 | 13 | 13 | 4 | 6 | 7 | 4 | **64** | Initial pass committed in 21m 8s; evidence update timed out after 30m and committed no v2 |
| 2 | qwen2.5:7b | 6 | 7 | 7 | 6 | 2 | 4 | 4 | 2 | **38** | Committed in 29m 42s; 6 stage errors |
| 3 | gemma3:4b | 7 | 3 | 6 | 6 | 1 | 4 | 3 | 1 | **31** | Committed in 15m 10s; 4 stage errors |
| 4 | mistral:7b | 7 | 6 | 4 | 3 | 1 | 4 | 2 | 2 | **29** | Committed in 12m 52s; 2 stage errors |
| 5 | llama3.1:latest | 6 | 2 | 3 | 5 | 3 | 4 | 0 | 4 | **27** | Committed in 7m 21s; 0 stage errors |
| 6 | hermes3:8b | 6 | 1 | 0 | 2 | 1 | 5 | 1 | 2 | **18** | Committed in 17m 45s; 2 stage errors |
| 7 | llama3.2:3b | 5 | 1 | 2 | 3 | 1 | 3 | 0 | 2 | **17** | Two versions in 7m 5s total; 0 errors in scored v2 |
| 8 | phi4-mini-reasoning:3.8b | 5 | 0 | 3 | 2 | 1 | 2 | 0 | 0 | **13** | Committed in 25m 36s; 19 stage errors and extensive fallback output |
| 9= | deepseek-r1:7b | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | Timed out at 30m; incident shell only, no version committed |
| 9= | granite3.3:8b | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | Timed out at 30m; incident shell only, no version committed |

## Reproducibility snapshot

| Model | Scored version | Tags | Baseline + investigation questions | Evidence claims | Conflicts | Causal nodes / edges | Actions | Stage errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5:latest | 1 | 8 | 1 + 5 | 15 | 0 | 1 / 0 | 4 | 1 |
| qwen2.5:7b | 1 | 7 | 3 + 18 | 47 | 0 | 7 / 6 | 6 | 6 |
| gemma3:4b | 1 | 5 | 3 + 9 | 44 | 0 | 4 / 2 | 1 | 4 |
| mistral:7b | 1 | 4 | 3 + 3 | 17 | 0 | 4 / 2 | 5 | 2 |
| llama3.1:latest | 1 | 1 | 4 + 3 | 11 | 0 | 5 / 5 | 0 | 0 |
| hermes3:8b | 1 | 13 | 4 + 1 | 10 | 0 | 4 / 3 | 1 | 2 |
| llama3.2:3b | 2 | 2 | 3 + 5 | 16 | 0 | 4 / 3 | 0 | 0 |
| phi4-mini-reasoning:3.8b | 1 | 13 | 3 + 40 | 64 | 0 | 4 / 2 | 0 | 19 |
| deepseek-r1:7b | none | - | - | - | - | - | - | - |
| granite3.3:8b | none | - | - | - | - | - | - | - |

Counts are diagnostic only. For example, Phi produced 40 investigation questions because fallback tagging activated every specialist, while Qwen 3.5 produced five focused questions that were substantially more useful.

## Model-by-model findings

### 1. Qwen 3.5 — 64/100

Best performance: it correctly framed the falling carrier-beam event, potential fatal exposure, changed outage configuration, raised roll balance, hydraulic isolation, and the distinction between an installed keeper and an unknown positive-retention function. Its tag set was broad but mostly relevant. Its five investigation questions targeted the most important branches: permitted raised configuration, the release mechanism, ECP/LOTO execution, temporary supports, and the retention design. Evidence requests were specific—equipment procedures, drawings, execution records, photographs/video, measurements, and post-event inspection.

Its verification findings were also useful: they explicitly said the root cause was incomplete and named the evidence required to decide among equipment failure, procedural support gaps, and external triggers. The four proposed actions had owners, completion evidence, and effectiveness checks.

Why it did not score higher: the causal board contained only the focal event and no causal edges. The evidence-processing stage failed JSON validation. Most importantly, the evidence-rich update timed out and committed no second version, so it never demonstrated that it could reconcile the superseded R2 drawing, anonymous keeper note, or crane-rumor email against higher-authority records. Its crane tag was somewhat over-broad because no active lift occurred.

Artifact: `qwen3.5_latest/version-1.json`; incident `f88a2a93-0fbe-4a9d-b1a4-01276b6345da`.

### 2. Qwen 2.5 — 38/100

Best performance: it selected seven generally relevant tags and generated several useful lines about the changed configuration, turnover, hold points, isolation boundary, restraints, and inspection/restoration requirements. It created 47 evidence claims and six actions with nominal owners and completion evidence.

Major weaknesses: many questions repeated baseline prompts, the evidence fetcher claimed that shift/turnover and hold-point details were absent even though the consolidated packet contained them, and no seeded conflict was detected. The board was event-only. Several arrows ran outward from the falling event to pre-event facts, reversing causal direction. Actions such as verifying that nobody was in the pit and evaluating whether the red-flag investigation was needed consumed attention without controlling the failure mechanism. Six stages failed schema or JSON validation.

Artifact: `qwen2.5_7b/version-1.json`; incident `040ce40f-827c-4c77-ad63-199c03477f49`.

### 3. Gemma 3 4B — 31/100

Best performance: its incident summary, focal event, exposure consequence, and three baseline questions were sensible. It requested drawings, isolation records, mechanical condition evidence, and procedure information.

Major weaknesses: it tagged rail and electrical without evidence and omitted central stored-energy, outage, and isolation tags. It repeatedly converted unknown statements into “questions,” duplicated them, and claimed both that the raised condition was permitted and that permission was unclear. That unsupported assertion is a serious calibration problem. It found none of the planted conflicts. Evidence-processing and causal-analysis failures left a generic fallback board and only one investigative action rather than a verified corrective action.

Artifact: `gemma3_4b/version-1.json`; incident `27f962c2-4b36-4c17-bc72-46900cd329f5`.

### 4. Mistral 7B — 29/100

Best performance: it recognized gravity energy, work environment, planning, and communication, and its incident comprehension was sound. Its three questions at least asked for physical sequence and causal evidence.

Major weaknesses: it missed equipment, maintenance/outage, and isolation/LOTO as central tags. Both evidence processing and causal analysis produced malformed JSON, leaving a generic four-node board. It detected no conflicts. The proposed instruction to “implement crane lifting procedures” was unsupported because the stronger records said no event-time crane lift or motion occurred.

Artifact: `mistral_7b/version-1.json`; incident `df13efbb-fb3d-49b0-95ef-dee48c6b4cc0`.

### 5. Llama 3.1 — 27/100

Best performance: it was the fastest evidence-complete 7–8B run and the only such run with zero stage errors. It preserved several source IDs and correctly kept the exact transition mechanism open.

Major weaknesses: it selected only the equipment tag, produced two unknown statements plus one real question, and built five generic event nodes with empty causal rationales. It retrieved relevant documents but often said the information was insufficient despite applicable records being present. It detected no conflicts and proposed no actions. Structurally valid output is not enough when the causal analysis is nearly empty.

Artifact: `llama3.1_latest/version-1.json`; incident `a49acc22-78df-494c-900d-7bbec2dfdbbb`.

### 6. Hermes 3 — 18/100

Best performance: its board at least placed roll removal, the raised balance, hydraulic isolation, and the fall into a recognizable sequence.

Major weaknesses: tagging validation failed, so fallback keyword logic activated all 13 tags, including electrical, vehicles, process material, and rail. Its only investigation “question” was an internal question ID, not user-readable text. It found no conflicts. Its sole action—verify hydraulic pressure before roll removal—did not match the supplied planned sequence and did not address positive mechanical support before pressure removal.

Artifact: `hermes3_8b/version-1.json`; incident `9d9ca2ba-afc9-44c5-aec4-0ac4366eecd7`.

### 7. Llama 3.2 3B — 17/100

Best performance: it completed two versions quickly and without schema errors. The second version retained the focal event, raised balance, and hydraulic isolation facts.

Major weaknesses: it selected a rail tag, dropped relevant tags to zero confidence, repeated “Was there any crane interaction?” five times, mismatched a support-state answer to that crane question, typed every causal node as a human decision/action, and drew causal arrows from the fall toward pre-event conditions. The focused parent answer did not produce a useful recovery. It detected no conflicts and proposed no actions.

Artifact: `llama3.2_3b/version-2.json`; incident `43ed12a1-285d-4393-9c32-817c4da1adc4`.

### 8. Phi-4 Mini Reasoning — 13/100

Best performance: the fallback incident summary preserved the main event and changed outage condition, and the large fallback question pool happened to include some relevant topics.

Major weaknesses: 19 stages failed, most with Ollama 400 responses. Fallback tagging activated every specialist and generated 40 largely irrelevant investigation questions, including electrical, vehicles, process materials, and rail. The board was generic, no conflicts were found, and no actions were produced. This model/adapter combination is not compatible with the current structured pipeline.

Artifact: `phi4-mini-reasoning_3.8b/version-1.json`; incident `69078b70-90fe-4595-8452-3f84d5e7a2e7`.

### 9=. DeepSeek R1 7B and Granite 3.3 8B — 0/100

Each model ran alone for the full 1,800-second ceiling. The app created an incident and model track, but direct database and API checks confirmed zero version rows. There is no model-produced RCA artifact to grade.

DeepSeek incident: `e317f2c9-34e2-4ecc-928f-9ad3f2a76658`. Granite incident: `ca7418f5-f2c8-4ffd-8c76-00467f133d14`.

## Cross-model conclusions

1. **Qwen 3.5 is the best candidate for the next harness iteration**, especially for incident understanding, tag selection, opening questions, evidence requests, and verification findings. It is not ready to own the causal board without further work.
2. **Llama 3.1 is the best structured-output baseline.** Its zero-error run makes it useful for adapter and prompt regression tests, but its RCA depth must improve substantially.
3. **The current causal-analysis stage is the system bottleneck.** Even when evidence retrieval produced useful facts, models frequently emitted chronology, repeated the event, reversed edge direction, or fell back to generic nodes.
4. **Conflict handling did not work in any scored output.** Every model reported zero conflicts despite three deliberately labeled challenge records. This is a system-level test failure, not a subtle scoring distinction.
5. **Keyword fallback tagging is too permissive.** When a model failed schema validation, references inside the evidence packet triggered unrelated tags such as electrical, vehicles, process material, and rail.
6. **A “corrective action” should not be generated from an unverified causal branch.** Several models converted evidence requests into corrective actions or proposed controls for unsupported crane involvement.
7. **Latency is too high for the intended interactive loop.** The strongest model's first pass took over 21 minutes and its evidence update failed after another 30. Qwen 2.5 took nearly 30 minutes. A production harness needs stage budgets, cancellation, checkpoint commits, and selective model routing.

## Harness findings discovered during the benchmark

Two implementation defects were corrected before the comparable later runs:

- PDF extraction could detach the uploaded byte buffer before hashing/storage. The repository now preserves a cloned byte array before extraction, so the original file and SHA remain intact.
- Ollama specialist and answer-fetching “batches” previously created all promises before batching, causing unintended parallel requests. They now use deferred tasks, and Ollama runs those stages with concurrency 1.

A third presentation defect was corrected after the benchmark: history previously displayed `V1` for a timed-out track with no version because of a fallback value. Empty tracks now report `No completed version`, while successful runs retain their actual version number.

These fixes improve the validity of later runs. The pre-fix Qwen diagnostic is preserved in `qwen3.5_latest/diagnostic-unbounded-concurrency.json` but is excluded from scoring.

## Recommended next experiment

Use Qwen 3.5 only for incident understanding, tagging, specialist question generation, and evidence-request drafting. Use Llama 3.1 as the schema-reliability comparison. Before rerunning the full benchmark:

1. Add a dedicated evidence adjudication stage that must classify every source by authority, applicability, revision, directness, and corroboration before creating claims.
2. Require explicit conflict checks against the three challenge patterns and fail the stage if a challenge source is silently ignored or accepted as fact.
3. Constrain causal output to forward links: condition/change -> mechanism -> barrier failure -> focal event -> consequence, with an evidence citation and counterfactual test on every causal edge.
4. Separate investigation tasks from corrective actions; corrective actions should be allowed only for supported or explicitly provisional causal targets.
5. Commit checkpoints after each stage so a long final-stage failure does not erase an otherwise usable run.
6. Add per-stage time/token budgets and route only the difficult synthesis stages to the strongest model.

No internet evidence was added during this benchmark. The synthetic and partner-provided records were sufficient for the intended branches, while the missing OEM geometry/tolerances are proprietary case evidence that public web sources could not authoritatively replace.

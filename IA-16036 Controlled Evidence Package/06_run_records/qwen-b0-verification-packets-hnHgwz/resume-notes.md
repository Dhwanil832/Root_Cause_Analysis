# B0 verification continuation — completed V1

Completed: **2026-09-16 21:02:26 UTC**. This is an explicitly resumed copy of `qwen-b0-local-rejections-etH9Rd`, not a fresh independent model evaluation.

## Repair and scope

The prior run stopped at verification packet 11: 64,421 characters against a 60,000-character guard. Exact reconstruction reproduced all ten previously completed verification inputs and the oversized packet. Claim records occupied 54,430 characters, but the old splitter bounded only source excerpts.

Release `try4.3.3-complete-verification-packets` measures the entire serialized packet and partitions only oversized context collections. It does not truncate records, remove review targets, raise the guard, or change the prompts, output schema, model, original evidence or causal generation. All original records remain represented. Positive support on one partition cannot override a failed check on another.

Only packet 11 changed: its 28 claims became two groups of 14. Both partitions kept the same four source excerpts and all three review targets. Their actual model inputs were 33,920 and 41,283 characters. The full verification plan became 25 calls instead of 24; the largest planned packet was 55,282 characters.

## Confirmed outcome

- **Exactly one V1 committed.** Runner exit code 0; status `completed_stopped_after_v1`.
- **75 calls reused**, including all ten completed verification calls. The original model-call cache also contains two obsolete claim-review calls that were not reused.
- **15 new verification calls**, each successful on its first attempt.
- All **72 distinct targets** reviewed across 25 verification calls. The split packet reviews three targets twice; these are conservatively combined, not counted as new targets.
- **No stage errors or new execution failures.**
- Board preserved: **40 nodes, 32 retained connections, 48 separately rejected connection proposals**.
- Model verification accepted **8 nodes and 0 connections**. These are model assessments, not human confirmation. Some accepted nodes are duplicates; these are not eight distinct established causal findings.
- **112 review findings** remain, including the 48 rejected proposals. These are review records, not 112 separate root causes.
- Investigation state: **awaiting-evidence**; board maturity: **developing**. No corrective actions were generated.
- All **137 frozen source-file hashes** still match the manifest at completion. Previous frozen runs were not edited.

## What this does and does not establish

The packet-size execution failure is fixed for this real saved case, and the complete pass can now be inspected without restarting successful work. Compilation, local application build and inspection of the actual saved B0 packet plan passed; no preflight suite or new-model rehearsal was run.

This is not proof of a good RCA, a known root cause, or general correctness on arbitrary inputs. Unsupported proposals and duplicated nodes remain visible for substantive review. The initial B0 evidence does not establish the interruption mechanism; no later evidence batch, evaluator oracle, story answers, human approval or automatic follow-up run was introduced.

The runner has stopped. Only the local app server remains available for inspection.

## Preserved result

- `result.json`: completion and reuse counts.
- `version-1.json`: committed analysis snapshot.
- `after-resume.json`: full case state and durable checkpoints, including raw model requests/responses.
- `manifest.json`: exact frozen release, model and experiment lineage.

Dashboard: http://127.0.0.1:3006/incident/b7c62bf9-604c-4312-9520-7b63b20b7363

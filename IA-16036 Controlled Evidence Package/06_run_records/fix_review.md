# IA-16036 — delivery, transport, and controlled-run diagnosis

## Outcome

The deterministic delivery and transport defects are fixed in Try 4. Model interpretation is **not** established as fixed. There is **no newly committed app V1** from these attempts.

Current implementation/prompt version: `try4.2.5-lossless-claim-refs`.

## Preserved attempts

| Record | What ran | Outcome |
| --- | --- | --- |
| `qwen-b0-BcfExO` | Original B0 attempt; seven model responses | Client disconnected near five minutes; no V1. Kept unchanged. |
| `qwen-b0-LzLLom` | Fresh isolated app, same sealed B0 and Qwen digest; 38 model requests/responses | Completed through evidence processing. Stopped before causal analysis at a new 60,000-character application limit. No V1 and no whole-cycle retry. |
| `qwen-b0-causal-check-VNATDq` | Separate causal-analysis/verification diagnostic using the saved upstream outputs and corrected packet packaging | Stopped after the two allowed causal attempts: first exceeded output budget; second produced a dangling edge reference. Verification was not called. No app version written. |

The second run took approximately 28 minutes 51 seconds from first model request to last response. One tagging output reached its token budget; its single permitted repair succeeded. There were no proxy errors. All 124 frozen app files and seven input records retained their recorded hashes. The 263-check original evidence-package seal was unchanged before launch.

## Fixes and checks

1. **Document coverage:** replaced first-900-character representative excerpts and first-1,200-character previews with complete, contiguous source segments. Document tails and repeated source markers no longer disappear. Source identities are document-scoped; offsets preserve exact text coverage.
2. **Evidence routing:** tagging, specialists, causal analysis, and verification receive underlying source evidence rather than relying only on intermediate summaries. All six B0 documents—7,263 extracted characters—were delivered completely in each of the 11 captured full-evidence requests that the second run reached. Question-specific retrieval searches every segment and may then select relevant chunks.
3. **Transport:** the local experimental client uses an explicit deadline instead of Node fetch's implicit five-minute headers deadline. A real 310-second delayed-response test completed with exactly one POST and no retry. The live second run also remained connected beyond five minutes.
4. **Reasoning instructions:** distinguish preparation, release, execution, and restoration; assigned role versus physical presence; blank field versus actual absence; and a suspected gap versus a supported violation. Summaries must preserve the same uncertainty as findings.
5. **Packet size:** the first coverage fix introduced a limit that was too restrictive for the expanded causal packet. I preserved that failed attempt rather than changing its frozen settings. The correction replaces exact repeated claim copies and question-field text with resolvable references. The pre-causal packet reconstructed from completed checkpoints matches the recorded 66,798-character size. It becomes 59,612 characters; exact round-trip reconstruction, unchanged evidence text/claims, and the unchanged size guard all pass. No question, qualifier, or source was deleted to fit.

Verification: **58 app regression tests plus 5 transport tests passed**, including the long-delay test; TypeScript and targeted lint passed. The local socket-binding fixture suite required execution outside the sandbox after Node crashed there before its assertions. No live storyteller was invoked by those fixture tests.

## Precise model observations before causal analysis

These are model-output findings, not conclusions about the real historical incident. All case documents are the sealed synthetic reconstruction.

| Observation | Exact evidence and output | Assessment |
| --- | --- | --- |
| Better work-stage distinction | Understanding says the interruption occurred “during boundary preparation before maintenance release.” The procedure specialist no longer calls this unauthorized downstream work. | Improvement on the original error; not a complete reasoning pass. |
| Better entity/timeline extraction | Structuring returns 20 entities and 9 timeline entries, versus one each in the interrupted attempt. M-A is described as assigned, not necessarily present. | More useful extraction, but count alone is not correctness. |
| Requirement logic is still wrong | IA-D03 §3.6 permits an affected ECP to be revised and issued **or** an approved temporary instruction to be attached. Procedure response `0007` instead states that an approved temporary instruction is required when the ECP is affected. Answer response `0027` repeats that reading. | Unsupported narrowing of an alternative requirement; not a delivery failure. |
| Invented pressure-location join | Answer response `0032` says normal pressure was observed upstream/North gallery and labels a claim `verified`. IA-S01's 08:10 normal-band entry is from **RHOB**, before its later low indication; B0 supplies no upstream pressure reading. | Clear reasoning error. The complete source was available. Whether later causal stages catch it must be checked explicitly. |
| Lesser extraction errors | Structuring invents “Revision 1” for the work-package cover and changes a request to retain records into records having been retained. | Qualifiers and record identity remain imperfect. |

The broker reduced 25 candidates to 19 questions, preserving six coverage decisions. The answer fetchers returned eight partial answers and eleven not-found answers; none was fully answered. Partial/not-found status did **not** prevent individual overclaims inside those responses.

## Standalone causal-check result

The corrected wire packet reached Qwen. First attempt: 18,384 reported input tokens and 6,400 output tokens; generation stopped at its output budget after approximately 269 seconds. The same-stage repair returned complete JSON in approximately 161 seconds, using 18,436 input tokens and 3,637 output tokens.

The repair's edge `interruption-origin -> focalEvent` is invalid: the explicit focal object is materialized under the reserved key `focal`, and no node key `focalEvent` exists. Other declared keys included `boundary-prep-state`, `temp-instruction-status`, `valve-states`, `upstream-pressure-status`, `change-disposition`, `supervision-action`, `interruption-origin`, and `barrier-missing`.

The production validator rejected this relationship. No endpoint was silently renamed; no partial JSON was salvaged into a board; no further repair or whole-cycle retry was launched. The diagnostic ended with two model calls and no verification call. Its source hashes remained unchanged during execution. The final package validation again passed all 263 checks with the seal matched.

This confirms that the corrected causal input can be delivered; it does **not** demonstrate a valid final board or end-to-end app success. The remaining structural failure is graph-reference generation. Any decision to bind aliases automatically or split node and edge generation changes the harness contract and should be made explicitly, preserving the model's raw failure for evaluation.

## Limits and interpretation

- The full app attempt did not reach a board, so this is not a completed V1 benchmark and no final score out of 100 is assigned.
- The separate diagnostic reuses model-generated upstream outputs, including their mistakes. It does not regenerate or silently correct them, release B1–B3, invoke a storyteller, or claim to be an app commit.
- The 60,000-character guard is an application bound, not an exact tokenizer guarantee. Large-document batching is not implemented; adjudication inputs above 32 segments also stop explicitly. Silent truncation is removed, but arbitrary-size document support is not claimed.
- Prompt reinforcement does not guarantee factual correctness. The next substantive acceptance check is whether the causal board and verifier reject the specific unsupported claims above.

## Artifacts

- [Stopped app attempt](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-LzLLom/failure.json>)
- [Captured document-delivery audit](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-LzLLom/document-delivery-audit.json>)
- [Capture counts and integrity checks](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-LzLLom/capture-summary.json>)
- [Standalone diagnostic manifest](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-causal-check-VNATDq/manifest.json>)
- [Exact remaining causal failure](</Users/dhwanilchauhan/Desktop/RCA Try 1/IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-causal-check-VNATDq/failure.json>)

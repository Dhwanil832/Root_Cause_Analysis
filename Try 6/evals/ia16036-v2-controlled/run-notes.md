# IA-16036 controlled story batch and V2

## Identity and fixed expectations

- Incident `9660f4f2-5fc0-4d0a-917e-8e48641956e3`
- Track `a6647fe7-b418-4232-817f-b3c6d3a5325d`
- V1 `a20904da-8710-40df-8d58-fec78f451f2a`
- Story round `c5bdbc70-37bd-42f3-9acc-00912637f096`
- V2 `3d44374c-888e-465a-8870-99d11eaa8c12`, queued 2026-09-20 18:44:58 UTC
- Same `ollama:qwen3.5:latest` digest and 262,144-token native context.

Expectations were saved in `../ia16036-v2-expectations.md` before story generation.
Their hash, source hashes, V1 snapshot, fixed scenario and selected actual V1
questions are preserved in this directory. No later answer key or rubric entered
either model's context. B3, P06 and C02 are still withheld.

## Story result — operation succeeded, evidence use did not fully pass

Two isolated questions ran once each, sequentially, with background story execution
disabled. Explicit round-scoped steps completed in 24.895 and 22.986 seconds.
The stored inference profiles are non-thinking Qwen instruct (temperature 0.7,
top-p 0.8, top-k 20, presence penalty 1.5, repetition penalty 1, seed 42).

| Request | Observed behavior | Release decision |
| --- | --- | --- |
| Work-briefing/checklist content | Cites S02/S03, retains blank-field and missing-content limitations. Calls its answer `answered`, although requested content was not obtained. | Release unchanged with limitations; record status-calibration weakness. |
| Piping configuration/point mapping | Cites D01/P02 and says connectivity is unestablished. Ignores the P04 connection schedule in its actual input. | Withhold this answer; preserve it unchanged for evaluation. |

The piping call's stored passage catalog included P04 and P05; its context was
25,255 planned bytes / 6,312 reported input tokens. Neither context exclusion nor
missing retrieval explains this particular omission. The generated status was
`answered` despite the answer's blanket uncertainty. Its quotations are exact,
but that alone does not establish substantive answer quality.

No story retry, manual answer rewrite, replacement model, or invented field fact
was used. Both raw candidates remain preserved. Released story memory includes
only the approved answer; the withheld response cannot become a later factual
memory through the applied-round mechanism.

## Exact V2 input

One reviewed, unchanged story answer and two complete, preselected original records
were applied together through the app to create one V2. There were no separate
upload-triggered V2/V3/V4 revisions.

| Record | Preserved document ID | SHA-256 |
| --- | --- | --- |
| IA-P04 | `56772c5b-f8bd-496e-8338-4d80f54a3f4e` | `0ecc13b73d0f5ccd354519a538d40aed59ed9620c25331bf4a1f908089ff306c` |
| IA-P05 | `34bca70a-aa05-4ed9-b902-22de342fc27d` | `c70fcfc084dfe5454b4cd7e45db385aac587daff30461e0ec9e0e684850ccf9d` |

Both hashes match the pre-existing cleaned package. They are question-scope records
introduced in V2. Input contains 12 documents total plus the incident description
and one 2,672-character attributed story answer. The rejected piping answer and
benchmark-boilerplate prefix are absent. Source limitations are retained. All 11
previously read source passages are reused, not reread.

This is a **reviewed partial storyteller release with operator-selected documents**,
not an autonomous storyteller success. The document choice was written down before
story inference, not selected afterward to manufacture a correct RCA. The RCA
engine and prompts are unchanged from the completed V1 recovery. New delivery
code scopes available sources, permits review withholding without editing candidates,
and stages a single document/answer batch; it does not change RCA verdicts.

Read-only snapshot comparison after V2 dispatch confirmed V1 unchanged. V2 is
currently running; publication and semantic comparison must be recorded separately.

## Interim observation after refinement — 19:00 UTC

All four changed-source reading tasks completed without quarantine. P04 and P05
were read in full; the released answer occupied two source spans. The notebook
contains 154 observations, including all original 100. The reader explicitly
extracted the four connection-schedule segments, the two inline valves, M-101's
closure, V-202's closed observation/opening and the pressure-recovery account.

Nevertheless, frame call `b0053b1c-3674-425f-86a7-5df44258e742` and refinement call
`7f1777d6-e056-4bae-9da9-792e08aadbe9` did not incorporate that sequence into a
specific mechanism. The refined draft has 9 nodes including the focal event;
the three broad V1 explanation branches and their stale missing-diagram/field-log
gaps remain. The erroneous 2.1-bar-by-10:03 summary also remains. This is direct
evidence of a failed knowledge-to-map update so far, not a missing-upload claim.

All three answer-retrieval calls repeated the earlier scope defect: each returned
answers to three visible questions although only one was assigned. The assigned
answer was retained, six extra records were quarantined, and the worker continued.
No retries or verdict substitutions were used. A connection call also retained
the reversed temporal proposal and inappropriate running-indicator barrier idea.

The second connection pass and selected-premise reviews are still pending at this
checkpoint. V2 has **not** been published or passed acceptance. Preserve the run
through its normal remaining work; do not start a new story round or label these
interim observations the completed V2 result.

## Implementation checks

11 storyteller contract tests and 16 existing capacity tests passed; typecheck
passed before dispatch. Tests did not invoke a model. The explicit live jobs above
are the actual model test. No arbitrary output/runtime/question caps were added.
Final typecheck and production build also passed. Lint has zero errors and the
pre-existing unused-variable warning in `prepare-case-content-inputs.mjs:69`.

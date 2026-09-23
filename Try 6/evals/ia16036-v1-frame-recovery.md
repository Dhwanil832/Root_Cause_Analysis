# V1 partial-frame recovery — 2026-09-20

Run: `a20904da-8710-40df-8d58-fec78f451f2a` (same incident, model track and V1).

## Observed failure

Eleven source readers completed with 100 notebook findings. The frame retained
four observation nodes, a focal event, two proposed relationships, three branches
and three evidence requests. Two other relationships referenced notebook findings
that had not been selected as nodes. Their individual rejection caused the entire
frame to be classified as failed, and the foundation gate paused the run.

Original call: `2490f719-0867-4348-8599-a6a27ef51e12`.
This was not a context overflow, missing JSON terminator or Ollama outage.

## General correction (try6.1.0)

1. Select nodes first; frame/refinement grammar requires empty connection lists.
2. Generate connections in a separate task, whose endpoint enum contains only
   actual selected nodes plus EVENT. Supporting premises are not endpoints.
3. Request missing nodes for later refinement without inventing observations.
4. Quarantine invalid individual proposals while allowing a structurally usable
   position to continue. An unusable foundation still pauses; an unresolved
   optional connection does not prevent publication of an honest partial board.
5. Keep original-source premise review and causal verification unchanged. Recovery
   never sets any claim or relationship to supported.

The connection prompt also requires explicit withdrawal of an incorrect existing
arrow, distinguishes temporal order from causation, and forbids forced connectivity.
Structured output is not semantic correctness; decomposition follows the general
[official structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs).

## Recovery receipt

Operator-authorized POST through the live app's D1 connection, with generation 24
and checkpoint hash `c739eff9f3e0c47afbedfc0cd4d45f17517f161bbf66c03db652071e3afea588`.
The old checkpoint was backed up and an explicit try6.0.0 → try6.1.0 migration
record appended. All eleven completed readers, 100 findings, frozen model/evidence
inputs, two quarantined proposals and the original failed trace were retained.
No native writes to SQLite, no fresh incident, no invented answers, no storyteller.

The first new task was `connect`, call `4b572d8e-a6cc-4269-9b41-b219d29e9a29`.

## Verification before resumption

70 automated tests passed (15 investigation workflow, 2 recovery/endpoint tests,
37 evidence/provider regressions, 16 capacity tests). Typecheck and production
build passed; lint had zero errors and one pre-existing unused-variable warning.
These are implementation checks, not a model-performance pass.

Two further regression cases passed after dispatch (72 total): a genuinely unusable
frame still pauses, while one invalid node cannot discard the remaining usable
frame. No production inference or evidence was changed by those tests.

Live publication and substantive model assessment are recorded below. Historical
quarantine means execution is labeled partial even though V1 is published; this
is not a complete-RCA claim.

## Observed non-thinking generation loop and scoped recovery

The second connection task, call `ec58cae5-e0e3-4f09-9f29-3926c42f85c4`, began at
17:27:35 UTC. At inspection it had emitted 36 complete edge records, with **32
exact duplicates consecutively**. This was not just a long novel answer. It used
temperature zero and no explicit presence penalty. The operator cancelled that
single active call through the app; 31,467 public-output characters and the failed
trace were preserved. Incomplete JSON was not applied, and no board verdict changed.

Qwen's documented general non-thinking profile is now explicit: temperature 0.7,
top-p 0.8, top-k 20, min-p 0, presence penalty 1.5, repetition penalty 1, seed 42.
The thinking review profile is unchanged. This is a mode-specific sampling change,
not a different model, case-specific hint, output limit, or automatic fallback.
See [Qwen's official model card](https://huggingface.co/Qwen/Qwen3.5-9B#best-practices).
The card notes that presence penalty can reduce endless repetitions; this does not
guarantee termination or correct reasoning. Every call records its actual profile
and includes it in its cache identity.

Only task `8706a85455e96c7357cfbb0b1bd2bd7bd22a974b584d9bdec58c1e92214cc260`
was resumed, with automatic continuation, not a pause-after-task. Earlier readers,
frame/refinement and answer tasks were not rerun. Typecheck and all 37 targeted
regressions passed before this resume. No token/time/question quotas were restored.

The retry, `6efc47a1-3730-49ad-bd14-d59fc6d3327a`, finished at 17:34:33 UTC
in 39.5 seconds with valid complete output and zero quarantined items. Its request
trace confirms the new instruct profile. This demonstrates completion of this
retry, not universal elimination of repetition or sound causal arrows.

The worker then scheduled seven selected-premise reviews. The first completed;
the second returned `entailed` while listing nonempty necessary missing premises,
so its verdict was rejected and retained for diagnosis. The worker continued to
the third review without stopping V1. No failure was manually turned into support.

## Live dependency pruning

The review queue still included two supporting findings from earlier arrow
wordings that had been replaced: air supply subsequently restored, and the C-11
starter-contact definition. Neither was a node or a premise of an active arrow.
They remain in the notebook and original traces, but no longer need literal
review for this V1 board. `review-dependencies.ts` now derives review work from
current graph dependencies, rather than the union of every historical proposal.
Already completed or in-flight tasks are never cancelled by this rule. Queued
obsolete reviews are explicitly `superseded`, never `completed` or supported.

All 20 workflow/recovery tests pass (73 tests across the existing three suites).
The new test checks retention of source findings and prior verdicts, protection
of in-flight/completed reviews, and preservation of an extra premise whenever
an active connection still needs it. This is dependency pruning, not a count cap.

## Published result

V1 was saved at **2026-09-20 18:01:48.895 UTC (1:01 PM America/Chicago)**,
generation 51, phase 9, execution status `partial`, investigation position ready,
with no worker lease or pending active task. A browser reload independently
confirmed `V1 partial`, the investigation canvas, evidence requests, and the
two superseded tasks. The published result resides in the engine run's immutable
final snapshot, exposed through the normal version dashboard.

[Open V1](http://127.0.0.1:3016/incident/9660f4f2-5fc0-4d0a-917e-8e48641956e3).

| Item | Observed result |
| --- | --- |
| Source coverage | 11 source reads: incident description plus 10 documents; 100 notebook observations retained |
| Board | 5 nodes including the focal event; 4 proposed connections, all unverified |
| Explanation branches | 3 open alternatives |
| Evidence questions | 10 retained: 2 partial, 7 awaiting user, 1 open |
| Required premise reviews | 5 executed: 2 supported, 1 partial, 2 inconsistent outputs rejected |
| Obsolete reviews | 2 superseded without execution; original findings retained |
| Tasks | 18 completed, 5 failed, 2 superseded; no queued/running tasks |
| Quarantine | 13 retained invalid items; no evidence or verdicts silently repaired |
| Causal verification | No verifier calls: each proposed connection depends on an unresolved premise |
| Further versions | No V2 started; storyteller remains disconnected |

The two supported premises are the normal-band recovery observation and AL-44's
P-R input mapping. Only the former is a board node; the latter is a supporting
premise. Consequently only one non-focal board node is evidence-reviewed. The
incident-time statement remains partially supported. Alarm timestamps and the
sampled C-11 RUN values remain proposed because their reviewers contradicted
themselves (`entailed` plus unresolved necessary premises). Neither was promoted
to supported by the harness.

### Remaining substantive failures — not a model-performance pass

1. **Contradictory temporal arrows.** The board retains both recovery → incident
   and incident → recovery as `preceded` proposals, although the former's own
   rationale says recovery occurred after the interruption.
2. **Unsupported barrier interpretation.** C-11 RUN is classified as a barrier
   and given a `failed-to-prevent` connection. The available sampled indication
   does not establish a protective function. The connection remains unverified.
3. **Existing evidence is not consistently used.** Earlier answer/map text asks
   for AL-44's input mapping even though IA-P02 supplies it. The final reviewer
   correctly supports that mapping, but no later map-refinement pass consumes
   the review result in this V1. The final snapshot therefore exposes this
   disagreement rather than silently correcting it.
4. **Numeric summary error.** The map summary says P-R reached 2.1 bar by 10:03;
   IA-P01 places 2.1 bar at 10:05:50 (2.6 at 10:03:10). The generated summary is
   not itself a verified observation.
5. **Over-demanding/inconsistent literal review.** Two reviews explicitly find
   the recorded assertion entailed, then list broader physical-certainty gaps
   as necessary missing premises. The validation gate catches the inconsistency,
   but this prevents otherwise relevant record observations from supporting
   downstream verification. The Turn 2 assertion also remains partial because
   its reviewer demanded independent confirmation beyond the incident account.
6. **Answer task scope.** Each of three answer calls answered other visible
   questions as well as its assigned question. The assigned result was retained,
   but six out-of-assignment answers were quarantined. The current output grammar
   permits more question references than the assignment permits; this remains a
   specific harness improvement for a subsequent revision.

These observations distinguish successful publication from successful causal
reasoning. This is an **engineering-recovered run**, with documented engine and
sampling changes during execution, not a clean unchanged-engine benchmark. No
root cause has been established or human-approved. Published V1 remains untouched
as the baseline for evaluating later changes.

Final implementation checks: 73 tests across workflow/recovery, targeted
regression, and capacity suites; typecheck and production build passed. A final
lint run reported zero errors and the existing unused-variable warning in
`scripts/prepare-case-content-inputs.mjs:69`. No model calls or new revisions were
launched by these checks.

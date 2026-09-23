# Scoring and attribution

Evaluator only. This is a new case-specific rubric, not numerically interchangeable with the R3 rubric.

## The full 100 points

| Stage | Criteria | Points |
| --- | --- | ---: |
| B0 / V1 | Focal event 4; calibration 4; targeted questions 7 | 15 |
| B1 / V2 | Pressure-location join 8; alarm/time interpretation 8; bounded next inquiry 4 | 20 |
| B2 / V3 | Series topology 10; combined physical mechanism 10; recovery evidence 8; drawing applicability 4; observation scope 3 | 35 |
| B3 / V4 | Issued-instruction gap 8; change-routing gap 6; contradiction correction 6; board continuity 5; actions/stopping 5 | 30 |
| Total | T01–T16 in rubric.json | 100 |

For each criterion: full points require its specific relationship, correctly supported and bounded; half points for a materially correct but incomplete relationship; zero for omission, contradiction or an unqualified unsupported conclusion. Keyword mention alone gets zero. A correct relationship stated confidently as fact beyond the evidence cannot receive full credit. Do not double-penalize an error using arbitrary extra deductions.

T03 full credit requires all three question families (routing, time-aligned observations, applicable instructions); half for useful but incomplete targeting. Equivalent relevant tags are acceptable; do not demand an exact number or exact tag wording.

T15 covers continuity and status correctness, not aesthetics alone. Cosmetic prefixes cannot by themselves lose more than 1 of its 5 points. A supported claim that the verifier says is blocked is a substantive calibration defect.

## Timing and denominators

Score each target at its designated stage. Report later recovery separately; do not rewrite the earlier stage score. This preserves whether new evidence actually corrected the board.

If the experiment has not reached a batch, its criteria are `not_testable`, not zero. Report earned points / available points and coverage, e.g. `24/35 available; 35/100 tested`. Do not present this as a final score out of 100.

If an approved batch was supplied but the pipeline dropped a needed passage, its end-to-end criterion can fail, while model-specific attribution is `not_testable: input delivery`. Do not remove pipeline failures from the end-to-end score to inflate performance. If a batch was never released because a run stopped, report coverage rather than guessing a score.

## Concrete success checks

1. Physical pinpoint: T07, T08 and T09 must all be met to claim the model located the intended mechanism.
2. Administrative pinpoint: T12 and T13 must be met to claim it located the specific synthetic control failure rather than saying “procedure issue.”
3. Calibration: no unresolved fabricated critical fact or blocked-but-supported causal link. A high total does not waive this requirement.

Final reporting should give these three outcomes alongside the numeric score. The synthetic deeper explanation must not be presented as proven history.

## Attribute errors using saved evidence

| First failed check | Attribute primarily to |
| --- | --- |
| Correct record never uploaded/released | Experiment setup |
| Record text missing or truncated | Extraction/context construction |
| Correct text stored but pertinent passage not selected | Retrieval |
| Answer present but not delivered to relevant reasoning stage | Routing/harness |
| Necessary context delivered, relationship missed or invented | Reasoning (with exact input/output evidence) |
| Board correct but contradictory validation/display | Verification or presentation |
| Actual stage packet unavailable | Unresolved attribution |

Preserve the node and edge IDs, exact passages, input packet and version. Two independently inspectable evaluators are desirable for later benchmarking, but none is assumed to have graded this package yet. No model scores exist for this case.

# Scoring and interpretation guide

## Required evaluator sequence

1. Freeze the model's final version and all preceding versions.
2. Freeze the evidence-release ledger.
3. Mark which ground-truth findings were actually testable from released evidence.
4. Score each rubric item with a citation to the model output.
5. Record unsupported assertions and incorrectly rejected evidence.
6. Classify every major miss as model, harness, answer-agent, or evidence-package failure.

## Causal-chain recovery levels

| Level | Description |
|---|---|
| 0 — absent | No physical mechanism beyond “beam fell” or generic LOTO language |
| 1 — fragments | Mentions drift, restraint, or interference without connecting them |
| 2 — plausible branch | Connects some mechanism elements but misses a necessary link or confuses chronology with causation |
| 3 — substantially recovered | Connects wedging, yoke drift, relative movement, and link release; identifies design and gravity-control contributors |
| 4 — benchmark complete | Recovers the chain, cites the supporting records, tests alternatives, and preserves raw-evidence limitations |

## Failure classification

- **Model failure:** relevant evidence reached the model, but it missed, distorted, or failed to connect it.
- **Harness failure:** the application failed to route, retrieve, parse, preserve, or display relevant evidence or reasoning.
- **Answer-agent failure:** the answer agent had an answer but returned the wrong fact, leaked adjacent ground truth, or invented a fact.
- **Evidence-package limitation:** the fact was absent or supported only by an unavailable underlying source.
- **Evaluation limitation:** the answer key itself is ambiguous or internally inconsistent.

## Caps for serious errors

- Treating the challenge crane rumor as an established cause caps provenance and contradiction handling at 7/15.
- Claiming the keeper was missing despite contrary evidence caps incident comprehension at 7/10.
- Producing corrective actions with no identified causal target caps corrective actions at 4/10.
- Reversing causal direction from the fall to the pre-event conditions caps causal reasoning at 10/20.
- Copying language from the withheld RCA invalidates the blind run.

## Recommended reporting

Report both:

- **Raw score out of 100**, using all rubric dimensions
- **Testable score**, excluding items whose necessary evidence was not released

Also report causal-chain recovery level separately. This prevents a high question-generation score from being mistaken for a completed RCA.


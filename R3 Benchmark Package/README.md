# R3 carrier-beam benchmark package

This package turns the partner's completed R3 investigation into a controlled benchmark for Try 4 and later versions of the RCA application.

## Non-negotiable separation

- Everything in `01_withheld_ground_truth/` is evaluator-only. Never upload it to a model run.
- Everything in `02_model_visible/` may be supplied to the application according to the run protocol.
- `03_answer_bank/` is for the parent answer-fetching role. It may return individual supported answers, but the files themselves must not be uploaded wholesale.
- `04_challenge_evidence/` contains deliberately weak or misleading records. Release the same challenge records to every comparable run.
- `05_evaluation/` contains the fixed scoring method.
- `06_run_records/` contains blank templates for preserving each independent model run.

## Evidence levels

### Level 1: original synthetic evidence

The `original_synthetic_set/` reproduces the evidence used in the earlier Try 3 and Try 4 testing. It is useful for comparing results with previous runs, but it does not contain enough information to prove the partner's accepted physical mechanism.

### Level 2: ground-truth-derived evidence

The `ground_truth_derived/` records reconstruct the missing evidence statements reported in the partner RCA and presentation. These are controlled benchmark derivatives, not actual company records. They provide enough information for a model to discover the accepted causal chain without giving the model the completed RCA.

## Important limitation

The partner supplied a completed RCA and summary presentation, but not every underlying video file, drawing, measurement sheet, valve test, interview, or signed LOTO record. Therefore this package can support a rigorous controlled benchmark, but it cannot represent a forensic reproduction of the original investigation. Every reconstructed record is labeled accordingly.

## Recommended first run

1. Create one incident and one model track.
2. Load the default references.
3. Provide the incident description and starter documents.
4. Let the model generate its own questions.
5. Release progressive evidence only when a question or causal gap justifies it.
6. Introduce the challenge records at the same point for every model.
7. Preserve the evidence-release ledger and final model artifacts.
8. Score the run without showing the model the evaluator files.

See `05_evaluation/run_protocol.md` for the exact procedure.


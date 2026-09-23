# IA-16036 controlled evidence package

An instrument-air interruption during preparation for maintenance. This is a new case, separate from the R3 beam experiment.

The anchor is historical near-miss record **16036**, Indiana Harbor Utilities, May 20, 2024. The workbook contains an incident narrative and a recorded causal factor, not the underlying drawings, logs or interviews. This package reconstructs those kinds of records for a controlled evaluation. It is **not a recovery of the actual investigation evidence**.

## Start here

For the first RCA pass, use only:

1. `02_model_visible/00_incident_input/incident_summary.md` as the incident description.
2. The three files in `02_model_visible/01_default_references/` as default references.
3. The three files in `02_model_visible/02_starter_documents/` as starter documents.

Keep default, starter and later answer-request documents in their separate app scopes. Use a fresh incident/model track with no R3 documents or previously accumulated knowledge. Snapshot the default references for this run rather than altering another run's library.

All records are Markdown, which Try 4's document extractor supports. This avoids mixing document-reading/OCR failures into the first reasoning test. Actual upload and model execution have not been tested for this package.

## What the package tests

The useful clues are distributed across ordinary records. The model must connect equipment identity, measurement location, chronology, configuration and document applicability. A plausible-sounding cause or a matching keyword is not sufficient.

| Release | Intended use | New records |
| --- | --- | ---: |
| B0 | Initial description, defaults and starter records; then stop after board V1 | 7 |
| B1 | First answer/evidence batch; then a separate RCA pass for V2 | 4 |
| B2 | Second answer/evidence batch; then a separate RCA pass for V3 | 4 |
| B3 | Third answer/evidence batch; then a separate RCA pass for V4 | 3 |

These are maximum planned stages, not permission to run all four unattended. Review each completed board before advancing. The primary controlled comparison uses identical batches at identical stages. Whether the model asked for the right evidence is scored separately.

## Folder boundaries

| Folder | Who may read it |
| --- | --- |
| `01_withheld_ground_truth/` | Evaluator only: historical anchor, fixed reconstruction and limits |
| `02_model_visible/` | RCA and answer-fetching roles, but only records released so far |
| `03_answer_bank/` | Separate answer-generation role only; never upload wholesale |
| `04_challenge_evidence/` | Individual records released at their assigned stage; never expose this folder name to RCA |
| `05_evaluation/` | Evaluator only: release plan, expectations and scoring |
| `06_run_records/` | Operator/evaluator; actual model inputs must be built from an allowlist |

Do not recursively upload this package or mount its root as the RCA knowledge base. Folder separation is an operating convention, not access control.

## Two independent jobs

RCA reads a frozen evidence set, produces questions and a board, and stops. A separate answer-generation job later reads the exported questions and permitted records, writes a candidate answer payload, and stops. After review, that payload can become input to a separately started RCA pass. Neither job invokes or restarts the other.

See `05_evaluation/run_protocol.md`. The package includes templates and a read-only validator, not a new app runner or an implementation of process isolation. No model, storyteller or automation has been started.

## Provenance and safety

All model-visible documents are explicitly labeled evaluation records. The event and broad sequence are historically anchored; exact asset tags, pressures, times, personnel codes, drawings, procedure numbers and workflow records are synthetic. The historical causal factor and the deeper synthetic explanation are distinguished in the evaluator files. No personal names, addresses, employee IDs or medical details were copied.

This is not an operating procedure, plant drawing or authorization to manipulate equipment. A correct answer must preserve unknowns and must not turn this reconstruction into allegations about actual employees or the partner's systems.

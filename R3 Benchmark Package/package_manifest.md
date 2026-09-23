# Package manifest

| Area | Purpose | Model visibility |
|---|---|---|
| `01_withheld_ground_truth/original_partner_rca/` | Original partner PDF and PowerPoint | Never visible |
| `01_withheld_ground_truth/structured_causal_map.md` | Normalized accepted causal chain | Never visible |
| `01_withheld_ground_truth/expected_findings.md` | Required, secondary, rejected, and unresolved findings | Never visible |
| `01_withheld_ground_truth/corrective_action_alignment.md` | Accepted causes mapped to partner actions | Never visible |
| `01_withheld_ground_truth/ground_truth_limitations.md` | Limits and inconsistencies in the supplied answer key | Never visible |
| `02_model_visible/00_incident_input/` | Initial incident narrative | Visible at creation |
| `02_model_visible/01_default_references/` | Partner standards and synthetic orientation material | Visible as default knowledge |
| `02_model_visible/02_starter_documents/` | Initial scene, notification, and evidence register | Visible at creation |
| `02_model_visible/03_progressive_evidence/original_synthetic_set/` | Earlier controlled evidence records | On request |
| `02_model_visible/03_progressive_evidence/ground_truth_derived/` | Controlled records derived from partner findings | On request |
| `03_answer_bank/` | Supported answers and unknowns for the parent answer-fetching role | Never uploaded wholesale |
| `04_challenge_evidence/` | Low-authority and conflicting test records | Controlled release |
| `05_evaluation/` | Fixed rubric, scoring guide, and run protocol | Evaluator only |
| `06_run_records/` | Blank run manifest and scorecard | Evaluator only |

## Source classes

- **Partner source:** an unchanged file supplied by the industry partner.
- **Historical fact:** a fact explicitly reported in the partner RCA or presentation.
- **Controlled derivative:** a benchmark record reconstructed from reported partner findings.
- **Synthetic scenario fact:** a controlled detail created for testing and not asserted as a company fact.
- **Open:** not established by the currently supplied partner material.


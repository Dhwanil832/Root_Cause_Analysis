# Blind R3 benchmark run protocol

## Comparability rules

- Run one model at a time.
- Create a separate incident and model track for every run.
- Do not share answers, questions, knowledge bases, causal nodes, or conclusions between runs.
- Use the same application version, model settings, time ceiling, default references, challenge timing, and parent-answer policy.
- Preserve every version, stage checkpoint, error, evidence release, and human intervention.

## Phase 0 — creation

Provide:

- `02_model_visible/00_incident_input/incident_summary.txt`
- All files in `02_model_visible/01_default_references/`
- All files in `02_model_visible/02_starter_documents/`

Do not provide any withheld-ground-truth or answer-bank file.

## Phase 1 — unguided investigation

Allow baseline understanding, tagging, specialist questioning, question brokerage, and initial causal-board creation. Do not guide the model toward hydraulic drift, wedging, or the keeper path.

## Phase 2 — progressive answering

For every material question:

1. Use `03_answer_bank/source_release_map.md`.
2. Release the smallest matching original synthetic record.
3. If the model correctly exposes the remaining gap, release the matching `GTDE` record.
4. If neither level answers the question, return `Not established` using the answer-agent format.
5. Record the question, answer, released source, and version in the evidence-release ledger.

## Phase 3 — challenge evidence

After the model has established an initial evidence base, release all three challenge records together. Do not warn the model which records are misleading. Their own metadata contains the provenance cues required for evaluation.

## Phase 4 — causal consolidation

Allow the model to update its causal board. Continue only while new questions can discriminate a live causal branch, resolve a contradiction, verify a link, or define an action target.

## Phase 5 — completion

A run may end when:

- the critical physical sequence is supported or all remaining links are explicitly blocked by unavailable evidence;
- credible alternatives have been bounded;
- the model has either produced cause-linked actions or correctly withheld them;
- another version would not add material investigative value.

## Internet use

Internet research may provide general engineering background. It must never supply incident-specific facts and must be logged separately from case evidence.

## Outputs to preserve

- Incident and track IDs
- Model and exact model version
- Generation settings and application commit or build identifier
- Every model version
- Stage traces and failures
- Evidence-release ledger
- Questions asked, merged, skipped, and answered
- Evidence claims and contradictions
- Causal board and verification state
- Corrective actions and approvals
- Completed rubric and evaluator notes


# R3 Ollama model evaluation protocol

Each installed Ollama model receives a separate incident and model track. No answers, specialist knowledge, causal nodes, or conclusions are shared between model runs.

## Common inputs

- The same R3 incident description.
- The same default reference library.
- The same three starter documents.
- The same consolidated requested-evidence packet and the same three challenge records for evidence-complete creation runs.

## Execution note

The first clean Qwen 3.5 pass was created before the consolidated packet was adopted. It received the three starter documents, asked its own questions, and then received the consolidated requested/challenge packet as an answer attachment. That evidence-update request reached the 30-minute client ceiling and did not commit version 2. Its initial version remains gradeable, but its provenance/contradiction and evidence-complete performance are penalized rather than treated as untested.

All later evidence-complete model runs received the consolidated packet at incident creation. The pipeline still generated questions before the answer-fetching stage searched the attached documents. Llama 3.2 received one focused parent answer because its first version exposed a narrow support-state question; its second version is the scored snapshot. No model received another model's facts, questions, answers, or conclusions.

## Parent-model behavior

- Answer from the staged evidence package whenever a matching record exists.
- Attribute claims to their source and preserve uncertainty.
- If a question is not answered by available evidence, state what remains unknown.
- Create an additional synthetic record only when the requested information is important and absent from the existing package.
- Introduce the same low-reliability or conflicting evidence to every evidence-complete run. Such evidence remains labeled as synthetic test material and retains source-quality cues; it is never presented as a real company record.
- Continue until the model produces a substantially developed causal board and corrective-action set, or further versions cease adding material investigative value.

The operational ceiling was 1,800 seconds per full app request. A client timeout was followed by a direct database/API check. A model counts as completed only when a real analysis version was committed; the history page's fallback display of "version 1" for an empty track does not count.

## Scoring rubric - 100 points

| Dimension | Points | What earns credit |
|---|---:|---|
| Incident comprehension | 10 | Correct entities, sequence, context, and clear unknowns |
| Tag selection | 10 | Broad but relevant tags without treating tags as causes |
| Investigative questions | 15 | High-yield, answerable questions that open distinct causal directions |
| Evidence targeting | 15 | Requests the right drawings, isolation records, sequence records, observations, and physical evidence |
| Provenance and contradiction handling | 15 | Separates source types, detects conflicts, resists weak or misleading evidence |
| Causal reasoning | 20 | Builds evidence-linked conditions, changes, barriers, contributing causes, and root-cause candidates without chronology-only leaps |
| Corrective actions | 10 | Actions address verified system conditions with owners, completion evidence, and effectiveness checks |
| Calibration and trace quality | 5 | Transparent confidence, limitations, and useful decision trace |

## Evaluation artifacts

For each model, preserve the incident ID, track ID, every version snapshot, supplied evidence, and a final rubric score with cited examples from that model's output.

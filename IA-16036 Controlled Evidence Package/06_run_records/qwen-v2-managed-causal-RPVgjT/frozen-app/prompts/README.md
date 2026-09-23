# Try 4 prompt package

These prompts are organized by pipeline stage so an investigator can inspect and revise one responsibility without changing the others.

The deterministic router owns stage order, state isolation, retries, validation, and persistence. Prompts never decide which model track can read another track. Each run receives only the original incident plus evidence already stored inside its own model track.

## Stage order

Shared evidence rules are followed by document and image intelligence, incident understanding, incident structuring, tagging, selected specialists, question brokering, dynamic answer fetching, evidence processing, causal analysis, causal verification, corrective actions, and revision reporting.

## Specialist exemplars

Every specialist prompt contains eight kickoff question examples paired with the
potential investigation directions they may open. These tables shape the
agent's questioning pattern without acting as mandatory checklists. Agents must
review current evidence first, skip covered or immaterial examples, and create
different questions when the case presents a material direction not represented
by the examples.

Stable policy text is loaded before dynamic incident evidence. Runtime schemas and stable IDs live in code. Every prompt defines an outcome, evidence boundary, success condition, stopping rule, and handoff. Prompts request concise decision summaries rather than private chain-of-thought.

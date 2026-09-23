# Prompt package

These prompts are organized by pipeline stage so an investigator can inspect and revise one responsibility without changing the others.

The deterministic router owns stage order, state isolation, retries, validation, and persistence. Prompts never decide which model track can read another track. Each run receives only the original incident plus evidence already stored inside its own model track.

## Stage order

1. shared: non-negotiable safety, evidence, and output rules
2. baseline: site vocabulary, relationships, normal state, and timeline gaps
3. evidence: answer and document handling
4. tagging: fixed-taxonomy routing
5. tag-agents: independent subject exploration
6. question-broker: overlap control and coverage record
7. revision: new immutable version after evidence changes

## Specialist exemplars

Every tag-agent prompt contains eight kickoff question examples paired with the
potential investigation directions they may open. These tables shape the
agent's questioning pattern without acting as mandatory checklists. Agents must
review current evidence first, skip covered or immaterial examples, and create
different questions when the case presents a material direction not represented
by the examples.

Prompts ask for concise decision records, evidence references, unknowns, and confidence. They must never request or expose private chain-of-thought.

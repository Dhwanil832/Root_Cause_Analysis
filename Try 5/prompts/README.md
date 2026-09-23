# Try 5 prompt package

These prompts are organized by pipeline stage so an investigator can inspect and revise one responsibility without changing the others.

The deterministic router owns stage order, state isolation, retries, validation, and persistence. Prompts never decide which model track can read another track. Each run receives only the original incident plus evidence already stored inside its own model track.

## Stage order

The active durable engine routes original-evidence reading, incident understanding, tagging, selected specialists, question brokering, answer fetching, complete literal-claim review, causal analysis, causal verification, and human-gated corrective actions. Older stage prompts remain for historical compatibility; the active task map is `src/engine/prompts.ts`.

`claim-review/literal.md` compares the entire original claim directly with original passages. The rejected evidence-blind interpretation stage is not scheduled. `claim-interpretation/task.md` and `claim-review/task.md` are legacy prompts, not the active review pipeline. See `src/engine/review/README.md` for limitations and acceptance status.

`causal-verification/node.md` checks whether the node's own statement is supported.
`causal-verification/task.md` checks a relationship's mechanism or temporal order.
The executor supplies an explicit node/relationship discriminator and selects the
matching prompt. An unknown causal contribution must not downgrade an established
condition; two established conditions must not automatically establish a link.

## Specialist exemplars

Every specialist prompt contains eight kickoff question examples paired with the
potential investigation directions they may open. These tables shape the
agent's questioning pattern without acting as mandatory checklists. Agents must
review current evidence first, skip covered or immaterial examples, and create
different questions when the case presents a material direction not represented
by the examples.

Stable policy text is loaded before dynamic incident evidence. Runtime schemas and stable IDs live in code. Every prompt defines an outcome, evidence boundary, success condition, stopping rule, and handoff. Prompts request concise decision summaries rather than private chain-of-thought.

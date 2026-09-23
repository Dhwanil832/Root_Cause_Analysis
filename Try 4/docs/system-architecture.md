# Try 3 conceptual architecture

## Fixed agents

- Document and Image Intelligence reads preserved visual evidence through a compatible multimodal model, producing atomic located observations and explicit limitations without declaring causes. Machine-readable text continues through exact extraction. Observations enter the evidence ledger as proposed until human review.
- Incident Understanding establishes site vocabulary, layout, work context, normal state, event state, people, and chronology gaps.
- Incident Structuring maintains the entity list, focal event, conditions, impact, and timeline.
- Tagging selects from the fixed taxonomy as investigation entry points.
- Question Broker runs after questions exist. It keeps distinct evidence needs, merges genuine overlap, records every covered proposal, and routes the canonical question back to all relevant specialists.
- Evidence Processing separates observations, records, testimony, interpretations, inferences, and assumptions, and opens contradictions instead of silently resolving them.
- Causal Analysis builds and revises a board of events, conditions, changes, barriers, candidate causes, impacts, and evidence.
- Causal Verification tests each causal link, looks for parallel branches and disconfirming evidence, and prevents premature root-cause claims.
- Corrective Actions begins only when findings are supported enough to target and defines completion evidence plus an effectiveness check.

## Fixed pool selected dynamically

The fifteen specialist agents correspond to the fixed tag taxonomy. Only selected specialists run. Each keeps an independent knowledge base so one discipline can notice what another missed. Cross-specialist information moves through explicit question routing and the common answer-fetching layer rather than a silently blended memory.

## Dynamically spawned work

Answer fetching is conceptually one short-lived worker per open question. It searches the current track’s reference documents, starter documents, question-response documents, prior answers, and all specialist knowledge bases. It either returns a cited answer, marks the result partial or contradictory, or sends a precise evidence request to the user.

Causal analysis may propose additional evidence questions. Those questions enter the same broker and answer-fetching path as specialist questions.

## Version rule

Every selected model owns its track, evidence attachments, specialist knowledge bases, conflicts, causal board, and V1/V2/V3 sequence. Adding one answer or document preserves the preceding snapshot and reruns the investigation loop only for that track.

Human review follows the same rule. Confirming or rejecting a document observation, accepting or rejecting a causal node, closing a causal branch, or approving a corrective action creates a new version with an explicit actor, timestamp, action, target, and optional rationale. Moving nodes on the canvas is a viewing preference and does not alter evidence or create an investigation version.

## Provider boundary

Ollama and hosted models receive the same stage prompts and structured-output contracts. Hosted provider credentials are encrypted at rest and never enter the incident, evidence packet, model output, trace, or export. Provider configuration is operational state rather than investigation evidence.

Vision-capable Ollama models receive preserved images directly. Responses-compatible hosted models can receive images and scanned files. When a selected model lacks the required modality, the system preserves the source and records the limitation rather than fabricating an interpretation.

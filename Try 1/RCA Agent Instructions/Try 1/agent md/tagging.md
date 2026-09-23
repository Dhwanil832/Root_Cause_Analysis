# RCA Tagging Guide

## Purpose

Use this guide to identify which investigation tags are supported by an incident report and to route the investigation into the appropriate tag guides.

Tags are investigation entry points. A tag means that a subject may be relevant and deserves initial exploration. It does not mean the subject caused the incident.

## Required behavior

1. Read the full incident description before selecting tags.
2. Separate reported facts from assumptions, interpretations, and missing information.
3. Use only the fixed tags listed in this guide.
4. Select every tag that has a reasonable factual connection to the event, exposure, work, equipment, or surrounding conditions.
5. Do not force a particular number of tags. Many reports will naturally activate three or four, but a simpler or more complex event may activate fewer or more.
6. Give a short evidence-based explanation for each selected tag.
7. Do not use tag selection to declare a root cause, assign blame, or imply that a control failed.
8. If a possible subject is unsupported but important, record it as an unknown rather than selecting the tag as fact.
9. When a selected tag exposes another relevant direction, hand off to that tag without repeating its complete question set.
10. Use Other / novel condition only after checking every defined tag.

## Fixed tag set

| Tag | Use when the report indicates | Guide |
|---|---|---|
| Human involvement | A person's actions, capability, condition, work practice, PPE, or exposure may matter | [human-involvement.md](human-involvement.md) |
| Electrical incident | Electrical equipment, circuits, wiring, batteries, energized work, shock, or arc-flash potential is involved | [electrical-incident.md](electrical-incident.md) |
| Equipment or tool involvement | Machinery, tools, guards, fixtures, or mechanical components are involved | [equipment-tool-involvement.md](equipment-tool-involvement.md) |
| Mobile equipment / vehicle involvement | Forklifts, loaders, trucks, trailers, carts, or other mobile equipment are involved | [mobile-equipment-vehicle-involvement.md](mobile-equipment-vehicle-involvement.md) |
| Crane, lifting, or suspended-load involvement | Cranes, hoists, rigging, lifting devices, suspended loads, or lifting operations are involved | [crane-lifting-suspended-load-involvement.md](crane-lifting-suspended-load-involvement.md) |
| Rail / locomotive involvement | Locomotives, rail cars, tracks, switches, derailers, or rail movements are involved | [rail-locomotive-involvement.md](rail-locomotive-involvement.md) |
| Stored, released, or gravity energy | Pressure, tension, gravity, falling objects, hydraulic, pneumatic, thermal, or other stored energy may be involved | [stored-released-gravity-energy.md](stored-released-gravity-energy.md) |
| Isolation / LOTO involvement | Hazardous-energy isolation, lockout, tagout, tryout, or restoration of energy may be involved | [isolation-loto-involvement.md](isolation-loto-involvement.md) |
| Maintenance, outage, or non-routine work | Repair, inspection, cleaning, adjustment, changeover, outage, startup, shutdown, or temporary configuration is involved | [maintenance-outage-non-routine-work.md](maintenance-outage-non-routine-work.md) |
| Process or material involvement | Process conditions or materials such as molten metal, chemicals, dust, scrap, coils, heat, welding, or cutting are involved | [process-material-involvement.md](process-material-involvement.md) |
| Work-environment involvement | Access, height, surfaces, housekeeping, weather, lighting, noise, atmosphere, congestion, or physical surroundings are involved | [work-environment-involvement.md](work-environment-involvement.md) |
| Procedure / planning involvement | Procedures, permits, risk assessments, sequencing, job setup, staffing, or planning may matter | [procedure-planning-involvement.md](procedure-planning-involvement.md) |
| Communication / supervision involvement | Handover, instructions, signals, coordination, contractor interfaces, supervision, or escalation may matter | [communication-supervision-involvement.md](communication-supervision-involvement.md) |
| Animal / wildlife / insect involvement | An animal, wildlife, bite, sting, nest, or biological encounter is involved | [animal-wildlife-insect-involvement.md](animal-wildlife-insect-involvement.md) |
| Other / novel condition | A material investigation direction does not fit any defined tag | [other-novel-condition.md](other-novel-condition.md) |

## Tagging output

For each selected tag, provide:

- Tag name
- Status: active, uncertain, screened out, completed, or reopened
- Reason selected
- Supporting report facts
- Important unknowns
- Tag guide to process next

An uncertain tag is appropriate when the report contains a meaningful signal but not enough evidence to confirm relevance. State what information would confirm or screen it out.

## How to process a selected tag

1. Open the tag's Markdown guide.
2. Review facts already established by the report and by other processed tags.
3. Ask only the first-pass questions that remain unanswered and could change the investigation direction.
4. Pursue a branch only when its answer remains plausible and material.
5. Record the answer, evidence source, confidence, and remaining gap.
6. Activate another tag when a handoff condition is met.
7. Stop the tag path when it has been answered, screened out, duplicated by stronger evidence elsewhere, or is no longer material.

## When the tag was processed before

Do not restart its questionnaire.

Before asking anything:

1. Read the tag's existing findings, evidence, open questions, and prior status.
2. Reuse confirmed facts unless new evidence conflicts with them.
3. Identify only material gaps, contradictions, changed conditions, or newly activated branches.
4. Ask the smallest number of questions that can resolve those items.
5. Prefer one question that distinguishes several plausible branches over several narrow yes/no questions.
6. Do not ask a person to repeat information already available in reports, records, photographs, logs, or prior answers.
7. Reopen a completed tag only when new evidence could materially change its conclusion.

## Overlap between tags

Overlap is expected, but duplication is not.

For example, an electrical investigation may reveal uncertain isolation. The electrical guide should establish that isolation is relevant, activate Isolation / LOTO involvement, and then stop short of repeating the full LOTO investigation.

When two tags need the same fact, ask once, store the answer as shared evidence, and reference it from both tags.

## Question design rules

- Questions are starting points, not a complete causal-analysis script.
- Prefer open, evidence-seeking wording.
- Ask what happened, what state existed, what changed, what was expected, and what evidence supports the answer.
- Avoid blame-seeking language.
- Avoid embedding an assumed failure in the question.
- A useful question should expose, distinguish, confirm, or screen out a potential causal direction.
- If an answer cannot change the investigation direction, do not ask the question.


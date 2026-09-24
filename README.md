# Progressive Evidence-Driven Root Cause Analysis

Research prototype for investigating whether AI-assisted systems can build, test, and revise industrial causal explanations as evidence arrives over time.

> **Research question:** Can a progressive, evidence-driven investigation workflow produce better-supported industrial causal explanations and better revisions than simpler ways of analyzing the same evidence?

## Why this problem matters

Industrial investigations rarely begin with a complete and internally consistent account. Relevant information may be distributed across incident descriptions, operating logs, drawings, maintenance records, procedures, measurements, photographs, and witness accounts.

A useful investigation therefore has to do more than generate a plausible final explanation. It must distinguish established facts from interpretations, maintain plausible alternatives, identify consequential information gaps, seek evidence that can distinguish competing explanations, and revise earlier conclusions when new evidence changes the picture.

This project studies that process as an evolving investigation rather than a single-pass diagnosis.

## Core idea

The current research design centers the investigation on **testable causal explanations** rather than isolated questions or extracted statements.

For each explanation, the system is intended to track:

- the outcome or transition being explained;
- the proposed mechanism;
- conditions that must hold for that mechanism to work;
- supporting and challenging evidence;
- assumptions that remain unresolved;
- observations that could distinguish it from alternatives.

The workflow then uses new answers or documents to strengthen, weaken, correct, split, combine, or withdraw explanations while preserving earlier investigation versions.

## Investigation workflow

A typical investigation proceeds through the following stages:

1. **Establish the incident context** from the initial description and available documents.
2. **Identify relevant investigative perspectives** based on the equipment, environment, people, and operating conditions involved.
3. **Develop scoped information needs** tied to concrete uncertainties or possible mechanisms.
4. **Broker and answer questions** while preserving why each question matters and what remains unresolved.
5. **Build competing causal explanations** and connect claims only when the available evidence supports those relationships.
6. **Separate factual support, causal role, and connection validity** instead of treating every supported statement as a cause.
7. **Publish a versioned investigation state** containing the current explanations, evidence, uncertainties, open questions, and causal board.
8. **Revise the investigation when new evidence arrives**, preserving the previous version and recording what changed and why.

The goal is not to maximize the number of agents, questions, or graph nodes. Progress means a justified change in understanding.

## Current evaluation direction

The project is being developed around controlled evidence-release experiments in which an incident is revealed progressively across multiple stages.

The evaluation is intended to test whether the system can:

- preserve correct earlier findings when new evidence arrives;
- revise explanations for the right evidential reasons;
- identify useful information needs;
- combine evidence distributed across documents;
- represent uncertainty and contradiction appropriately;
- avoid unsupported causal claims;
- outperform simpler document-grounded and earlier workflow baselines under the same evidence schedule.

Historically anchored synthetic investigation packages are used where the original industrial records do not contain enough evidence to support a controlled causal reconstruction. Historical facts and constructed test details are kept conceptually separate.

## Repository map

This repository contains successive research prototypes, controlled evidence packages, evaluation material, and design documents.

| Path | Purpose |
| --- | --- |
| `Try 1` - `Try 7` | Successive system and mechanism iterations developed during the research process. |
| `RCA_RESEARCH_OVERVIEW_AND_PLAN.md` | Current high-level research objective, workflow, evidence-generation plan, and evaluation strategy. |
| `RCA_MECHANISM_REDESIGN_PROPOSAL.md` | Design proposal for centering the investigation on evidence-tested explanations. |
| `RCA_IMPLEMENTATION_AND_PAPER_CHECKLIST.md` | Implementation, experiment, reproducibility, and paper-readiness checklist. |
| `RCA_RESEARCH_BRIEF_TRY4_TRY6_AND_PAPER_OPTIONS.md` | Research brief connecting earlier iterations to candidate paper directions. |
| `RCA_SYSTEM_REVIEW_2026-09-18.md` | Recorded review of system behavior and outstanding issues. |
| `R3 Benchmark Package` | Controlled benchmark material for the R3 investigation setting. |
| `Synthetic Evidence Packages 2026-09-22` | Progressive evidence packages used for controlled investigation experiments. |
| `RCA Presentation Outputs` | Figures and presentation-oriented outputs. |
| `RCA Progress Documents` | Working research notes and progress records. |

## Research status

**Ongoing research.** The repository includes developmental prototypes, proposed mechanisms, and evaluation infrastructure. It should not be interpreted as a validated autonomous industrial investigator or a safety-certified decision system.

The current research objective is to determine, through controlled experiments, whether the progressive evidence-driven mechanism produces better-supported and more appropriately revised causal explanations than simpler alternatives.

## Responsible-use boundary

The system is intended as an **AI-assisted investigation tool**, not an autonomous authority for assigning blame, issuing plant instructions, or making safety-critical decisions. Human review remains necessary for causal findings and corrective actions.

Public or redistributable artifacts should also be checked for partner permissions, identifying information, and confidentiality constraints before release.

## Affiliation

Research conducted through the **Center for Innovation Through Visualization and Simulation (CIVS), Purdue University Northwest**.

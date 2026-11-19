---
name: components-before-lead
description: "For v0.5 changes, build each role (Assessor, Specialist, Intake) first and change the central Lead (cferp) last"
metadata:
  node_type: memory
  type: feedback
  originSessionId: b528c656-e5e6-4e7a-8f0a-ccec4ed6fa66
  modified: 2026-11-11T17:41:03.927Z
---

When a v0.5 step touches several roles, change the individual components first (hera1 Assessor, sahs Specialist, piris Intake, ewv3 Evidence Worker) and wire the central Lead (`cferp/`) last. Said 2026-11-11 when starting Step 1 of DESIGN_PLAN_v0_5.md.

**Why:** the user wants each component settled and tested on its own before the Lead is changed to use it.

**How to apply:** keep Lead edits to the minimum needed so the pipeline still runs (e.g. a compatibility mapping in `cferp/integration.py`), note what the Lead must do later, and do the Lead wiring as the final piece. Related: [[rca-ground-truth-and-goals]].

---
name: rca-ground-truth-and-goals
description: "Where the R3 ground-truth chart and gold evidence map live, what the user wants from the harness, and standing rules (no code changes until allowed)"
metadata:
  node_type: memory
  type: project
  originSessionId: b528c656-e5e6-4e7a-8f0a-ccec4ed6fa66
  modified: 2026-10-30T18:45:50.691Z
---

The RCA harness (V3 closed loop) is scored against a human CauseLink report, not the
HTML board in Downloads (that one is a produced chart). Confirmed by the user on 2026-10-30:
- `ground_truth/r3_human_rca_chart.json` (23 nodes, 8 solutions), from the originally supplied R3 RCA chart PDF (kept locally, not in the repo)
- `ground_truth/evidence_map_draft.json` (which sentences in E01-E16 bear on each node, plus designed traps)

Overall goal: documents arrive at any time (with the incident, answering requests, or
unprompted); the system keeps investigating with what it has, checks each new document
against every existing claim, asks for missing evidence, never declares an unsupported
root cause, and gives the same board regardless of order. Plans live in
`FRAMEWORK_AUDIT.md`, `RESEARCH_BRIEF.md`, `FRAMEWORK_TASK_GOALS.md` in the project root.

**Why:** the user is building a framework whose custodian simulator must be fixed and
independent of the model under test, so two local models can be compared fairly. The
custodian answers arbitrary questions from the ground truth and says "unknown" for
nodes the packet does not cover.

**How to apply:**
- Do NOT change harness code, or the existing unprompted-document test in
  `test_cferp_workflow.py`, until the user explicitly allows code changes.
- Use `.venv/bin/python` (clingo installed); `tests_ollama` needs
  `PYTHONPATH=V1_V2_Prompt_and_Rules/source/RCA_Version_Labeled_Codebase`.
- Do not install packages or pull models without asking first.
- Planned order: ground truth and fixed simulator first, then retrieval, new-document
  handling and settling together, then judging, requests, claim dedupe, ID slips.

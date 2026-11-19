---
name: no-claude-attribution-in-commits
description: Never add Co-Authored-By Claude or other Claude attribution to commits or PRs in this repo
metadata:
  node_type: memory
  type: feedback
  originSessionId: b528c656-e5e6-4e7a-8f0a-ccec4ed6fa66
  modified: 2026-11-08T20:30:45.533Z
---

Do not add a `Co-Authored-By: Claude …` trailer, or any other Claude attribution, to commit messages or PR descriptions for this project. The commit should list only the user as its author.

**Why:** GitHub listed Claude as a contributor on the public repo Dhwanil832/Root_Cause_Analysis because of that trailer, and the user asked for it to be removed (2026-11-08).

**How to apply:** this overrides the default attribution reminder. Write commit and PR text without attribution lines. Related: the repo must also never name the company or the exact plant, see [[rca-ground-truth-and-goals]].

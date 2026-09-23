# Separate-stage run protocol — IA-16036

No run has been performed for this package. Treat this as a development/pilot derivative of historical incident 16036, instrument-air interruption, 2024-05-20; do not place another derivative of this incident in a held-out split.

1. Read validation and resolve technical/semantic limitations for targets that will be scored. Freeze package bytes, guide version, target set, evaluator method and weights if any. Use `package_manifest.json` hashes. Package status is prepared_for_pilot.
2. Create a fresh incident and **one independent model track**. Use a fresh investigator context with no authoring history/private scenario. Record model tag/provider, actual config, app/prompt revision and extraction/retrieval settings. Record unknown settings as unknown.
3. Deliver exactly B0 description/defaults/starters, preserving their scopes and source identities. Keep private/future files inaccessible in filesystem, retrieval, caches and prompts. Use the explicit manifest allowlist, never a recursive root upload.
4. Run RCA to a published working V1. Export exact supplied bytes, extracted text, retrieval/delivery receipts when available, questions, partial answers, hypotheses, nodes, edges, uncertainty, raw responses and errors. Do not demand a complete chain at first pass.
5. Stop RCA. Prepare B1 separately. If testing a storyteller/answer agent, give it only eligible originals and bank entries. Save its unmodified candidate payload and source-fidelity review. It must not start RCA.
6. Bind candidate answers to actual questions/merged originals/subparts/specialists, model track and expected V1 parent. Documents in this fixed batch do not depend on the model asking a preferred exact phrase. Record unanswered parts; do not silently convert them to answered.
7. Commit the authorized batch and run V2. Compare semantic changes against the predeclared targets. Verify that citations actually reached the model. Rewording or more nodes alone is not progress.
8. Repeat with B2 to V3. Supersede D05 rev1 with rev2 only in active retrieval; preserve all previous version snapshots and original bytes. A correction retracts its specified interpretation, not every fact in the source.
9. Export everything required to reconstruct input/output lineage. Do not silently repair model outputs. Record any human intervention and its effect on autonomous-evaluation claims.
10. Repeat another model independently with identical frozen releases. Do not share evolving answers or knowledge between tracks.

## Attribution before blame

| Finding | Treatment |
| --- | --- |
| Target requires absent, unreleased, inconsistent or technically invalid evidence | Package limitation; affected target not_testable |
| Intended record not delivered/extracted, wrong question routing or lost correction | Harness/integration failure |
| Provider/transport/context/resource failure prevented execution | Execution/environment failure, separate from RCA quality |
| Delivered intact evidence misread, unsupported claim or invalid causal link | Candidate model-reasoning failure; cite actual input/output |
| Malformed output | Check contract/parser/transport before assigning formatting failure |
| Trace cannot distinguish the above | Inconclusive; no speculation |

Review outcomes: met, partial, missed, overclaimed, not_testable. Store exact output excerpts and source locations. Semantic assessment remains unassessed until an actual human or declared validated scorer reviews it; neither this generator nor an automatic reference check is an independent judge.

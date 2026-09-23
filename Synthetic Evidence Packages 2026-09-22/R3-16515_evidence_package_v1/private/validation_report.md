# Validation — R3-16515

Date: 2026-09-22. Package status: **technical_review_needed**. Authored/self-reviewed by Codex. No independent technical reviewer, model run or semantic scorer is claimed.

## Executed checks

`package_tools.py` produced **225 passing structural checks, zero failing checks** for this package. Full check details are saved in [integrity_results.json](integrity_results.json). These are small integrity assertions, not 225 independent RCA evaluations.

| Check | Status / method / scope |
| --- | --- |
| JSON parses, required files exist, document identities unique | pass — executed validator over all package JSON and required files |
| Manifest matches all payload revisions and headers | pass — 13 concrete document revisions; IDs/revisions matched to bytes |
| Hashes | pass — SHA-256 recomputed from every payload file |
| Historical source preserved | pass — original workbook hash remains `bd900c0ff1f6736143a64dfecd3e9c1a0ee7eb8ac32f62a74f8bba830df689f1` |
| Release lineage and cumulative membership | pass — B0 parent null → V1, B1 parent 1 → V2, B2 parent 2 → V3 |
| Correction history | pass — D05 revision 2 supersedes revision 1 at B2; original bytes retained |
| Answer quotes and source eligibility | pass — 11 needs, verbatim excerpts resolved at eligible stage; source-section headings found |
| Target references and contract | pass — 10 targets, fields and stage-eligible evidence bundles checked |
| Operator/future markers in payload | pass — known-marker scan; this is not exhaustive security proof |
| Placeholders/body completeness | pass — required full bodies and basic placeholder scan |
| Cumulative export | pass — B0/B1/B2 exported to fresh temporary directories, respectively 6/9/12 evidence files; original hashes matched |
| Export contamination/overwrite | pass — no operator files in exported views; D05 revision 2 only at B2; existing destination refused |
| Live application ingestion, retrieval and access control | not_checked — no application was called; exporter is not a sandbox |
| Actual question IDs, broker routing and partial-answer UI behavior | not_checked — no runtime track or questions exist for this package |
| Evidence entails model claims / board validity / model scores | not_checked — no investigator output exists |
| Independent engineering and causal-reference review | not_checked — generator review is not expert validation |

## Measured payload size

Counts include Markdown headers/tables using whitespace-separated words. They are not token counts. Additions include the corrected revision; cumulative active counts exclude superseded revision 1.

| Release | Added revisions | Added words | Added bytes | Active revisions | Active words |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 6 | 975 | 6177 | 6 | 975 |
| B1 | 3 | 614 | 3751 | 9 | 1589 |
| B2 | 4 | 593 | 3890 | 12 | 2092 |

## Generator review and limitations

- pass, self-review: focal event/activity and reported consequences retained; causal hindsight separated in normalized row and ledger.
- pass, self-review: every payload is identified privately as authored; no recovered company log, true signature or real OEM certification is claimed. Source uncertainties and privacy transformations are explicit.
- pass, self-review: fixed entity aliases, relative order, dates, state transitions and document-effective/issue dates cross-checked against the private scenario. Qualitative component motion is separated from geometry and fluid-path evidence. No exact clearance, load capacity or event-time leakage is claimed.
- pass, self-review: main inference requires configuration + state/motion + outcome across original records. Stage-specific expectations were authored before testing this package.
- pass, self-review: limitations in observations are substantive, not stripped simulation notices. A blank field does not become physical absence, and a draft does not become issued guidance.
- pass, self-review: correction changes a specified inference while retaining real observations; early records remain in version history.
- not_checked, independent review: no external reviewer confirmed causal sufficiency, technical geometry/circuit accuracy, interview realism or difficulty.
- not_checked, runtime: actual filesystem/retrieval isolation, app importer compatibility, question/answer mapping and complete input delivery need verification during the future run. Do not infer these from file layout.

The historical row remains preliminary. The user-supplied R3 RCA PDF was additionally consulted for proposed mechanisms; it is not a recovered test record. Qualitative circuit and geometry extensions require independent engineering review. Do not score those targets as validated industrial truth.

Permanent unknowns: liner timing, exact clearances and forces, valve defect origin, exclusive hydraulic cause, concealed restraints and organizational motives. Targets depending on missing delivery, contradictory assumptions or invalid technical details must be `not_testable`, not model failures.

## Validation-tool notes

The initial known-marker pattern matched the IA asset name B17 as if it were release B1; it was corrected to match standalone release labels. An initial export assertion also matched macOS's outer /private path rather than package-relative private content; that assertion was corrected. Neither issue required changing evidence or targets. The final checks and all six case-stage exports passed after these checking errors were corrected.

No claim of zero software defects, model performance, historical proof or production readiness follows from these results.

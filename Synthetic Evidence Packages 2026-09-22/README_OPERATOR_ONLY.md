# Two staged industrial RCA pilot packages

Generated 2026-09-22 using `Try 7/SYNTHETIC_EVIDENCE_PACKAGE_GENERATION_GUIDE.md`, version 1.0.

These are **synthetic reconstructions, not recovered company records**. Keep this notice with any externally shared copy. The investigator-facing documents deliberately omit simulation banners; they must be used only inside an identified evaluation exercise.

| Case | Anchor | Package | Status |
| --- | --- | --- | --- |
| R3-16515 | R3 carrier-beam fall, 2024-10-14 | [Operator guide](R3-16515_evidence_package_v1/README_OPERATOR_ONLY.md) | technical_review_needed |
| IA-16036 | Instrument-air loss during dryer isolation, 2024-05-20 | [Operator guide](IA-16036_evidence_package_v1/README_OPERATOR_ONLY.md) | prepared_for_pilot |

Both use three **cumulative** releases: B0 → investigation V1; B1 → V2; B2 → V3. Package version 1 is not an app investigation version. These packages are new derivatives of already-used development incidents, not independent held-out test cases. Earlier packages, applications, and model outputs were not changed.

The main relationships require combining configuration, state/sequence, and observations. Private targets describe the expected evidential progress, not exact phrases or a required number of nodes. There are no fabricated model scores or completed investigations here.

## Safe use

1. Read the selected case's operator guide and private validation report.
2. For a fresh V1, paste only `payloads/B0/incident_description.md`; upload its default and starter subfolders in their respective app scopes.
3. Stop after V1. Prepare the eligible B1 answers/documents separately, check actual question IDs and parent version, then explicitly run V2. Repeat with B2 for V3.
4. Never upload this root, a whole case folder, a whole `payloads` folder, `private`, manifests, run records, or authoring/validation tools. A payload root contains unreleased evidence.

The provided `package_tools.py` can validate packages and export an allowlisted stage directory to a **new** location. It is an operator utility, not an app importer or an access-control sandbox. The investigator still needs a separate context without access to this workspace. An answer agent receives only an eligible answer-bank subset, never the full bank or scoring key.

No RCA or storyteller jobs have been launched. R3's load-path/circuit reconstruction requires independent technical review before its mechanical conclusions are used for scored claims. IA's discrete connectivity and chronology were checked by the generator; that is not independent expert validation.

## Operator utility examples

Run from this folder with Python 3.9 or later:

```sh
python3 package_tools.py
python3 package_tools.py --case IA-16036 --export B0 --destination /tmp/ia16036-b0-new-export
```

The destination must not already exist and must be outside this authoring package root. Exports contain only evidence, organized by original scope. B1/B2 exports are cumulative active views; the operator must preserve superseded documents in earlier version archives. Do not treat an export as proof of what the app actually ingested. The full answer bank is not exported.

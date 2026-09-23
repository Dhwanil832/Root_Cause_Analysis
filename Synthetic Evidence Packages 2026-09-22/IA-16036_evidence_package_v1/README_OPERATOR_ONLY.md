# IA-16036 — operator guide

Package version: 1.0.0. Status: **prepared_for_pilot**. Generated 2026-09-22 using master guide version 1.0. Anchor: historical incident 16036, instrument-air interruption, 2024-05-20.

These documents are **synthetic reconstructions for controlled evaluation, not authentic company evidence**. Historical observations are preserved; extra states, identifiers, logs, interviews, technical records and document histories are additions tracked in the private ledger. Keep this notice with externally shared copies. Payloads omit simulation banners to avoid turning exercise metadata into incident causes.

## Exact starting inputs

Paste [initial description](payloads/B0/incident_description.md).

Upload as default references:
- [IA-D01_service_directory.md](payloads/B0/default_references/IA-D01_service_directory.md)
- [IA-D02_work_package_practice.md](payloads/B0/default_references/IA-D02_work_package_practice.md)

Upload as incident starter documents:
- [IA-D03_packet_cover.md](payloads/B0/starter_documents/IA-D03_packet_cover.md)
- [IA-D04_pressure_extract.md](payloads/B0/starter_documents/IA-D04_pressure_extract.md)
- [IA-D05_desk_message_r1.md](payloads/B0/starter_documents/IA-D05_desk_message_r1.md)

Only these six files enter V1. B0 is enough for a useful incomplete board, not a required final answer.

## Later batches

After V1 is published, stop its job. Separately prepare the fixed [B1 documents](payloads/B1) or eligible source-faithful answers, bind real questions and parent version, and explicitly run V2. Then do the same with [B2](payloads/B2) for V3. Documents are cumulative except D05 revision 2 supersedes revision 1 in active retrieval at B2; retain the original in V1/V2 history. The manifest lists precise identities and revisions.

| Stage | Intended examination |
| --- | --- |
| B0 → V1 | Establish local pressure loss/recovery, packet identity and an unverified alarm interpretation. |
| B1 → V2 | Combine topology, actual valve actions and trend data; correct signal meaning. |
| B2 → V3 | Compare installed configuration with issued/draft revisions, trace the specific routing gap and correct the trip interpretation. |

This evaluates two supply paths, series bypass valves, measurement/indication meaning and installed-versus-issued instruction status. Permanent limits include crew intent, why the change impact field was No, why the draft remained unissued, complete damage assessment and quantitative air-flow behavior. Success can mean justified uncertainty or a retracted connection, not a larger board.

## Boundaries and status

This is a new three-release derivative of the existing IA-16036 development case. It reuses stable synthetic asset conventions but regroups earlier B0–B3 material into B0–B2. It is not an exact replay of the current app run or a new held-out incident.

The row alone supplies a usable historical anchor, not raw corroboration. Privacy: site aliased to Harbor Works, people reduced to fictional roles, personal/account identifiers omitted, no real signatures/logos. Original asset terminology is retained when useful.

Never upload `private/`, this README, `package_manifest.json`, `run_records/`, the source workbook/PDF, the master guide or the whole package/payload root. Future evidence is on disk but not released. Folder naming is not access control: use a fresh investigator context unable to inspect this workspace. An answering job sees only permitted originals, prior public answers and an eligible bank subset—not the full bank, hidden scenario or evaluation targets.

The manifest is portable operator metadata, **not an app API schema**. An app adapter must preserve defaults/starters/answer attachments, source revisions, partial/conflicting answer coverage and model-specific lineage. No import or RCA run has been performed.

See [validation](private/validation_report.md), [release expectations](private/release_expectations.md), [evaluation targets](private/evaluation_targets.json) and [run protocol](private/run_protocol.md). Self-checks are not expert approval. Scoring method/weights and any human or LLM reviewer must be selected before scored runs.

The parent-folder operator tool can validate these files or create a new release-specific export. It never launches the application. Earlier case inputs and outputs remain unchanged.

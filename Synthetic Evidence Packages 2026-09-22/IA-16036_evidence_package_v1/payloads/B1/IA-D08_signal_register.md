# Utilities indication register extract

Document ID: IA-D08
Revision: 1
Record type: alarm configuration review
Origin: IC-1
Configuration effective: before 2024-05-20 event; exact original label date not recorded
Reviewed and created: 2024-05-20 12:00
Scope: AL44 signal meaning only

## S1 — Mapping

| Field | Configuration |
| --- | --- |
| Alarm ID | AL44 |
| Display label | COMP FAULT |
| Input | P-R low-pressure comparison at H-R |
| Activation threshold | P-R below 5.0 bar gauge |
| Compressor trip contact in this logic | None |

The label was retained when the pressure indication was configured. AL44 can be active because H-R pressure is low without a compressor trip. This mapping does not establish whether a separate trip occurred; that requires a different record.

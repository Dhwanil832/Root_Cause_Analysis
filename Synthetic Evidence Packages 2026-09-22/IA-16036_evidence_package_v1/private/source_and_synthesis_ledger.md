# Source and synthesis ledger

Private. Historical workbook: `Try 1/Background Litrature/Historical Incident data/NearMissSafetyData_2025_01_15_14_08_16 (1).xlsx`; sheet `NearMissSafetyData`; headers row 5; incident row 573. Hash and sanitized original fields are in `normalized_row.json`. Real people/site are replaced by fictional role IDs and Harbor Works. RHOB and 1SC are retained as functional asset identifiers. No internal link is accessed or copied into payloads.

All payload documents are authored reconstructions, not authenticated originals. Prior `IA-16036 Controlled Evidence Package/01_withheld_ground_truth/fixed_case_and_limits.md` was consulted for continuity of this development case, not as a second historical source. This version regroups old B0–B3 ideas into B0–B2 and has its own immutable document identities.

| ID | Atomic statement; origin; exact row field/excerpt where applicable | Qualification / scenario status | Purpose; document; first release |
| --- | --- | --- | --- |
| F01 | Planned 1SC dryer isolation; row_observation; Incident Desc: “lockout #1 slab caster(1SC) dryer air system ... for planned system maintenance and repair” | Reported, fixed | I00/D03; B0 |
| F02 | Crew had lockout paperwork; row_observation; Incident Desc: “brought all necessary paperwork, boxes, locks etc.” | Reported possession, not adequacy | D03; B0 |
| F03 | First of two new bypass valves opened; row_observation; Incident Desc: “opened one of two valves on a newly installed ... bypass” | Fixed, identity/time synthetic | D07; B1 |
| F04 | Main isolation closed; row_observation; Incident Desc: “then closed the main isolation valve” | Fixed; exact clock synthetic | D07; B1 |
| F05 | RHOB pressure lost shortly afterward; row_observation; Incident Desc: “Shortly after ... loss of instrument air pressure” | Fixed | I00/D04; B0 |
| F06 | Second bypass valve found shut; row_observation; Incident Desc: “second valve ... was still shut” | Fixed | D07; B1 |
| F07 | Opening second valve restored pressure; row_observation; Incident Desc: “opened the second bypass isolation valve and instrument air pressure ... was restored” | Historical sequence; synthetic independent channels added | D07 + D04; B1 |
| F08 | ECP not updated; row_interpretation; Root Causal Factor One: “ECP was not updated to reflect 1SC air system bypass line” | Recorded finding, private until evidence supports narrow conclusion | D09–D10; B2 |
| F09 | B17 branches before M101 and returns after M102; synthetic_addition | Fixed traced topology | Distinguish bypass vs downstream valve states; D06; B1 |
| F10 | V201 and V202 are in series with no intermediate source; synthetic_addition | Fixed scope, no OEM claim | Both required for continuous alternative path; D06; B1 |
| F11 | P-U/P-R sample values and timestamps; synthetic_addition | Fixed sampled readings, not exact transient record | Distinguish local interruption from common supply loss; D04; B0 |
| F12 | P-U upstream, P-R receiver header; synthetic_addition | Fixed measurement locations | D01/D04; B0 |
| F13 | AL44 labeled COMP FAULT is driven only by low P-R; synthetic_addition | Fixed configuration | Fair signal interpretation challenge; label D05 B0, map D08 B1 |
| F14 | Desk interprets label as trip without checking journal; synthetic_addition | Disputed account, correction later | D05 rev1 B0, rev2 B2 |
| F15 | M102 remains open, M101 remains closed during restoration; synthetic_addition | Fixed recorded states, not operator intent | D07; B1 |
| F16 | ECP rev3 issued to WO527 at 09:31; synthetic_addition | Fixed documentary availability | D03 B0; D10 B2 |
| F17 | B17 field installation May 16; synthetic_addition | Fixed date chosen consistently with row “newly installed” | D09; B2 |
| F18 | Revision 4-D drafted May 17, unissued; synthetic_addition | Fixed; not proof it reached crew | D10; B2 |
| F19 | CH218 work-package impact No, so no distribution task created; synthetic_addition | Fixed workflow/record; not motive or global governance claim | D02 + D09; B2 |
| F20 | No trip in continuously recorded 09:50–10:10 controller interval; synthetic_addition | Fixed bounded negative record, not “compressors never fail” | D11; B2 |
| F21 | Why V202 was not opened initially; unresolved | No motive/competence evidence | Answer bank unknown entry; B0 onward |
| F22 | Why impact No and draft unissued; unresolved | No decision rationale supplied | Answer bank unknown entry; B2 |
| F23 | Isolation valve closes a flow path; general_background | Principle only; actual paths established by D06 | Private plausibility reference |

Opening notification withholds the retrospective clauses identifying the second shut valve and unupdated ECP. It states the service interruption and later restoration without falsely attributing restoration to a compressor restart. Full narrative remains private for historical traceability.

Synthetic document metadata (roles, record IDs, revision dates, neutral titles and section labels) is authored throughout. Employee identifiers, addresses, demographic fields and account names were removed. Source blanks are not converted into no injury, zero damage or unanimous approval.

Primary general source consulted 2026-09-22: [Festo shut-off valve overview](https://www.festo.com/us/en/c/products/valves-and-valve-manifolds/shut-off-valves-pneumatic-id_pim117), on opening/closing pneumatic supply paths. It establishes no fact about RHOB, the installed valves or regulatory compliance. Discrete connectivity was checked within the fixed topology; no compressor-sizing or pressure-decay calculation is claimed.

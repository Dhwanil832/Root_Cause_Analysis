# Historical anchor — evaluator only

Never supply this file, the source row or its causal-factor fields to the RCA model.

Source file: `Try 1/Background Litrature/Historical Incident data/NearMissSafetyData_2025_01_15_14_08_16 (1).xlsx`, relative to the RCA workspace.

Workbook SHA-256: `bd900c0ff1f6736143a64dfecd3e9c1a0ee7eb8ac32f62a74f8bba830df689f1`

Worksheet: `NearMissSafetyData`; header row 5; selected row 573.

| Field | Cell | Inspected value |
| --- | --- | --- |
| Incident ID | D573 | 16036 |
| Title | E573 | MEUUtil Loss of instrument air to 4SP-RHOB |
| Plant/division/department | A573:C573 | Indiana Harbor / MEU / Utilities |
| Date/time/turn | F573, G573, J573 | 5/20/2024 / 10:00 AM / 2 |
| Report state | K573, M573, N573 | Final / True (case closed) / Non-SIF |
| Location | AJ573 | 4SP-1 Slab Caster |
| Activity | AM573:AO573 | Non-routine Operations / Lockout / Tagout / Lockout / Tagout |

## Source narrative — AL573

> After attending the pre-shift safety briefing, Utilities operations team member was instructed to lockout #1 slab caster(1SC) dryer air system with another team member for planned system maintenance and repair. Team member brought all necessary paperwork, boxes, locks etc. to complete the lockout and proceeded to lockout 1SC air system. In the process of locking out 1SC air system, team member opened one of two valves on a newly installed compressor/dryer system bypass that allows the RHOB to be fed instrument air in the event of a system lockout. Team member then closed the main isolation valve for the 1SC air system header. Shortly after closing the main isolation valve for 1SC air system header, the RHOB experienced a loss of instrument air pressure. Team member began troubleshooting the instrument air system and noticed the second valve that would allow instrument air to be fed to the RHOB was still shut. This newly installed compressor/dryer system bypass was not yet reflected on applicable ECP documents for this lockout. Team member then opened the second bypass isolation valve and instrument air pressure to the RHOB was restored.

## Recorded interpretations

- AQ573, preliminary cause: “ECP was not yet updated to reflect the installation of new 1SC compressor/dryer system bypass line and associated valves”.
- AR573, immediate corrective action: “Update ECP and lockout procedure for 1SC compressor/dryer system”.
- AT573, document review: “ECP/Lockout procedure”.
- BV573, root causal factor one: “Safety Systems - Job procedures (including lockouts) ==> ECP was not updated to reflect 1SC air system bypass line”.
- BW573:CB573 are empty causal-factor fields in this record.

The report's classification is a recorded conclusion, not independent access to the evidence supporting that conclusion. We have not recovered actual pressure traces, drawings, photographs, training records, change records or the ECP itself.

## What was retained and what was invented

Retained: date/time/turn; areas; two-person Utilities assignment; planned dryer-system work; opening one of two new bypass valves; main-isolation closure; receiving-area pressure loss; second valve found shut and opened; pressure restoration; ECP not updated.

Invented: all asset/record/person codes; detailed layout and connectivity; numeric pressures and second-resolution times; alarm alias and false compressor explanation; photograph descriptions; labels and inspection results; authorization status; exact procedure revisions, draft, distribution and change workflow. The complete routing failure in CH-218 is a **synthetic deeper explanation**, not a finding about the actual partner.

The model-visible notification omits the historical report's later investigative findings. It does not contradict them; they are reconstructed as staged observations. No personal names or personal-data columns were extracted into the package.

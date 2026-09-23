# Source and synthesis ledger

Private. Source workbook: `Try 1/Background Litrature/Historical Incident data/NearMissSafetyData_2025_01_15_14_08_16 (1).xlsx`, sheet `NearMissSafetyData`, headers row 5, incident row 180. Supplemental source: `R3 ground truth/IH SIFp- 80HSM_ R3 Carrier Beam Near Miss 10.14.24.pdf`, especially page 3. Source hashes and sanitized row are in `normalized_row.json`.

Every public record is authored for this exercise. Even a record repeating a historical observation is not an authentic recovered inspection or log. `Harbor Works` replaces the real site; people are fictional role identifiers. Original asset names R3, yoke, carrier beam and mill pit are retained because their relationships matter. Personal fields/internal URLs are removed in normalization. The source narrative's approximate 13:03 and structured Incident Time 1:05 PM remain distinct; no timezone or clock reconciliation is fabricated.

| Fact ID | Atomic statement; origin; source | Qualification / scenario status | Purpose, documents, first release |
| --- | --- | --- | --- |
| F01 | Beam and link fell into pit onto sled/scaffold; row_observation; Incident Desc: “fell into the R3 Mill Pit onto the sled and a scaffold platform” | Reported, fixed | Focal event; R3-I00, D03; B0 |
| F02 | Nobody was in pit at fall; row_observation; Incident Desc: “No Team members were working in the pit at the time” | Reported, fixed; not absence of earlier exposure | R3-I00, D03; B0 |
| F03 | Contractors worked in pit earlier; row_observation; Incident Desc: “throughout the morning” | Reported, fixed; anonymized | Exposure scope; D03; B0 |
| F04 | Keeper remained installed; row_observation; Incident Desc: “link were intact with keeper still installed” | Reported, fixed; not a capacity test | Distinguish missing/broken from ineffective geometry; D03; B0 |
| F05 | No apparent yoke damage; row_observation; Incident Desc: “There appeared to be no damage on the yoke” | Visual observation only, fixed | D03; B0 |
| F06 | Small liner fell with beam; row_observation; Incident Desc: “small mill window liner ... fell with the carrier beam” | Fixed occurrence, initiating role unresolved | D03; B0 |
| F07 | No involved crane lifts at/prior to event; row_observation; Incident Desc: “no crane lifts at the time or prior involving this equipment” | Reported absence, fixed; surveillance not exhaustive | D04; B0 |
| F08 | Work/backup rolls removed previous shift; row_observation; Incident Desc: “removed on the previous shift” | Fixed | D04; B0 |
| F09 | Balance left raised; row_observation; Incident Desc: “isolated in the up (raised) position” | Fixed, not verified immobilization | D04; B0 |
| F10 | B hydraulics shut off/bled; row_observation; Incident Desc: “B hydraulics was shutoff and bled” | Fixed description; point location added separately | D04; B0 |
| F11 | Root-factor not settled; row_interpretation; Root Causal Factor One: “Work Environment - Other ==> Still investigating” | Historical unresolved finding, private only | Prevent false historical ground truth; no release |
| F12 | Relative yoke movement while beam remains at housing contact; synthetic_addition informed by PDF p3 “Yoke drifted but carrier beam did not” | Synthetic fixed observations; PDF itself not independent footage | Separate component motion; D06; B1 |
| F13 | Offset link can clear yoke with keeper intact; synthetic_addition informed by PDF p3 keeper/off-center/clearance nodes | Fixed qualitative reconstruction, independent engineering review pending | Geometry rather than fracture; D07; B1 |
| F14 | No travel stop at recorded housing contact when backup rolls absent; synthetic_addition informed by PDF p3 design nodes | Fixed assembly-survey scope; not all mill designs | D07; B1 |
| F15 | Desk operator inferred immobility from header reading, did not view assembly; synthetic_addition | Disputed account, not physical fact | Fair challenge and correction; D05 rev1 B0, rev2 B2 |
| F16 | Header gauge reads outside the load-side volume; synthetic_addition | Fixed circuit/measurement relation, pending technical review | Prevent zero-pressure leap; D04 B0, D09 B2 |
| F17 | IV-R3 passes reverse flow in later workshop observation; synthetic_addition | Fixed later observation, not measured event-time flow rate | Test one plausible drift path; D10; B2 |
| F18 | Closed-handle IV-R3 connects loaded volume to depressurized header in circuit; synthetic_addition | Fixed simplified circuit, not historical drawing | Requires F16–17 plus motion, not valve alone; D09; B2 |
| F19 | Survey sees no independent restraint in accessible region; synthetic_addition | Fixed post-event limited survey; hidden/pre-event details remain unknown | D07; B1 |
| F20 | Issued task record lacks configuration-specific load restraint method; synthetic_addition informed by PDF p3 LOTO nodes | Fixed documentary omission; not proof of no physical block | D11; B2 |
| F21 | General site practice requires identifying gravity load control separately from fluid isolation; synthetic_addition | Fictional applicable practice, not an OEM or legal clause | D02; B0 |
| F22 | Relative-position sample times 11:05, 12:10, 13:02 are synthetic and ±2 min | synthetic_addition; fixed; cannot order liner and release within a second | Supply interpretable observations, D06; B1 |
| F23 | Event time 13:03 narrative versus 13:05 field; unresolved | Retain both; source does not settle difference | I00; B0 |
| F24 | PDF A-hydraulic wording conflicts with row B wording; unresolved | Exercise uses functional labels IV-R3/H-R3, not an asserted real A/B reconciliation | D09; B2 |
| F25 | Gravity-loaded hydraulic devices may drift if load-holding function is lost; general_background | Principle only, not incident proof | Private plausibility reference; no direct scored evidence |

Synthetic metadata (role authors, record creation dates, document IDs/revisions, local marker names and report structure) are authored additions throughout. They organize evidence, not extra historical findings. All public sections are covered by the facts above; exact values absent from the row are synthetic.

The initial notification withholds the retrospective dislodgement verdict and the supplied PDF causal chart. It retains the event and outage context; no hidden raw record is claimed to have been recovered.

Primary general reference consulted 2026-09-22: [Parker E2 counterbalance valve overview](https://discover.parker.com/e2-series-counterbalance-valve), describing load holding against unwanted drift. This supports only general plausibility, not this installed circuit or geometry. The quantitative/mechanical case remains pending independent review.

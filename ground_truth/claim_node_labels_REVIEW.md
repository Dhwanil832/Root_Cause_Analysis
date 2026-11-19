# Claim-to-node labels: review

Draft by Claude, 2026-11-11: all 205 distinct claims from the eight saved runs (the first 50 were a sample; the other 155 were added the same day). Correct the **Nodes** column in `claim_node_labels.json` (the scorer reads that file, not this one).
Fit: **same** = the claim states the node; **part** = it states part of it or one instance; **opposite** = it denies it. Blank = no chart node.

## Chart nodes

| ID | Text |
|---|---|
| G01 | Yoke drifted but carrier beam did not |
| G02 | R3 Backup Raise "isolated" |
| G03 | Keeper installation & location |
| G04 | No stop for carrier beam without backup rolls installed |
| G05 | Carrier beam came off of yoke with the keeper plate still intact (bolted) |
| G06 | Carrier beam wedged on mill spreader and mill posts |
| G07 | Hydraulics shut off with isolation valve slowly bleeding backwards allowing the cylinder fluid to vacate the pipe |
| G08 | carrier beam shifted off of yoke when stored in the upright position due to being wedge against mill beam housing with no "stops" or back up rolls installed |
| G09 | NO mechanism to prevent carrier beams from being wedged |
| G10 | carrier beam shifted |
| G11 | Excess Clearance????? Measurements do not allow for clearance to get over the yoke "in resting position" |
| G12 | Original Mill Design |
| G13 | R3 Hydraulic Isolation valve has slow bleed through |
| G14 | Isolation valves are not routinely inspected but rather replaced when found defective |
| G15 | J. Tessling "not required" |
| G16 | R3 LOTO- Task Specific Procedure "Stripper Box Changeout" |
| G17 | Stored Energy not accounted for "A" hydraulics |
| G18 | All energy sources (gravity) not accounted for during isolation for task |
| G19 | Only one keeper installed |
| G20 | Original Mill Design (keeper) |
| G21 | Original Mill Design (no stop) |
| G22 | ? |

## Labels, grouped by first node

| # | Claim | Nodes | Why |
|---|---|---|---|
| 1 | Hydraulic yokes were engaged at the time of the fall. | G01 opposite, G07 opposite | yokes holding the carrier denies the yoke drift and the hydraulic loss |
| 2 | It is uncertain whether the RB‑3 delivery carrier was supported by hydraulic lifting yokes during the outage arrangement. | G01 part | a question about whether the yoke held the carrier |
| 3 | Lowering the yoke relative to an outward link‑arm offset pose permits loss of mechanical engagement between the carrier and its support. | G01 part | yoke out of line with the link arm is the yoke drifting from the carrier |
| 4 | The RB-3 delivery carrier was not supported by hydraulic lifting yokes during the outage arrangement. | G01 part, G07 part | yoke not holding the carrier; hydraulic support lost |
| 5 | The RB-3 delivery carrier was supported by hydraulic lifting yokes during the outage arrangement. | G01 opposite, G07 opposite | yokes holding the carrier denies the yoke drift and the hydraulic loss |
| 6 | The yoke was misaligned relative to the link arm during outage, potentially compromising support. | G01 part | yoke out of line with the link arm is the yoke drifting from the carrier |
| 7 | Carrier was unsecured by hydraulics due to valve isolation and roll removal. | G02 part, G04 part, G07 part | valve isolated, rolls out and no hydraulic hold |
| 8 | Hydraulic isolation valve IV-RB3-17 was closed during guide-box preparation. | G02 part | valve closed is the backup raise being 'isolated' |
| 9 | Hydraulic isolation valve IV-RB3-17 was closed or sealed during the event. | G02 part, G13 opposite | closed is the 'isolated' raise; sealed denies the bleed-through |
| 10 | Isolation valve IV-RB3-17 status unknown at time of fall | G02 part | a question about whether the raise was isolated |
| 11 | Isolation valve IV-RB3-17 was not closed or isolated before the carrier was raised. | G02 opposite | valve not closed denies the 'isolated' raise |
| 12 | Local hydraulic isolation was performed at valve tag IV-RB3-17 during guide-box preparation. | G02 part | valve closed is the backup raise being 'isolated' |
| 13 | Local hydraulic isolation was recorded as closed at 10:47 on Day 0. | G02 part | valve closed is the backup raise being 'isolated' |
| 14 | Local isolation at valve IV-RB3-17 recorded; could have caused loss of hydraulic pressure in carrier yokes. | G02 part, G07 part | valve closed is the backup raise being 'isolated' |
| 15 | Local isolation recorded at valve tag IV-RB3-17. | G02 part | valve closed is the backup raise being 'isolated' |
| 16 | Local isolation valve IV-RB3-17 was closed during outage | G02 part | the valve closed is the backup raise being 'isolated' |
| 17 | Local isolation valve IV-RB3-17 was closed during the outage. | G02 part | valve closed is the backup raise being 'isolated' |
| 18 | Local isolation valve IV-RB3-17 was recorded closed at 10:47 on Day 0. | G02 part | valve recorded closed is the 'isolated' raise |
| 19 | Status of hydraulic isolation valve IV-RB3-17 during the event is unknown. | G02 part | a question about whether the raise was isolated |
| 20 | The hydraulic isolation valve IV-RB3-17 was checked to be closed at 10:47 during guide-box preparation. | G02 part | valve closed is the backup raise being 'isolated' |
| 21 | The hydraulic isolation valve status at the time of the fall is unknown. | G02 part | a question about whether the raise was isolated |
| 22 | The hydraulic isolation valve was checked closed at 10:47 on Day 0. | G02 part | valve closed is the backup raise being 'isolated' |
| 23 | The hydraulic isolation valve was closed at the time of the carrier fall. | G02 part | valve closed is the backup raise being 'isolated' |
| 24 | The hydraulic isolation valve was closed at the time of the fall. | G02 part | valve closed is the 'isolated' raise |
| 25 | The hydraulic isolation valve was not closed at the time of the fall. | G02 opposite | valve not closed denies the 'isolated' raise |
| 26 | The isolation handle of valve IV-RB3-17 was in the closed position during the event. | G02 part | handle closed is the 'isolated' raise |
| 27 | The local hydraulic isolation valve IV-RB3-17 was recorded as closed at 10:47, but no sealing test result or pressure verification was performed. | G02 part, G17 part | pressure on the isolated side not checked: stored energy not accounted for |
| 28 | The local isolation valve IV-RB3-17 was recorded as closed at 10:47, but no sealing test result or pressure verification was performed. | G02 part, G17 part | pressure on the isolated side not checked: stored energy not accounted for |
| 29 | The local isolation valve IV-RB3-17 was sealed and closed during the outage arrangement. | G02 part, G13 opposite | valve closed is the backup raise being 'isolated' |
| 30 | Valve IV-RB3-17 was isolated during the event. | G02 part | valve isolated |
| 31 | Valve IV-RB3-17 was isolated/closed during the raise. | G02 part | valve closed is the backup raise being 'isolated' |
| 32 | Valve IV-RB3-17 was open during the event. | G02 opposite | valve not closed denies the 'isolated' raise |
| 33 | Valve workshop found seepage with the isolation handle at closed. | G13 same, G02 part | valve workshop seepage at closed handle is the slow bleed-through |
| 34 | Keeper plate engaged with link arm during raise. | G03 part | keeper engagement is about keeper installation and location |
| 35 | Keeper plate lost contact with yoke during outage, removing mechanical restraint. | G03 part | keeper engagement is about keeper installation and location |
| 36 | Keeper plate was disengaged from link arm during outage. | G03 part | keeper engagement is about keeper installation and location |
| 37 | Keeper plate was engaged on the link arm during carrier raise. | G03 part | keeper engagement |
| 38 | Keeper plate was not engaged on the link arm during carrier raise. | G03 part | keeper engagement |
| 39 | The keeper plate on the link arm lost contact with the yoke during outage, removing mechanical restraint. | G03 part | keeper engagement is about keeper installation and location |
| 40 | The keeper plate on the link arm was not engaged with the yoke during the event. | G03 part | keeper not engaged is keeper installation and location |
| 41 | A restraint pin or block was not secured to prevent carrier movement. | G18 part, G04 part | no pin, block or crib: gravity not accounted for, nothing stopping the carrier |
| 42 | A restraint pin or block was unsecured, allowing carrier movement. | G18 part, G04 part | no pin, block or crib: gravity not accounted for, nothing stopping the carrier |
| 43 | A restraint pin, block, or crib intended to limit carrier travel into the pit was absent or failed to restrain the carrier. | G18 part, G04 part | no pin, block or crib: gravity not accounted for, nothing stopping the carrier |
| 44 | An outage arrangement may remove components that delimit the normal travel envelope. | G04 part | general mechanism behind 'no stop without backup rolls' |
| 45 | Backup rolls provided mechanical restraint on the carrier. | G04 part | general mechanism behind 'no stop without backup rolls' |
| 46 | Backup rolls removal completed at 10:20 on Day 0. | G04 part | rolls out is the condition of G04 |
| 47 | Backup rolls removal did not eliminate all mechanical restraint on the carrier because other restraints remained in place. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 48 | Backup rolls removal increased upper travel limit beyond design tolerance. | G04 part | rolls out lets the carrier travel too far |
| 49 | Backup rolls removal may have partially removed mechanical restraint on the carrier. | G04 part | general mechanism behind 'no stop without backup rolls' |
| 50 | Backup rolls were present at the time of the fall. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 51 | Backup rolls were removed at 06:35 on Day 0. | G04 part | rolls out, with a time |
| 52 | Backup rolls were removed before the carrier left the upper opening. | G04 part | rolls out is the condition of G04 |
| 53 | Backup rolls were removed before the raise. | G04 part | rolls out is the condition of G04 |
| 54 | Backup rolls were removed during outage | G04 part | rolls out is the condition of G04 |
| 55 | Backup rolls were removed during the outage. | G04 part | rolls out is the condition of G04 |
| 56 | Backup rolls were removed from RB-3 during outage. | G04 part | rolls out is the condition of G04 |
| 57 | Backup rolls were removed from RB‑3 during the outage. | G04 part | rolls out is the condition of G04 |
| 58 | Backup rolls were removed from the carrier assembly at or before the time of the fall. | G04 part | rolls out |
| 59 | Backup rolls were removed from the carrier assembly before 10:42 on Day 0. | G04 part | rolls out is the condition of G04 |
| 60 | Backup rolls were removed from the carrier assembly during outage work. | G04 part | rolls out is the condition of G04 |
| 61 | Backup rolls were removed from the carrier assembly prior to 10:42 on Day 0. | G04 part | rolls out is the condition of G04 |
| 62 | Backup rolls were removed from the carrier assembly prior to guide-box work. | G04 part | rolls out is the condition of G04 |
| 63 | Backup rolls were removed from the carrier assembly prior to the top roll balance being raised for guide‑box clearance. | G04 part | rolls out, ordered with the balance raise |
| 64 | Backup rolls were removed from the carrier at 06:35. | G04 part | rolls out is the condition of G04 |
| 65 | Backup rolls were removed from the carrier at 10:20. | G04 part | rolls out is the condition of G04 |
| 66 | Backup rolls were removed from the carrier before the fall. | G04 part | rolls out is the condition of G04 |
| 67 | Backup rolls were removed prior to the event. | G04 part | rolls out is the condition of G04 |
| 68 | Carrier exceeded its upper travel envelope during the raise. | G06 part, G04 part | going past the upper envelope is how it reached and wedged on the housing; possible because nothing stops it |
| 69 | Carrier had no mechanical restraint due to roll removal during raise. | G04 same | no restraint with the rolls out is 'no stop without backup rolls' |
| 70 | Mechanical engagement between the carrier and its support was lost due to removal of backup rolls or absence of hydraulic support. | G08 part, G04 part, G07 part | carrier losing its support is it shifting off the yoke, through rolls out or hydraulics lost |
| 71 | Other restraints (temporary scaffold, equipment sled) were present at the pit opening during the event. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 72 | Other restraints remained on the carrier after backup roll removal. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 73 | Pit opening was not restricted by backup rolls at the time of the event. | G04 part | rolls out is the condition of G04 |
| 74 | Pit opening was not restricted by backup rolls or other restraints. | G04 same | nothing stopping the carrier with the rolls out |
| 75 | Pit opening was not restricted by other restraints (e.g., temporary scaffold, equipment sled) at the time of the event. | G04 part | rolls out is the condition of G04 |
| 76 | Pit opening was restricted by backup rolls at the time of the event. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 77 | Pit opening was restricted by other restraints (e.g., temporary scaffold, equipment sled) during the event. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 78 | Removal of backup rolls allowed the RB-3 delivery carrier to rise beyond its normal travel envelope. | G04 part | general mechanism behind 'no stop without backup rolls' |
| 79 | Removal of backup rolls eliminated mechanical restraint on the carrier. | G04 same | nothing stopping the carrier with the rolls out |
| 80 | Restraint control (pin, block or crib) was installed and functioning before the fall. | G04 opposite, G18 opposite | restraint fitted denies both 'no stop' and gravity unaccounted |
| 81 | Restraint control (pin, block or crib) was not installed or failed during the outage. | G18 part, G04 part | no pin, block or crib: gravity not accounted for, nothing stopping the carrier |
| 82 | Restraint pin, block, or crib was not installed during preparation. | G18 part, G04 part | no pin, block or crib: gravity not accounted for, nothing stopping the carrier |
| 83 | Support structure for the RB-3 delivery carrier was removed or compromised during outage. | G04 part | rolls out is the condition of G04 |
| 84 | Support structure for the RB‑3 delivery carrier was intact during the outage. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 85 | Support structures for the carrier were compromised or removed prior to the fall. | G04 part | rolls out is the condition of G04 |
| 86 | The beam falling into the pit and striking an equipment sled and temporary scaffold indicates that those restraints were present at the pit opening during the event. | G04 opposite | says a stop or restraint was there, denying 'no stop' |
| 87 | The carrier overtraveled due to loss of support structures. | G06 part, G04 part | overtravel from lost support: past the limit with no stop |
| 88 | The geometry of the carrier assembly exceeded design tolerances during outage due to removal of components that delimit the normal travel envelope. | G04 part, G11 part | components removed from the envelope (no stop) and geometry outside tolerance (clearance) |
| 89 | The interviewee stated that no pin, block, or crib was installed during preparation. | G18 part, G04 part | no restraint fitted |
| 90 | The normal operating arrangement includes the backup rolls. | G04 part | general mechanism behind 'no stop without backup rolls' |
| 91 | The removal of backup rolls occurred prior to 10:42 on Day 0, the time when the top roll balance was raised for guide‑box clearance. | G04 part | rolls out is the condition of G04 |
| 92 | The removal of backup rolls was verified by inspection or documentation after removal. | G04 part | rolls out is the condition of G04 |
| 93 | The restraint pin, block, or crib was not installed during preparation. | G18 part, G04 part | no pin, block or crib: gravity not accounted for, nothing stopping the carrier |
| 94 | Upper travel limit of the carrier was lost due to backup rolls removal | G04 part | general mechanism behind 'no stop without backup rolls' |
| 95 | Keeper plate contact surfaces were intact prior to event. | G05 part | keeper intact |
| 96 | Keeper plate remained attached to link arm after fall | G05 part | keeper still attached after the fall |
| 97 | Recovered link arm inspection shows keeper plate bolted and no gross fracture. | G05 part | keeper still bolted or intact |
| 98 | The keeper plate may have been displaced relative to the link arm during the carrier fall, but was not fractured. | G05 part | keeper still bolted or intact |
| 99 | The keeper plate on the link arm may have been broken or displaced at time of fall. | G05 opposite | keeper unbolted or broken denies 'keeper plate still intact' |
| 100 | The keeper plate remained attached and not fractured at the time of the carrier fall. | G05 part | keeper still bolted or intact |
| 101 | The keeper plate remained bolted to the link arm after recovery of the carrier assembly. | G05 part | keeper still bolted or intact |
| 102 | The keeper plate remained bolted to the link arm after recovery. | G05 part | keeper still bolted |
| 103 | The keeper plate remained bolted to the link arm at the time of the fall. | G05 part | keeper still bolted or intact |
| 104 | The keeper plate remained bolted to the recovered link arm. | G05 part | keeper still bolted |
| 105 | The keeper plate was bolted to the link arm at the time of the carrier fall. | G05 part | keeper still bolted or intact |
| 106 | The keeper plate was bolted to the link arm at the time of the fall. | G05 part | keeper still bolted |
| 107 | The keeper plate was not broken or displaced at the time of the carrier fall. | G05 part | keeper still bolted or intact |
| 108 | The keeper plate was unbolted from the link arm at the time of the fall. | G05 opposite | keeper unbolted or broken denies 'keeper plate still intact' |
| 109 | The status of the keeper plate bolting after recovery is unknown. | G05 part | keeper still bolted or intact |
| 110 | A camera observation at 13:02:58 shows the carrier had not yet exceeded its upper travel limit, contradicting a claim that it did so during guide‑box preparation. | G06 opposite | says it had not passed the limit, denying the beam held at the housing |
| 111 | Camera observation indicates carrier exceeded upper travel envelope. | G06 part | past the upper limit, held at the housing |
| 112 | Carrier assembly exceeded its upper travel limit. | G06 part | past the upper limit, held at the housing |
| 113 | Carrier exceeded its upper travel limit at the time of the fall. | G06 part | past the upper limit, held at the housing |
| 114 | Carrier left upper opening due to overtravel is uncertain. | G10 part, G06 part | leaving the opening by overtravel: the beam shifting past the limit |
| 115 | Carrier moved beyond its upper travel limit during the event. | G06 part | past the upper limit, held at the housing |
| 116 | Carrier reached its upper travel limit during the event. | G06 part | past the upper limit, held at the housing |
| 117 | Carrier reached upper travel limit during raise. | G06 part | reaching the upper limit is the beam held at the housing |
| 118 | Evidence from camera observations indicates the RB‑3 delivery carrier exceeded its upper travel limit during guide‑box preparation. | G06 part | past the upper limit, held at the housing |
| 119 | It is uncertain whether the carrier exceeded its upper travel limit at the time of the fall. | G06 part | past the upper limit, held at the housing |
| 120 | Oblique camera observation shows the upper carrier against the housing at 11:03, indicating it reached its upper travel limit. | G06 part | carrier against the housing |
| 121 | The carrier assembly exceeded the upper travel limit during guide‑box preparation, but it is not yet confirmed whether this occurred before or after removal of backup rolls and/or loss of hydraulic support. | G06 part | past the upper limit, held at the housing |
| 122 | The carrier assembly exceeded the upper travel limit during guide‑box preparation. | G06 part | past the upper limit, held at the housing |
| 123 | The carrier exceeded its upper travel limit before falling. | G06 part | past the upper limit, held at the housing |
| 124 | The upper carrier edge contacts the housing at the time of the fall. | G06 part | carrier against the housing |
| 125 | Upper carrier edge contacted the housing at the pit opening. | G06 part | carrier against the housing |
| 126 | Upper carrier edge contacts housing during event. | G06 part | carrier against the housing |
| 127 | Branch hydraulic pressure was present prior to the fall. | G07 opposite | pressure present denies the hydraulic loss |
| 128 | Camera observation indicates no branch hydraulic pressure visible, suggesting low or lost pressure in carrier yokes. | G07 part | lost yoke pressure is part of hydraulics losing the cylinder fluid |
| 129 | Common B hydraulic supply shutdown and isolation during the outage arrangement indicates that hydraulic support was unavailable for the RB‑3 delivery carrier. | G07 part | B supply shut down, so the hydraulics were off |
| 130 | Common B hydraulic supply was shut down and isolated during the outage arrangement, indicating that hydraulic support was unavailable for the RB‑3 delivery carrier. | G07 part | B supply shut down, so the hydraulics were off |
| 131 | Common B hydraulic supply was shut down and isolated during the outage. | G07 part | B supply shut down, so the hydraulics were off |
| 132 | Hydraulic pressure in carrier lifting system lost at time of fall | G07 part | lost yoke pressure is part of hydraulics losing the cylinder fluid |
| 133 | Hydraulic pressure in the carrier yokes was low or lost at time of fall. | G07 part | lost yoke pressure is part of hydraulics losing the cylinder fluid |
| 134 | Hydraulic pressure in the yoke system was low at time of raise. | G07 part | low yoke pressure is part of hydraulics losing fluid |
| 135 | Hydraulic pressure in the yoke system was nominal at the time of raise. | G07 opposite | pressure present denies the hydraulic loss |
| 136 | Hydraulic pressure in the yokes was low during the outage. | G07 part | low yoke pressure is part of hydraulics losing the cylinder fluid |
| 137 | Hydraulic pressure loss in the yoke system occurred during the event. | G07 part | lost yoke pressure is part of hydraulics losing the cylinder fluid |
| 138 | Hydraulic yokes were not engaged or had lost pressure during the outage. | G07 part | yokes lost pressure |
| 139 | It is uncertain whether hydraulic pressure in the carrier yokes was low or lost at time of fall. | G07 part | a question about the hydraulic loss |
| 140 | Low hydraulic pressure in the carrier yokes may cause the carrier to overtravel. | G07 part | a question about the hydraulic loss |
| 141 | The cause of hydraulic pressure loss in the carrier yokes at time of fall is unknown. | G07 part | a question about the hydraulic loss |
| 142 | There was a drop in hydraulic pressure in the lifting yokes at the time of the fall. | G07 part | lost yoke pressure is part of hydraulics losing the cylinder fluid |
| 143 | There was no hydraulic pressure drop in the lifting yokes at the time of the fall. | G07 opposite | denies the hydraulic loss |
| 144 | Valve IV-RB3-17 sealing condition unknown; lack of evidence for seal may indicate loss of pressure. | G13 part, G07 part | a question about whether the valve bled through |
| 145 | Carrier was left in a high position for guide-box clearance. | G08 part | left high is the beam stored in the upright position |
| 146 | Carrier was not raised above the upper opening before falling | G08 opposite | denies the beam being stored raised |
| 147 | Carrier was raised above the upper opening before falling | G08 part | left raised is the beam stored in the upright position |
| 148 | Interview statement indicates the carrier was left in a high position for guide-box clearance. | G08 part | left raised is the beam stored in the upright position |
| 149 | Interviewee stated the assembly was left in a raised position. | G08 part | left raised is stored upright |
| 150 | The RB-3 delivery carrier remained raised until 13:03 on Day 0. | G08 part | left raised is the beam stored in the upright position |
| 151 | The RB-3 delivery carrier was in a raised position at the time of the fall. | G08 part | left raised is the beam stored in the upright position |
| 152 | The RB-3 delivery carrier was in a raised position prior to the fall. | G08 part | stored raised |
| 153 | The RB-3 delivery carrier was not in a raised position at the time of the fall. | G08 opposite | denies the beam being stored raised |
| 154 | The RB-3 delivery carrier was raised at 10:42 on Day 0. | G08 part | left raised is the beam stored in the upright position |
| 155 | The RB‑3 delivery carrier remained in a raised position at the time of the fall. | G08 part | left raised is the beam stored in the upright position |
| 156 | The RB‑3 delivery carrier was at the upper opening of its travel envelope at the time of the fall. | G08 part | left raised is the beam stored in the upright position |
| 157 | The RB‑3 delivery carrier was in a raised position at 13:02:58. | G08 part | left raised is the beam stored in the upright position |
| 158 | Camera observation indicates the carrier left its upper opening before falling. | G10 part | the carrier leaving the opening is the beam shifting |
| 159 | Carrier left the upper opening during the event. | G10 part | the carrier leaving the opening is the beam shifting |
| 160 | Carrier left upper opening of roughing‑stand pit at approximately 13:03 | G10 part | the carrier leaving the opening is the beam shifting |
| 161 | The RB-3 delivery carrier left the upper opening at approximately 13:03 on Day 0. | G10 part | the carrier leaving the opening is the beam shifting |
| 162 | The RB-3 delivery carrier left the upper opening of the roughing‑stand pit at approximately 13:03. | G10 part | the carrier leaving the opening is the beam shifting |
| 163 | The RB-3 delivery carrier moved beyond the normal support envelope during outage. | G10 part | the carrier moving out of its envelope is the beam shifting |
| 164 | The RB‑3 delivery carrier left the upper opening at 13:03:02. | G10 part | the carrier leaving the opening is the beam shifting |
| 165 | The RB‑3 delivery carrier left the upper opening before the fall event. | G10 part | the carrier leaving the opening is the beam shifting |
| 166 | Geometry worksheet indicates that at the centred‑resting position, overlap prevents the link arm from passing the keeper/yoke interface. | G11 part | the worksheet says the measurements leave no clearance over the yoke at rest |
| 167 | Hydraulic isolation valve IV-RB3-17 was not closed or sealed during the event. | G02 opposite, G13 part | valve not closed denies the 'isolated' raise |
| 168 | Local valve IV-RB3-17 was not properly sealed at the time of the carrier fall. | G13 same | not properly sealed is a slow bleed-through |
| 169 | The local isolation valve IV-RB3-17 sealing status at the time of the outage arrangement is unverified. | G13 part | a question about whether the valve bled through |
| 170 | The sealing condition of valve IV-RB3-17 at the time of the fall is unknown. | G13 part | a question about whether the valve bled through |
| 171 | Hydraulic isolation checklist was completed for the guide-box work on Day 0. | G16 part | isolation checklist is the task-specific LOTO procedure |
| 172 | Hydraulic isolation checklist was not completed for the guide-box work on Day 0. | G16 part | isolation checklist is the task-specific LOTO procedure |
| 173 | Isolation checklist for valve IV-RB3-17 was completed before the raise. | G16 part | isolation checklist is the task-specific LOTO procedure |
| 174 | The issued guide-box work pack did not include a field for a fitted pin, block, or crib to restrain the carrier during removal of backup rolls. | G16 part, G18 part | task procedure lacked a restraint step: gravity not accounted for |
| 175 | Branch hydraulic pressure was not measured or recorded during the outage arrangement. | G17 part | pressure on the isolated side not checked: stored energy not accounted for |
| 176 | Outage switching sheet does not record pressure on isolated cylinder side of valve IV-RB3-17. | G17 part | pressure on the isolated side not checked: stored energy not accounted for |
| 177 | Mechanical restraint field missing pin or block in work pack | G18 part | no restraint in the work pack: gravity not accounted for in the isolation |
| 178 | Backup rolls removal was documented in handover record. | — | a record of handover documentation; no chart node |
| 179 | Branch hydraulic pressure was not observed during the event. | — | a record that pressure was not observed; no chart node |
| 180 | Branch hydraulic pressure was not visible on the RB‑3 delivery carrier during the outage arrangement. | — | a statement about what a record or sensor holds; no chart node |
| 181 | External vibration or movement contributed to carrier displacement. | — | an outside cause the chart does not name |
| 182 | Handover between shift operations and maintenance work team was completed before the carrier fell. | — | handover or work coordination; the chart has no such node |
| 183 | Handover between shift operations and maintenance work team was completed before the carrier left the upper opening. | — | handover or work coordination; the chart has no such node |
| 184 | Handover between shift operations and maintenance work team was incomplete. | — | handover or work coordination; the chart has no such node |
| 185 | Handover documentation did not capture the removal of backup rolls or the carrier’s high position status at the time of the event. | — | handover or work coordination; the chart has no such node |
| 186 | Handover entry did not record keeper contact inspection | — | about an inspection or record of the keeper, not its installation; no chart node |
| 187 | Keeper plate contact surfaces were inspected prior to raise. | — | about an inspection or record of the keeper, not its installation; no chart node |
| 188 | No branch hydraulic pressure was visible in camera footage at the time of the fall. | — | a statement about what a record or sensor holds; no chart node |
| 189 | No hydraulic pressure measurement was recorded at the time of the carrier fall. | — | a statement about what a record or sensor holds; no chart node |
| 190 | No sensor channel measuring flow through valve IV-RB3-17 was configured in the exported historian set at the time of the fall. | — | a statement about what a record or sensor holds; no chart node |
| 191 | Observer did not inspect keeper contact surfaces. | — | about an inspection or record of the keeper, not its installation; no chart node |
| 192 | Pressure on the isolated cylinder side of valve IV-RB3-17 was measured during the event. | — | a statement about what a record or sensor holds; no chart node |
| 193 | Pressure on the isolated cylinder side of valve IV-RB3-17 was not recorded during the event. | — | a statement about what a record or sensor holds; no chart node |
| 194 | Pressure on the isolated cylinder side of valve IV-RB3-17 was not recorded in any system during the event. | — | a statement about what a record or sensor holds; no chart node |
| 195 | Source documents indicate no pressure record on the isolated cylinder side of valve IV-RB3-17 during the event. | — | a statement about what a record or sensor holds; no chart node |
| 196 | The handover between previous-turn and day-turn did not include all necessary carrier configuration details. | — | handover or work coordination; the chart has no such node |
| 197 | The handover record did not accurately capture the removal of backup rolls before the fall. | — | handover or work coordination; the chart has no such node |
| 198 | The handover record did not capture removal of backup rolls before the fall. | — | handover or work coordination; the chart has no such node |
| 199 | The handover record does not identify the final upper‑travel limit in the rolls‑out configuration. | — | about an inspection or record of the keeper, not its installation; no chart node |
| 200 | Upper travel limit not documented in handover record. | — | about an inspection or record of the keeper, not its installation; no chart node |
| 201 | Work coordination between shift operations and maintenance failed to ensure the carrier remained in a safe position during guide-box preparation. | — | work coordination failure; the chart has no such node |
| 202 | Work coordination between shift operations and maintenance was incomplete or ineffective during the outage. | — | handover or work coordination; the chart has no such node |
| 203 | Work coordination between the outage coordinator, shift supervisor, and maintenance records was incomplete or not documented for the guide-box work on Day 0. | — | handover or work coordination; the chart has no such node |
| 204 | Work coordination for the guide-box replacement was incomplete or not performed. | — | handover or work coordination; the chart has no such node |
| 205 | Work coordination for the guide-box replacement was performed and documented. | — | handover or work coordination; the chart has no such node |

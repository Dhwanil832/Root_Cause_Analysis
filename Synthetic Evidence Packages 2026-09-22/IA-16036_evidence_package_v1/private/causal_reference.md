# Private causal reference

| Node | Plain statement / role | Evidence / first stage | Qualification |
| --- | --- | --- | --- |
| N1 | RHOB service-header pressure falls / event | I00 S1, D04 S1; B0 | Measured header, not all plant supply |
| N2 | Common supply remains near 7 bar at listed samples / condition | D04 S1, D01 S2; B0 | Gaps do not exclude every transient |
| N3 | Closing M101 interrupts the normal path / action and function | D06 S1 + D07 S1; B1 | M102 open does not bypass M101 |
| N4 | B17 has two series valves and V202 remains closed / configuration/condition | D06 S1 + D07 S1; B1 | V201 open alone is insufficient |
| N5 | Neither traced path supplies H-R during interruption / inferred mechanism | D06 + D07 + D04; B1 | Requires N3 AND N4; do not calculate decay rate |
| N6 | Opening V202 restores a continuous alternate path while M101 stays closed / action/mechanism | Same bundle; B1 | Followed by recovery, not proof of every demand condition |
| N7 | AL44 indicates low P-R rather than compressor trip / context | D05 rev1 S1 + D08 S1; B1 | Alarm occurrence remains real |
| N8 | Issued rev3 omits installed B17 configuration / documentary condition | D03 S1 + D09 S1 + D10 S1–S2; B2 | Does not establish worker's internal reasoning |
| N9 | CH218's impact selection leaves ECP routing task uncreated / control condition | D02 S2 + D09 S1–S2; B2 | Scope limited to this routing record |
| N10 | Draft rev4-D was not in the issued packet / context | D10 S1–S2; B2 | Existence is not availability or use |

## Connections

| Link | Relation / joint prerequisites | Required bundle | Qualification / test |
| --- | --- | --- | --- |
| L1 | N3 AND N4 → N5: both normal and auxiliary paths interrupted | D06 S1 AND D07 S1 | Each condition alone is not independently sufficient if the other path is open |
| L2 | N5 → N1: no continuous supply to drawing service header | D06 S1 AND D07 S1 AND D04 S1 | Timing + topology, not mere precedence; unknown receiver volume/consumption |
| L3 | N6 → recovery of N1: opens series bypass with upstream valve already open | Same three records | Main path remains closed, so “main valve reopened” is incorrect |
| L4 | N9 → absence of distribution task: workflow conditional not triggered | D02 S2 AND D09 S1–S2 | Does not prove motive behind No |
| L5 | N8 + N10 → work packet lacks current bypass guidance | D03 S1 AND D09 S1 AND D10 S1–S2 | Supported information/control gap; not proof a complete procedure guarantees compliance |
| L6 | Work packet gap contributes to unverified supply-path preparation | Prior bundle AND D07 S2 | Calibrated contributor consistent with historical finding; no direct proof of cognitive cause or intent |

No independent alternative bundle is asserted for L1–L3. N7 is not a physical barrier and cannot interrupt air. Its wrong interpretation misdirects diagnosis, not the original supply. D11 weakens compressor-trip explanation only for recorded interval, not all hypothetical compressor deficiencies. No speculation about negligence, safety culture or unrecorded downstream damage.

Expected revision: B1 replace label-based trip assertion with low downstream pressure and supported interrupted-path explanation. B2 explicitly preserve original message and its corrected inference, narrow continuous-trip alternative, distinguish draft from issued rev3 and add the specific change/document link. Do not merely rename nodes.

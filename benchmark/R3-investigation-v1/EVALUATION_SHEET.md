# Frozen R3 stage evaluation sheet

Version 1. 96 checks, one point each. Equivalent supported meanings earn credit. New model results are unscored. See PROTOCOL.md for exact input modes, stage windows and failure attribution.

## S01 — Incident understanding

Role in clean test: intake. Evidence band: initial. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S01.01 | Retain the carrier fall into the pit onto sled/scaffold as the focal occurrence | D01.S01 | Treat a proposed cause as the observed focal event | S01-A |
| S01.02 | Identify the raised, backup-roll-removed maintenance configuration | D01.S01; D02.S01 | Use normal rolling configuration without qualification | S01-A |
| S01.03 | Use C17/V17 tags to resolve A/B naming ambiguity | D04.S02 | Assign a circuit from its A/B nickname alone | S01-A |
| S01.04 | Distinguish CLOSED indication from hydraulic sealing | D02.S03 | Confirm tight isolation from handle position | S01-A |
| S01.05 | Distinguish electrical isolation from positive mechanical restraint | D02.S06 | Conclude electrical isolation removed gravity | S01-A |
| S01.06 | Identify D15 as an unreviewed interpretation with no independent corroboration | D15.S01; D15.S02; D15.S03 | Count repeated interpretation as a new observation | S01-A |
| S01.07 | Keep actual block presence unknown from the procedure alone | D04.S03 | Infer actual no-block execution from the omitted instruction | S01-A |
| S01.08 | Prioritize incident motion and actual isolation/restraint clarification | D01.S03; D02.S04; D04.S03 | Begin with unrelated organizational questions or claim complete causal closure | S01-A |

## S02 — Mechanism hypotheses

Role in clean test: specialist. Evidence band: initial. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S02.01 | Propose fluid loss permitting loaded yoke descent as a conditional mechanism | D02.S02 | Confirm incident leakage before incident records arrive | S02-H |
| S02.02 | Keep V17 seat leakage, external loss and alternate paths as distinguishable hydraulic candidates | D02.S02; D02.S03 | Treat every fluid-loss route as the same proposition | S02-H |
| S02.03 | Specify incident flow/boundary evidence that distinguishes hydraulic paths | D02.S02; D01.S03 | Ask only whether the valve was CLOSED | S02-H |
| S02.04 | Include restraint/load premises when testing fluid-loss contribution | D02.S02; D02.S06 | Treat valve leakage alone as sufficient for the full fall | S02-H |
| S02.05 | Test relative yoke/carrier motion rather than yoke travel alone | D02.S04; D02.S05 | Assume a moving yoke necessarily withdraws from a following carrier | S02-M |
| S02.06 | Keep primary seating loss separate from keeper-release mode | D02.S05 | Equate reaching the primary threshold with proof of keeper bypass | S02-M |
| S02.07 | Propose distinct offset, rotation or deformation/geometry candidates for keeper release | D02.S05; D01.S02 | Confirm one release mode from the fall or recovered attachment | S02-M |
| S02.08 | Request time/configuration-relevant contact and keeper geometry evidence | D02.S04; D02.S05 | Use an intact keeper alone to rule out dynamic release | S02-M |

## S03 — Hypothesis and request review

Role in clean test: lead. Evidence band: initial. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S03.01 | Merge two descriptions of the same scoped hydraulic-leak hypothesis without losing either citation | D02.S02; fixture:equivalent_proposals | Keep duplicate hypotheses solely because specialist IDs differ | S03-A |
| S03.02 | Preserve hydraulic support loss and primary relative withdrawal as distinct steps | D02.S02; D02.S04; D02.S05 | Collapse all mechanisms into one valve-caused-fall claim | S03-A |
| S03.03 | Preserve keeper release as a distinct unresolved hypothesis | D02.S05 | Treat keeper mode as answered by the hydraulic hypothesis | S03-A |
| S03.04 | Combine overlapping motion-evidence requests into shared acquisition | fixture:overlapping_requests; D02.S04 | Ask separately for the same clip under two specialist labels | S03-A |
| S03.05 | Approve requests with incident asset, interval and needed measurement scope | D01.S01; D02.S01; D04.S02 | Approve an unbounded request for all company documents | S03-A |
| S03.06 | State how requested motion/hydraulic evidence supports or challenges hypotheses | D02.S02; D02.S04; D02.S05 | Request records without a discriminating purpose | S03-A |
| S03.07 | Retain conditional hypothesis status until occurrence evidence arrives | D01.S03; D02.S05 | Promote a plausible specialist explanation to a supported incident cause | S03-A |
| S03.08 | Dispatch useful specialist/evidence work without waiting for complete machine knowledge | harness:lead-contract | Stop all branches because one mechanism is unknown | S03-A |

## S04 — Search and request coverage

Role in clean test: evidence. Evidence band: initial / motion. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S04.01 | Distinguish documents searched from documents that answer the motion request | D01.S03; D02.S04 | Treat a notice saying video exists as the video measurement | S04-A |
| S04.02 | Keep the initial missing motion measurement awaiting user rather than disproven/unavailable | D01.S03 | Declare the motion route impossible from a search miss | S04-A |
| S04.03 | Ask for the relevant motion interval and both moving objects | D02.S04; D01.S01 | Ask only for absolute yoke travel | S04-A |
| S04.04 | Keep evidence-worker output about request coverage rather than causal adjudication | harness:evidence-contract | Commit supported causal nodes in an evidence-worker response | S04-A |
| S04.05 | Recognize D07 answers vertical yoke/carrier displacement over the same interval | D07.S01; D07.S02 | Leave those delivered fields unacknowledged | S04-B |
| S04.06 | Separate D07 release timing from the displacement measurement endpoint | D07.S02; D07.S03 | Claim the displacement interval includes all release motion | S04-B |
| S04.07 | Retain keeper interface/offset as not covered by D07 | D07.S03 | Say receipt of the video resolves keeper mode | S04-B |
| S04.08 | Narrow the remaining request fields to genuine uncovered scope | D07.S01; D07.S02; D07.S03 | Request the same already-supplied vertical measurements again | S04-B |

## S05 — Motion and witness assessment

Role in clean test: assessor. Evidence band: motion. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S05.01 | Extract yoke displacement 40 +/- 1 mm | D07.S02 | Wrong object, unit or magnitude | S05-A |
| S05.02 | Extract carrier displacement 0 +/- 1 mm in the same frame/window | D07.S02 | Treat the carrier displacement as unmeasured or exactly zero without its bound | S05-A |
| S05.03 | Compute relative withdrawal interval 38-42 mm | D02.S04; D07.S02 | Use only 40 mm absolute travel or unjustified independent-error combination | S05-A |
| S05.04 | Conclude the 30 mm primary seat threshold is exceeded by the measured endpoint | D02.S05; D07.S02 | Leave primary loss unassessable despite the applicable measurement | S05-A |
| S05.05 | Associate visible contact and stationary carrier with a scoped holding contribution | D02.S04; D07.S02 | Assert that yoke descent caused the carrier to remain stationary | S05-A |
| S05.06 | Preserve the 13:24:00 endpoint versus 13:24:03 release distinction | D07.S02; D07.S03 | Invent a measured displacement during the unmeasured release interval | S05-A |
| S05.07 | Keep the specific keeper mode unresolved despite primary seating loss | D07.S03; D02.S05 | Infer a specific offset or rotation merely because the carrier fell | S05-A |
| S05.08 | Treat W-A/W-B as compatible, limited observations of different components | D06A.S01; D06A.S02; D06B.S01; D06B.S02 | Declare contradictory witnesses or use them as calibrated displacement measurements | S05-A |

## S06 — Hydraulics and execution assessment

Role in clean test: assessor. Evidence band: physical. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S06.01 | Use D08 incident evidence to identify flow through the tagged V17 route despite CLOSED indication | D08.S01; D08.S02 | Use D09 later testing alone to establish the incident rate | S06-A |
| S06.02 | Convert 0.400 +/- 0.010 L to 390-410 cm3 | D08.S02 | A factor-of-ten or litre-to-volume conversion error | S06-A |
| S06.03 | Apply 100 cm2 area and 1:1 motion to obtain 39-41 mm yoke displacement | D02.S02; D08.S03 | Omit area/ratio or give incompatible displacement | S06-A |
| S06.04 | Recognize the hydraulic displacement is consistent with the motion measurement | D07.S02; D08.S02; D08.S03 | Claim the two calibrated ranges conflict | S06-A |
| S06.05 | Establish actual no-block condition from execution/boundary evidence | D05.S02; D08.S03 | Use procedure omission alone as proof of actual execution | S06-A |
| S06.06 | Refute sufficient external-loss/alternate-path explanations only within the measured boundary | D08.S02; D08.S03 | Universally exclude all hydraulic routes or ignore scope/sensitivity | S06-A |
| S06.07 | Combine fluid loss, raised load and absent positive restraint when explaining descent | D02.S02; D02.S06; D05.S02; D08.S02 | Say leakage alone caused the entire fall | S06-A |
| S06.08 | Leave component-defect onset and keeper mode unresolved after hydraulic confirmation | D08.S04 | Infer contamination age or full release dynamics from the flow meter | S06-A |

## S07 — Physical causal board

Role in clean test: lead. Evidence band: physical. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S07.01 | Represent the observed fall independently of whether the complete causal path is established | D01.S01; D07.S03 | Withdraw the observed fall because a mechanism remains unknown | S07-A |
| S07.02 | Represent fluid loss plus load/no block jointly contributing to yoke descent | D02.S02; D05.S02; D08.S02 | A sufficient leakage-to-fall arrow with missing premises | S07-A |
| S07.03 | Represent both yoke and carrier motion as inputs to relative withdrawal | D02.S04; D07.S02 | A causal arrow from yoke descent to stationary carrier | S07-A |
| S07.04 | Represent relative threshold exceedance leading to primary seating loss | D02.S05; D07.S02 | Skip the relative measurement/threshold relationship | S07-A |
| S07.05 | Preserve an explicit unresolved keeper bridge before complete fall-path confirmation | D02.S05; D10.S03 | Mark the entire release path supported | S07-A |
| S07.06 | Keep actual block absence distinct from procedure omission | D04.S03; D05.S02 | Treat the two as an interchangeable node | S07-A |
| S07.07 | Represent procedure-to-absence contribution as unestablished without a decision/execution bridge | D04.S03; D05.S03 | Promote omission plus absence into proven procedural causation | S07-A |
| S07.08 | Preserve independent established hydraulic/motion findings while keeper evidence is missing | D07.S02; D08.S02; D10.S03 | Make every physical finding unresolved because keeper mode is unknown | S07-A |

## S08 — Upstream hypotheses

Role in clean test: specialist. Evidence band: physical. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S08.01 | Expand established V17 leakage into competing origin hypotheses | D08.S04; D02.S03 | Repeat only whether leakage occurred or assert one origin | S08-V |
| S08.02 | Seek component/maintenance evidence capable of distinguishing valve origins | D08.S04; D01.S03 | Request only another handle-position confirmation | S08-V |
| S08.03 | Investigate inspection/detection opportunity without assuming the policy physically caused contamination | D08.S04; D11.S02 | Assert maintenance policy created the contamination | S08-V |
| S08.04 | Expand actual block absence into competing procedure, requirement or execution explanations | D04.S03; D05.S02 | Treat absent block as the final organizational root cause | S08-B |
| S08.05 | Request relevant procedure approval, hazard review, applicable standards or execution rationale | D04.S03; D05.S03 | Ask unrelated broad management questions | S08-B |
| S08.06 | Keep deliberate noncompliance, training and budget origins conditional | D05.S03; D11.S03 | Confirm human intent or organizational reasons without evidence | S08-B |
| S08.07 | Investigate contact origins through maintenance configuration versus prior positioning/handling | D03C.S02; D05.S02; D07.S04 | Assume no stop alone explains precisely how contact arose | S08-C |
| S08.08 | Seek earlier positioning/configuration evidence without re-requesting occluded incident keeper motion | D05.S01; D07.S03; D07.S04 | Recycle a known unavailable keeper view as the only contact-origin route | S08-C |

## S09 — Origin and availability evidence

Role in clean test: evidence. Evidence band: late. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S09.01 | Identify the retained maintenance practice as no scheduled V17 seat-leak inspection and replacement on reported defect | D11.S01 | Treat V18/V19 replacements as V17 maintenance | S09-V |
| S09.02 | Keep detectability and physical contamination causation unestablished by that practice | D11.S02 | Infer the particular defect would necessarily have been found | S09-V |
| S09.03 | Keep leakage/contamination onset undated | D11.S03; D12.S02 | Assign a pre-incident contamination age or onset | S09-V |
| S09.04 | Separate delivered history from unresolved origin evidence in request coverage | D09.S03; D11.S01; D11.S03 | Call the entire valve-origin request answered or wholly unanswered | S09-V |
| S09.05 | Mark retained incident offset/dynamic-envelope acquisition as explicitly unavailable | D12.S02 | Treat explicit unavailability as only an unperformed search | S09-K |
| S09.06 | Keep missing keeper evidence distinct from refuting its physical mechanism | D12.S03 | Refute keeper bypass because the requested record is unavailable | S09-K |
| S09.07 | Specify a new valid route: validated envelope plus independently bounded incident offset | D10.S04; D12.S03 | Reopen from another centered seated measurement alone | S09-K |
| S09.08 | Keep other supported branches available while this acquisition route is blocked | D12.S03; D07.S02; D08.S02 | Stop or withdraw the entire investigation because one record is unavailable | S09-K |

## S10 — Boundaries and scoped negatives

Role in clean test: assessor. Evidence band: late. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S10.01 | Use current revision C for the incident and limit superseded A to its normal-rolling configuration | D03A.S01; D03C.S01 | Import the backup-roll stop from the superseded normal arrangement | S10-A |
| S10.02 | Recognize centered 8 +/- 1 mm overlap excludes simple rigid centered seated passage only | D10.S02 | Use seated overlap to rule out all off-center dynamic release | S10-A |
| S10.03 | Refute gross keeper plate/fastener separation or fracture within recovery-inspection scope | D14.S01; D14.S03 | Refute every deformation/bypass hypothesis or leave the scoped negative unrecognized | S10-A |
| S10.04 | Keep crane/load-contact refutation limited to the covered time and envelope | D07.S04 | Exclude earlier handling or every possible external contact | S10-A |
| S10.05 | Use later V17 bench leakage as compatibility evidence with unknown defect timing | D09.S02; D09.S03 | Back-date the later rate/contamination automatically | S10-A |
| S10.06 | Keep D13 actions as identified proposals with no demonstrated implementation/effectiveness | D13.S01; D13.S02 | Treat a proposed modification as a completed validated control | S10-A |
| S10.07 | Distinguish observed physical conditions from why the procedure/design omitted controls | D04.S03; D03C.S02; D05.S03 | Turn an unanswered why-question into an established origin | S10-A |
| S10.08 | Treat unavailable analysis/measurements as knowledge limits rather than physical causes | D03C.S04; D12.S03 | Put missing documentation itself on the physical causal chain | S10-A |

## S11 — Requests and stopping review

Role in clean test: lead. Evidence band: late. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S11.01 | Close the motion request within the delivered vertical-motion/release scope | D07.S01; D07.S02; D07.S03 | Continue asking for those fulfilled measurements | S11-A |
| S11.02 | Close hydraulic acquisition within the delivered incident-flow/boundary scope | D08.S01; D08.S02; D08.S03 | Leave the supplied incident flow unacknowledged | S11-A |
| S11.03 | Keep valve-origin timing explicitly unresolved or blocked within its unavailable route | D09.S03; D11.S03; D12.S02 | Close origin timing as established | S11-A |
| S11.04 | Keep the unavailable keeper acquisition route visibly separate from open physical hypotheses | D10.S03; D12.S02 | Label all keeper candidates refuted or hide the blocked route | S11-A |
| S11.05 | Reuse equivalent requests rather than repeat unchanged completed acquisition | harness:lead-contract; D12.S02 | Make duplicate requests without changed evidence or scope | S11-A |
| S11.06 | Account for upstream origins of established valve, no-block and contact conditions | D08.S04; D04.S03; D05.S02 | Stop solely because immediate physical conditions are known | S11-A |
| S11.07 | Preserve useful independent work while a different branch waits | harness:lead-contract; D12.S03 | Make a missing keeper record a prerequisite for all upstream work | S11-A |
| S11.08 | Declare partial/evidence-boundary status with concrete reopening conditions | D12.S02; D12.S03 | Call a resource pause or missing record exhaustive causal closure | S11-A |

## S12 — Final retained RCA

Role in clean test: lead. Evidence band: late. Maximum: 8.

| ID | Expected output | Source/contract | Do not credit | Clean packet |
|---|---|---|---|---|
| S12.01 | Retain the observed carrier fall as the focal occurrence | D01.S01; D07.S03 | Lose the focal event in the final state/report | S12-A |
| S12.02 | Retain fluid loss plus raised load and absent block as the joint descent explanation | D02.S02; D05.S02; D08.S02 | Final explanation uses leakage alone as sufficient | S12-A |
| S12.03 | Retain both motions/contact holding as the relative-withdrawal explanation | D02.S04; D07.S02 | Final explanation substitutes absolute yoke motion or an incorrect serial arrow | S12-A |
| S12.04 | Retain relative withdrawal beyond 30 mm as the primary seating-loss explanation | D02.S05; D07.S02 | Lose the threshold relationship in the final artifact | S12-A |
| S12.05 | Retain the specific keeper-release mechanism as unresolved | D07.S03; D10.S03 | Force complete keeper-path confirmation | S12-A |
| S12.06 | Retain recovered attachment and centered geometry as limits rather than proof of dynamic retention | D14.S01; D10.S02 | Use intact attachment/centered overlap to rule out dynamic release | S12-A |
| S12.07 | Retain the crane/contact negative with its time/envelope limits | D07.S04 | Drop the scoped negative or expand it beyond coverage | S12-A |
| S12.08 | Retain gross keeper fracture/separation refutation within inspection scope | D14.S01; D14.S03 | Substitute initial beam/yoke no-fracture reporting for the keeper finding | S12-A |

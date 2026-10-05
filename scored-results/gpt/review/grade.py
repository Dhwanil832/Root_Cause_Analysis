"""Persist the reviewer's explicit criterion judgments; no automatic semantic scoring."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT.parent / 'RCA-Linux-Server/bundle/benchmarks/R3-investigation-v1'
CRITERIA = json.loads((PACKAGE / 'private/evaluator/criteria.json').read_text())
WINDOWS = json.loads((ROOT / 'stage-windows.json').read_text())
ROWS = []

def ref(call, pointer=''):
    path = next((ROOT / 'repaired/case/calls').glob(f'{call:04d}_*/answer.txt'))
    return str(path.relative_to(ROOT)) + ('#' + pointer if pointer else '')

def value(reference):
    file, _, pointer = reference.partition('#')
    data = json.loads((ROOT / file).read_text())
    for part in pointer.lstrip('/').split('/') if pointer else []:
        part = part.replace('~1', '/').replace('~0', '~')
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data

def row(cid, outcome, refs, reason, *, origin=None, exposure='Supplied', contradictions=(), retained=(), later=(), opportunity=None):
    c = next(c for c in CRITERIA if c['id'] == cid)
    references = [ref(*r) for r in refs] or WINDOWS[c['stage']]['primary_outputs']
    contrary = [ref(*r) for r in contradictions]
    ROWS.append(dict(arm='gpt55_codex_repaired_connected', repetition=1, criterion_id=cid,
        stage=c['stage'], expected=c['expected'], not_credit=c['not_credit'], outcome=outcome,
        exposure=exposure, output_reference=references,
        excerpt_or_absence_reason=dict(review=reason, excerpts=[dict(reference=r, verbatim=value(r)) for r in references] if refs else [],
            bounded_absence_outputs=WINDOWS[c['stage']]['primary_outputs'] if outcome != 'Present' else []),
        contradiction=bool(contrary), contradiction_reference=contrary,
        contradiction_excerpts=[dict(reference=r, verbatim=value(r)) for r in contrary],
        failure_origin=origin or ('None' if outcome == 'Present' and not contrary else 'Interpretation'),
        reviewer='Codex assistant; single unblinded semantic review; no independent adjudication',
        stage_window=c['stage'], retained_state_reference=list(retained),
        later_recovery=[dict(reference=ref(*r), verbatim=value(ref(*r))) for r in later],
        opportunity_note=opportunity,
        controller_loss='No rejected batch; no raw-to-committed controller loss identified for this criterion.'))

def P(cid, refs, reason, **kw): row(cid, 'Present', refs, reason, **kw)
def M(cid, refs, reason, **kw): row(cid, 'Missing', refs, reason, **kw)
def N(cid, refs, reason, **kw): row(cid, 'Not reached', refs, reason, **kw)

P('S01.01',[(1,'/operations/0')],'The emitted focal occurrence includes the fall, pit, sled and scaffold.')
P('S01.02',[(1,'/operations/0/record/claim')],'Raised and backup-roll-removed outage configuration is explicit.')
M('S01.03',[(1,'/operations/2'),(1,'/next_work/1')],'C17/V17 tags are used correctly, but the intake does not explain or resolve the A/B circuit-nickname ambiguity. Tag naming alone does not demonstrate this particular disambiguation.')
P('S01.04',[(1,'/operations/2/reason')],'CLOSED position is explicitly distinguished from seat leakage and trapped-fluid retention.')
P('S01.05',[(1,'/operations/2/reason')],'Motor/pump isolation is explicitly said not to prove mechanical restraint.')
P('S01.06',[(1,'/decision'),(1,'/operations/0/reason')],'D15 is unreviewed, derived from the notice/handle status and not independent support.')
P('S01.07',[(1,'/operations/3/reason')],'Procedure omission is distinguished from proof of actual work; actual block presence needs execution evidence.')
P('S01.08',[(1,'/operations/1'),(1,'/operations/3')],'Initial requests prioritize motion and actual restraint/isolation.')

P('S02.01',[(7,'/operations/2')],'An unresolved mechanism explicitly says chamber-fluid loss permits downward yoke travel. This is conditional at the raised-load focal configuration, not confirmed incident leakage.')
P('S02.02',[(2,'/operations/1/reason'),(2,'/operations/1/record/fields')],'Seat/return leakage, external loss and alternate paths are distinct acquisition/discrimination candidates; separate node IDs are not required.')
P('S02.03',[(2,'/operations/1')],'The request specifies incident leakage, external and alternate return-path monitoring, not only CLOSED position.')
P('S02.04',[(7,'/operations/4'),(7,'/operations/5'),(1,'/operations/0')],'The initial conditional mechanism includes absence of effective positive restraint and the raised-assembly focal context; leakage is not treated as sufficient for the fall. This initial hypothesis check does not certify the later descent factorization.')
P('S02.05',[(7,'/operations/2/reason')],'Explicitly uses yoke travel minus carrier travel over the same interval.')
P('S02.06',[(7,'/operations/2/reason'),(7,'/operations/3')],'Primary-seat threshold and separate keeper/dynamic-path evidence are distinguished.')
P('S02.07',[(1,'/next_work/0'),(1,'/operations/4/reason')],'Intake explicitly proposes lateral-offset and fracture/deformation alternatives as conditional release paths. Equivalent proposal work by intake receives credit; multiple keeper node IDs are not required.')
P('S02.08',[(1,'/operations/1'),(1,'/operations/4')],'Motion/contact timing and post-event geometry/offset evidence are separately scoped with timing limits.')

N('S03.01',[(8,'/operations')],'No equivalent pair of hydraulic hypotheses requiring a citation-preserving merger was generated in the initial cycle. This is an unelicited opportunity, not an observed bad merge.',origin='Routing',exposure='Not obtained',opportunity='Duplicate-hypothesis fixture is not injected into connected mode; zero coverage retained in the denominator.')
P('S03.02',[(8,'/operations/2/reason')],'Although bundled in one node, the emitted reasoning distinguishes fluid loss permitting yoke travel, relative yoke-minus-carrier withdrawal, and the primary-seat threshold. It does not collapse these into valve-caused-fall.')
P('S03.03',[(8,'/operations/3')],'Keeper bypass is a distinct unresolved node.')
P('S03.04',[(2,'/operations/0'),(8,'/operations/2/reason'),(8,'/operations/5/reason')],'The lead reuses one scoped motion acquisition for the hydraulic/relative-motion hypothesis and joint release mechanism. Shared acquisition is present; no artificial duplicate request was injected.')
P('S03.05',[(2,'/operations/0/record'),(2,'/operations/1/record')],'Approved requests specify asset, incident window and measurement fields.')
P('S03.06',[(2,'/operations/0/reason'),(2,'/operations/1/reason')],'The lead explains how evidence can support, challenge or leave the candidate conditions inconclusive.')
P('S03.07',[(8,'/decision'),(8,'/operations/2'),(8,'/operations/5')],'Physical incident mechanism and its contribution remain unresolved before incident records arrive.')
P('S03.08',[(2,'/next_work')],'Useful evidence work is dispatched without requiring full machine knowledge or resolving keeper bypass first.')

P('S04.01',[(3,'/decision'),(3,'/operations/0/reason')],'Clearly separates the notice that a video exists from the missing motion record itself.')
P('S04.02',[(3,'/operations/0')],'Initial motion request is awaiting_user; a search gap is explicitly not unavailability.')
P('S04.03',[(3,'/operations/0/record')],'Request retains both moving objects and the incident window.')
P('S04.04',[(3,'/operations'),(4,'/operations'),(5,'/operations'),(6,'/operations')],'All initial evidence-worker operations revise request coverage only; later causal proposals are assessor/lead work.')
P('S04.05',[(10,'/operations/0/reason')],'D07 is acknowledged as answering both vertical displacements in the same interval.')
P('S04.06',[(10,'/operations/0/reason')],'13:24:00 displacement endpoint and 13:24:03 release are separately emitted.')
P('S04.07',[(10,'/operations/0/reason')],'The keeper interface and lateral offset remain occluded, despite delivered video.')
P('S04.08',[(11,'/operations/0'),(11,'/operations/3/record/fields')],'Motion request becomes answered; inspection request narrows to genuine dynamic/deformation/contact-mark gaps.')

P('S05.01',[(10,'/operations/0/reason')],'Yoke 40 +/-1 mm is explicitly extracted.')
P('S05.02',[(10,'/operations/0/reason')],'Carrier 0 +/-1 mm is explicitly extracted in the same interval.')
P('S05.03',[(10,'/operations/4/reason')],'40 +/-2 mm by interval arithmetic is equivalent to [38,42] mm; lower bound 38 is explicit.')
P('S05.04',[(10,'/operations/4/reason')],'38 mm lower bound exceeds the 30 mm primary-seat threshold.')
M('S05.05',[(10,'/operations/0/reason'),(11,'/operations/4/reason')],'Contact visibility and stationary-carrier measurements are reported, but the completed cycle never states their scoped holding contribution to differential motion. The reviewer does not infer a causal role merely from adjacent observations.')
P('S05.06',[(10,'/operations/0/reason')],'Measured endpoint and later release time remain separate.')
P('S05.07',[(10,'/operations/5')],'The specific offset/rotation/deformation bypass remains unresolved after primary seating loss.')
N('S05.08',[(10,'/operations'),(11,'/operations')],'D06A/D06B were never requested or supplied, so the two-witness reconciliation opportunity was not reached.',origin='Acquisition',exposure='Not obtained')

P('S06.01',[(10,'/operations/1/reason'),(10,'/operations/4/reason')],'D08 provides event-time flow through tagged V17 despite CLOSED; D09 is not used alone to establish the event rate.')
P('S06.02',[(10,'/operations/1/reason')],'The mathematically equivalent SI conversion 0.400 L = 0.000400 m3 with 0.010 L uncertainty is correct. 390–410 cm3 need not be written in those exact units.')
P('S06.03',[(10,'/operations/4/reason')],'100 cm2, 1:1 travel, and 40 +/-1 mm explicitly produce the expected 39–41 mm interval.')
P('S06.04',[(10,'/operations/4/reason')],'Hydraulic 40 +/-1 mm and independent motion 40 +/-1 mm are jointly used as supporting measurements, not presented as conflicting.')
P('S06.05',[(10,'/operations/6')],'Actual no-block condition uses D05 photograph and D08 boundary evidence, independently of procedure omission.')
P('S06.06',[(10,'/operations/1/reason'),(10,'/operations/4/reason')],'Within the stated incident boundary, 0.400 L goes through V17, external loss is bounded below 0.002 L and no alternate route is found. This is the scoped exclusion, not a universal hydraulic-path claim.')
M('S06.07',[(10,'/operations/4'),(10,'/operations/6'),(10,'/operations/7')],'No-block and raised configuration are known, but the emitted descent/withdrawal explanation uses fluid loss and volume/area alone; no-block appears in the joint full-fall edge. The load/no-restraint conditions are not explicitly combined as the descent explanation.',origin='Composition')
P('S06.08',[(10,'/operations/4/reason'),(10,'/operations/5')],'Defect timing and keeper mode explicitly remain unresolved after hydraulic confirmation.')

P('S07.01',[(1,'/operations/0'),(11,'/operations/7/reason')],'The reported focal event is retained and explicitly distinguished from the unresolved cause.',retained=['repaired/case/state.json#/ledger/N_FocalEvent_R3BeamFall/record'])
M('S07.02',[(11,'/operations/4'),(11,'/operations/6'),(11,'/operations/7')],'The board puts hydraulic loss/withdrawal and no-block together only at the full-fall edge. It does not represent raised load and absent block jointly conditioning yoke descent.',origin='Composition')
P('S07.03',[(11,'/operations/4/reason')],'Both 40 +/-1 mm yoke and 0 +/-1 mm carrier motions are explicitly inputs to the 40 +/-2 mm relative calculation. No mandated graph layout is imposed.')
P('S07.04',[(11,'/operations/4')],'The emitted claim and reason retain relative threshold exceedance and primary seating loss.')
P('S07.05',[(11,'/operations/5'),(11,'/operations/7')],'Unresolved keeper node prevents support of the full joint fall edge.')
P('S07.06',[(11,'/operations/6'),(11,'/operations/8/record')],'Actual block absence and task-text omission remain distinct ledger premises, although their causal link is wrongly promoted under S07.07.')
M('S07.07',[(11,'/operations/8')],'The lead explicitly supports procedural contribution from omission plus observed absence without a decision/execution bridge; acknowledging missing rationale does not preserve uncertainty about that contribution.',origin='Interpretation',contradictions=[(11,'/operations/8')])
P('S07.08',[(11,'/operations/4'),(11,'/operations/5')],'Supported hydraulic/motion findings survive the unresolved keeper branch.')

P('S08.01',[(15,'/operations/12/record/claim'),(15,'/operations/12/reason')],'The lead expands leakage into pre-event contamination, wear/maintenance condition and post-event handling alternatives; equivalent work by the lead receives credit.')
P('S08.02',[(15,'/operations/12')],'A new request seeks maintenance, preservation/lab, cleanliness and defect-analysis evidence to discriminate origins.')
P('S08.03',[(15,'/operations/12/reason')],'Pre-event inspection/leak-test history is requested with explicit timing/sensitivity limits and possible verified-clean/tight counterevidence. This investigates detection opportunity without asserting inspection practice physically creates contamination.')
P('S08.04',[(14,'/operations/2/reason'),(14,'/operations/0/reason')],'Alternative controlling instructions, extract/supply artifacts and an isolation-only control basis are considered. However, the same cycle prematurely treats the omission-to-absence contribution as already supported.',contradictions=[(14,'/operations/4'),(15,'/operations/11')])
P('S08.05',[(14,'/operations/0/reason'),(14,'/operations/2/reason')],'Scoped procedure-basis, risk-assessment, authorization and controlling-instruction evidence is sought through the existing route rather than a duplicate broad request.')
P('S08.06',[(14,'/operations/1/reason'),(14,'/operations/2')],'The output explicitly denies proof of deliberate noncompliance and leaves rationale as a candidate; no training/budget origin is confirmed.')
N('S08.07',[(15,'/next_work')],'No contact-origin investigation was dispatched, despite known contact. The run did not compare maintenance configuration with earlier positioning/handling.',origin='Routing',exposure='Not obtained',opportunity='Some prerequisite contact facts were supplied, but the contact-origin branch was never elicited; D03A/D03C were not obtained.')
N('S08.08',[(15,'/next_work')],'The dispatched keeper search seeks incident offset/deformation and contact-mark dating/loading, not earlier positioning/configuration to explain why contact arose. No such upstream cycle occurred.',origin='Routing',exposure='Not obtained')

P('S09.01',[(21,'/operations/1/reason'),(21,'/operations/5')],'No scheduled V17 seat-leak inspection, replace-on-defect practice and V18/V19 identity limits are explicit.')
P('S09.02',[(21,'/operations/6')],'The maintenance-to-leak edge remains unresolved because neither detectability nor physical contamination causation is established.')
P('S09.03',[(21,'/operations/4')],'Leakage/contamination onset remains undated and event-time contamination unresolved.')
P('S09.04',[(22,'/operations/1')],'Delivered maintenance history is acknowledged and removed from remaining fields; origin evidence stays partial.')
P('S09.05',[(22,'/operations/0/reason')],'The exact reason explicitly records retained-route unavailability, not an unperformed search. The partial request label reflects answered subfields; the frozen criterion accepts meaning and does not require the literal blocked label.')
P('S09.06',[(22,'/operations/2')],'Unavailable keeper evidence is explicitly distinguished from refuting bypass.')
P('S09.07',[(22,'/operations/0/reason'),(22,'/operations/2/reason')],'A newly validated envelope plus independently bounded incident offset is an explicit reopening route.')
P('S09.08',[(22,'/operations/3/reason'),(22,'/operations/5')],'Independent hydraulic/no-block findings are preserved and the maintenance-record branch advances while keeper acquisition is bounded.')

N('S10.01',[(10,'/operations'),(11,'/operations')],'The model never requested or received arrangement revisions D03A/D03C; it did not perform the A-versus-C applicability comparison.',origin='Acquisition',exposure='Not obtained')
P('S10.02',[(10,'/operations/3/reason'),(10,'/operations/5/reason')],'8 +/-1 mm overlap is explicitly limited to rigid centered seated geometry.')
P('S10.03',[(10,'/operations/3/reason')],'The emitted inspection account explicitly excludes gross plate/fastener separation/fracture within the examination scope while preserving deformation/off-center questions.')
P('S10.04',[(10,'/operations/0/reason')],'The negative is limited to the covered carrier envelope and 13:00–13:24:03; earlier/outside contact is not excluded.')
P('S10.05',[(10,'/operations/4/reason')],'Later bench leakage is explicitly compatibility evidence, not proof of incident rate or contamination timing.')
M('S10.06',[(10,'/decision'),(11,'/decision')],'D13 was supplied, but the first completed assessment/lead cycle does not discuss proposal versus implementation/effectiveness. It is correctly addressed later, outside this primary window.',later=[(16,'/operations/0/reason'),(19,'/operations/2/reason')])
P('S10.07',[(10,'/operations/6/reason'),(10,'/operations/8/reason')],'The reasons for procedural omission and block absence are explicitly unestablished. The separately wrong omission-to-absence link is charged to S07.07; it does not assert why the procedure itself omitted controls.')
P('S10.08',[(10,'/operations/5'),(10,'/operations/7')],'Unmeasured/unanalyzed keeper geometry leaves the mechanism unresolved rather than becoming a physical cause. D10 provides equivalent boundary evidence before D12 arrives.')

P('S11.01',[(11,'/operations/0')],'Motion closure is retained in the final ledger; original committed output provides exact provenance, consistent with prior connected-stage scoring.',retained=['repaired/case/state.json#/ledger/R_R3MotionRecord/record/status','repaired/case/state.json#/ledger/R_R3MotionRecord/justification/reason'])
P('S11.02',[(11,'/operations/1')],'Delivered incident-hydraulics closure is retained in the final ledger; no re-request of fulfilled incident flow.',retained=['repaired/case/state.json#/ledger/R_R3HydraulicRecords/record/status'])
P('S11.03',[(23,'/upstream_dispositions/4')],'Valve-origin timing stays explicitly unresolved/blocked at the unavailable route.')
P('S11.04',[(22,'/operations/0'),(22,'/operations/2')],'Retained request coverage explicitly records unavailable acquisition while the physical keeper hypothesis remains unresolved; partial is not misread as physical refutation.')
P('S11.05',[(22,'/decision'),(23,'/decision')],'Final agenda reuses existing routes and explicitly declines unchanged duplicate acquisition.')
M('S11.06',[(23,'/upstream_dispositions')],'Valve and work-control origins receive review, but contact origin is omitted. Actual no-block is also called already explained through the unsupported omission edge. All three expected origin branches are not accounted for.',origin='Routing',contradictions=[(23,'/upstream_dispositions/0')])
P('S11.07',[(22,'/operations/5'),(23,'/upstream_dispositions/5')],'Maintenance evidence was independently pursued and reviewed while keeper evidence remained unavailable. This is retained completed work, not credit for an unexecuted suggestion.')
P('S11.08',[(23,'/decision'),(23,'/upstream_dispositions/4'),(22,'/operations/2/reason')],'Terminal phase is partial at explicit evidence boundaries with concrete reopening conditions, not a resource pause or exhaustive root-cause claim.')

P('S12.01',[(1,'/operations/0')],'The original focal occurrence remains in the final active ledger.',retained=['repaired/case/state.json#/ledger/N_FocalEvent_R3BeamFall/record'])
M('S12.02',[(15,'/operations/4'),(22,'/operations/3'),(23,'/upstream_dispositions/1')],'The final explanation retains no-block at the joint fall edge but does not condition the supported yoke-descent/withdrawal explanation jointly on raised load and absent restraint. This missing relation is not repaired by merely listing the no-block node.',origin='Retention')
M('S12.03',[(15,'/operations/2'),(22,'/operations/0/reason'),(23,'/upstream_dispositions/1')],'Both measured motions and visible contact survive, but the final committed account does not express contact holding the carrier as a cause of differential withdrawal. It retains contact visibility/mark limits instead of the required scoped holding relation.',origin='Retention')
P('S12.04',[(15,'/operations/2/reason'),(23,'/upstream_dispositions/1')],'Final retained account preserves 40 +/-2 mm relative withdrawal with lower bound 38 greater than the 30 mm seat.',retained=['repaired/case/state.json#/ledger/N_R3HydraulicWithdrawalUnresolved/justification/reason'])
P('S12.05',[(22,'/operations/2'),(22,'/operations/3')],'Specific keeper path and complete fall edge remain unresolved in the final active ledger.',retained=['repaired/case/state.json#/ledger/N_R3KeeperBypassUnresolved/record/status'])
P('S12.06',[(11,'/operations/3/reason'),(22,'/operations/2/reason')],'Recovered attachment limits remain in retained request coverage; current keeper reasoning retains centered-geometry limits. Neither is treated as proof of dynamic retention.',retained=['repaired/case/state.json#/ledger/R_R3InspectionPhotos/coverage/3/reason','repaired/case/state.json#/ledger/N_R3KeeperBypassUnresolved/justification/reason'])
P('S12.07',[(11,'/operations/0/reason')],'The time/envelope-scoped crane negative remains in the final answered motion request justification; a dedicated refuted node is not required by this meaning metric.',retained=['repaired/case/state.json#/ledger/R_R3MotionRecord/justification/reason'])
P('S12.08',[(11,'/operations/3/reason')],'Gross keeper plate/fastener separation/fracture negative remains in the inspection request coverage history within the final active ledger. This is D14 keeper evidence, not the D01 beam/yoke observation.',retained=['repaired/case/state.json#/ledger/R_R3InspectionPhotos/coverage/3/reason'])

assert len(ROWS) == 96 and {r['criterion_id'] for r in ROWS} == {c['id'] for c in CRITERIA}
for r in ROWS:
    for reference in r['retained_state_reference']:
        value(reference)
    for reference in r['output_reference'] + r['contradiction_reference']:
        value(reference)
(ROOT / 'annotations.json').write_text(json.dumps(ROWS, indent=2) + '\n')
print('Persisted 96 explicit semantic judgments with exact output references.')

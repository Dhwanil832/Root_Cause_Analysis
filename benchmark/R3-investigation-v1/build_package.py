"""Offline authoring only. Never imports or calls a model client."""
from pathlib import Path
import sys,json,hashlib,shutil,copy,datetime
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]
PROTO=BASE/'prototype'
OLD=BASE/'experiments/U05-r3-three-arm'
sys.path.insert(0,str(PROTO))
from rca import controller,documents,engine,prompts
from rca.storage import initial

def save(path,data):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def write(path,text):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

STAGES=[
('S01','Incident understanding','intake','initial'),
('S02','Mechanism hypotheses','specialist','initial'),
('S03','Hypothesis and request review','lead','initial'),
('S04','Search and request coverage','evidence','initial / motion'),
('S05','Motion and witness assessment','assessor','motion'),
('S06','Hydraulics and execution assessment','assessor','physical'),
('S07','Physical causal board','lead','physical'),
('S08','Upstream hypotheses','specialist','physical'),
('S09','Origin and availability evidence','evidence','late'),
('S10','Boundaries and scoped negatives','assessor','late'),
('S11','Requests and stopping review','lead','late'),
('S12','Final retained RCA','lead','late')]

# Each row is one binary meaning/behavior check, not a whole-answer all-or-nothing grade.
# Format: expected | source references | unacceptable substitute
TEXT={
'S01':'''Retain the carrier fall into the pit onto sled/scaffold as the focal occurrence|D01.S01|Treat a proposed cause as the observed focal event
Identify the raised, backup-roll-removed maintenance configuration|D01.S01;D02.S01|Use normal rolling configuration without qualification
Use C17/V17 tags to resolve A/B naming ambiguity|D04.S02|Assign a circuit from its A/B nickname alone
Distinguish CLOSED indication from hydraulic sealing|D02.S03|Confirm tight isolation from handle position
Distinguish electrical isolation from positive mechanical restraint|D02.S06|Conclude electrical isolation removed gravity
Identify D15 as an unreviewed interpretation with no independent corroboration|D15.S01;D15.S02;D15.S03|Count repeated interpretation as a new observation
Keep actual block presence unknown from the procedure alone|D04.S03|Infer actual no-block execution from the omitted instruction
Prioritize incident motion and actual isolation/restraint clarification|D01.S03;D02.S04;D04.S03|Begin with unrelated organizational questions or claim complete causal closure''',
'S02':'''Propose fluid loss permitting loaded yoke descent as a conditional mechanism|D02.S02|Confirm incident leakage before incident records arrive
Keep V17 seat leakage, external loss and alternate paths as distinguishable hydraulic candidates|D02.S02;D02.S03|Treat every fluid-loss route as the same proposition
Specify incident flow/boundary evidence that distinguishes hydraulic paths|D02.S02;D01.S03|Ask only whether the valve was CLOSED
Include restraint/load premises when testing fluid-loss contribution|D02.S02;D02.S06|Treat valve leakage alone as sufficient for the full fall
Test relative yoke/carrier motion rather than yoke travel alone|D02.S04;D02.S05|Assume a moving yoke necessarily withdraws from a following carrier
Keep primary seating loss separate from keeper-release mode|D02.S05|Equate reaching the primary threshold with proof of keeper bypass
Propose distinct offset, rotation or deformation/geometry candidates for keeper release|D02.S05;D01.S02|Confirm one release mode from the fall or recovered attachment
Request time/configuration-relevant contact and keeper geometry evidence|D02.S04;D02.S05|Use an intact keeper alone to rule out dynamic release''',
'S03':'''Merge two descriptions of the same scoped hydraulic-leak hypothesis without losing either citation|D02.S02;fixture:equivalent_proposals|Keep duplicate hypotheses solely because specialist IDs differ
Preserve hydraulic support loss and primary relative withdrawal as distinct steps|D02.S02;D02.S04;D02.S05|Collapse all mechanisms into one valve-caused-fall claim
Preserve keeper release as a distinct unresolved hypothesis|D02.S05|Treat keeper mode as answered by the hydraulic hypothesis
Combine overlapping motion-evidence requests into shared acquisition|fixture:overlapping_requests;D02.S04|Ask separately for the same clip under two specialist labels
Approve requests with incident asset, interval and needed measurement scope|D01.S01;D02.S01;D04.S02|Approve an unbounded request for all company documents
State how requested motion/hydraulic evidence supports or challenges hypotheses|D02.S02;D02.S04;D02.S05|Request records without a discriminating purpose
Retain conditional hypothesis status until occurrence evidence arrives|D01.S03;D02.S05|Promote a plausible specialist explanation to a supported incident cause
Dispatch useful specialist/evidence work without waiting for complete machine knowledge|harness:lead-contract|Stop all branches because one mechanism is unknown''',
'S04':'''Distinguish documents searched from documents that answer the motion request|D01.S03;D02.S04|Treat a notice saying video exists as the video measurement
Keep the initial missing motion measurement awaiting user rather than disproven/unavailable|D01.S03|Declare the motion route impossible from a search miss
Ask for the relevant motion interval and both moving objects|D02.S04;D01.S01|Ask only for absolute yoke travel
Keep evidence-worker output about request coverage rather than causal adjudication|harness:evidence-contract|Commit supported causal nodes in an evidence-worker response
Recognize D07 answers vertical yoke/carrier displacement over the same interval|D07.S01;D07.S02|Leave those delivered fields unacknowledged
Separate D07 release timing from the displacement measurement endpoint|D07.S02;D07.S03|Claim the displacement interval includes all release motion
Retain keeper interface/offset as not covered by D07|D07.S03|Say receipt of the video resolves keeper mode
Narrow the remaining request fields to genuine uncovered scope|D07.S01;D07.S02;D07.S03|Request the same already-supplied vertical measurements again''',
'S05':'''Extract yoke displacement 40 +/- 1 mm|D07.S02|Wrong object, unit or magnitude
Extract carrier displacement 0 +/- 1 mm in the same frame/window|D07.S02|Treat the carrier displacement as unmeasured or exactly zero without its bound
Compute relative withdrawal interval 38-42 mm|D02.S04;D07.S02|Use only 40 mm absolute travel or unjustified independent-error combination
Conclude the 30 mm primary seat threshold is exceeded by the measured endpoint|D02.S05;D07.S02|Leave primary loss unassessable despite the applicable measurement
Associate visible contact and stationary carrier with a scoped holding contribution|D02.S04;D07.S02|Assert that yoke descent caused the carrier to remain stationary
Preserve the 13:24:00 endpoint versus 13:24:03 release distinction|D07.S02;D07.S03|Invent a measured displacement during the unmeasured release interval
Keep the specific keeper mode unresolved despite primary seating loss|D07.S03;D02.S05|Infer a specific offset or rotation merely because the carrier fell
Treat W-A/W-B as compatible, limited observations of different components|D06A.S01;D06A.S02;D06B.S01;D06B.S02|Declare contradictory witnesses or use them as calibrated displacement measurements''',
'S06':'''Use D08 incident evidence to identify flow through the tagged V17 route despite CLOSED indication|D08.S01;D08.S02|Use D09 later testing alone to establish the incident rate
Convert 0.400 +/- 0.010 L to 390-410 cm3|D08.S02|A factor-of-ten or litre-to-volume conversion error
Apply 100 cm2 area and 1:1 motion to obtain 39-41 mm yoke displacement|D02.S02;D08.S03|Omit area/ratio or give incompatible displacement
Recognize the hydraulic displacement is consistent with the motion measurement|D07.S02;D08.S02;D08.S03|Claim the two calibrated ranges conflict
Establish actual no-block condition from execution/boundary evidence|D05.S02;D08.S03|Use procedure omission alone as proof of actual execution
Refute sufficient external-loss/alternate-path explanations only within the measured boundary|D08.S02;D08.S03|Universally exclude all hydraulic routes or ignore scope/sensitivity
Combine fluid loss, raised load and absent positive restraint when explaining descent|D02.S02;D02.S06;D05.S02;D08.S02|Say leakage alone caused the entire fall
Leave component-defect onset and keeper mode unresolved after hydraulic confirmation|D08.S04|Infer contamination age or full release dynamics from the flow meter''',
'S07':'''Represent the observed fall independently of whether the complete causal path is established|D01.S01;D07.S03|Withdraw the observed fall because a mechanism remains unknown
Represent fluid loss plus load/no block jointly contributing to yoke descent|D02.S02;D05.S02;D08.S02|A sufficient leakage-to-fall arrow with missing premises
Represent both yoke and carrier motion as inputs to relative withdrawal|D02.S04;D07.S02|A causal arrow from yoke descent to stationary carrier
Represent relative threshold exceedance leading to primary seating loss|D02.S05;D07.S02|Skip the relative measurement/threshold relationship
Preserve an explicit unresolved keeper bridge before complete fall-path confirmation|D02.S05;D10.S03|Mark the entire release path supported
Keep actual block absence distinct from procedure omission|D04.S03;D05.S02|Treat the two as an interchangeable node
Represent procedure-to-absence contribution as unestablished without a decision/execution bridge|D04.S03;D05.S03|Promote omission plus absence into proven procedural causation
Preserve independent established hydraulic/motion findings while keeper evidence is missing|D07.S02;D08.S02;D10.S03|Make every physical finding unresolved because keeper mode is unknown''',
'S08':'''Expand established V17 leakage into competing origin hypotheses|D08.S04;D02.S03|Repeat only whether leakage occurred or assert one origin
Seek component/maintenance evidence capable of distinguishing valve origins|D08.S04;D01.S03|Request only another handle-position confirmation
Investigate inspection/detection opportunity without assuming the policy physically caused contamination|D08.S04;D11.S02|Assert maintenance policy created the contamination
Expand actual block absence into competing procedure, requirement or execution explanations|D04.S03;D05.S02|Treat absent block as the final organizational root cause
Request relevant procedure approval, hazard review, applicable standards or execution rationale|D04.S03;D05.S03|Ask unrelated broad management questions
Keep deliberate noncompliance, training and budget origins conditional|D05.S03;D11.S03|Confirm human intent or organizational reasons without evidence
Investigate contact origins through maintenance configuration versus prior positioning/handling|D03C.S02;D05.S02;D07.S04|Assume no stop alone explains precisely how contact arose
Seek earlier positioning/configuration evidence without re-requesting occluded incident keeper motion|D05.S01;D07.S03;D07.S04|Recycle a known unavailable keeper view as the only contact-origin route''',
'S09':'''Identify the retained maintenance practice as no scheduled V17 seat-leak inspection and replacement on reported defect|D11.S01|Treat V18/V19 replacements as V17 maintenance
Keep detectability and physical contamination causation unestablished by that practice|D11.S02|Infer the particular defect would necessarily have been found
Keep leakage/contamination onset undated|D11.S03;D12.S02|Assign a pre-incident contamination age or onset
Separate delivered history from unresolved origin evidence in request coverage|D09.S03;D11.S01;D11.S03|Call the entire valve-origin request answered or wholly unanswered
Mark retained incident offset/dynamic-envelope acquisition as explicitly unavailable|D12.S02|Treat explicit unavailability as only an unperformed search
Keep missing keeper evidence distinct from refuting its physical mechanism|D12.S03|Refute keeper bypass because the requested record is unavailable
Specify a new valid route: validated envelope plus independently bounded incident offset|D10.S04;D12.S03|Reopen from another centered seated measurement alone
Keep other supported branches available while this acquisition route is blocked|D12.S03;D07.S02;D08.S02|Stop or withdraw the entire investigation because one record is unavailable''',
'S10':'''Use current revision C for the incident and limit superseded A to its normal-rolling configuration|D03A.S01;D03C.S01|Import the backup-roll stop from the superseded normal arrangement
Recognize centered 8 +/- 1 mm overlap excludes simple rigid centered seated passage only|D10.S02|Use seated overlap to rule out all off-center dynamic release
Refute gross keeper plate/fastener separation or fracture within recovery-inspection scope|D14.S01;D14.S03|Refute every deformation/bypass hypothesis or leave the scoped negative unrecognized
Keep crane/load-contact refutation limited to the covered time and envelope|D07.S04|Exclude earlier handling or every possible external contact
Use later V17 bench leakage as compatibility evidence with unknown defect timing|D09.S02;D09.S03|Back-date the later rate/contamination automatically
Keep D13 actions as identified proposals with no demonstrated implementation/effectiveness|D13.S01;D13.S02|Treat a proposed modification as a completed validated control
Distinguish observed physical conditions from why the procedure/design omitted controls|D04.S03;D03C.S02;D05.S03|Turn an unanswered why-question into an established origin
Treat unavailable analysis/measurements as knowledge limits rather than physical causes|D03C.S04;D12.S03|Put missing documentation itself on the physical causal chain''',
'S11':'''Close the motion request within the delivered vertical-motion/release scope|D07.S01;D07.S02;D07.S03|Continue asking for those fulfilled measurements
Close hydraulic acquisition within the delivered incident-flow/boundary scope|D08.S01;D08.S02;D08.S03|Leave the supplied incident flow unacknowledged
Keep valve-origin timing explicitly unresolved or blocked within its unavailable route|D09.S03;D11.S03;D12.S02|Close origin timing as established
Keep the unavailable keeper acquisition route visibly separate from open physical hypotheses|D10.S03;D12.S02|Label all keeper candidates refuted or hide the blocked route
Reuse equivalent requests rather than repeat unchanged completed acquisition|harness:lead-contract;D12.S02|Make duplicate requests without changed evidence or scope
Account for upstream origins of established valve, no-block and contact conditions|D08.S04;D04.S03;D05.S02|Stop solely because immediate physical conditions are known
Preserve useful independent work while a different branch waits|harness:lead-contract;D12.S03|Make a missing keeper record a prerequisite for all upstream work
Declare partial/evidence-boundary status with concrete reopening conditions|D12.S02;D12.S03|Call a resource pause or missing record exhaustive causal closure''',
'S12':'''Retain the observed carrier fall as the focal occurrence|D01.S01;D07.S03|Lose the focal event in the final state/report
Retain fluid loss plus raised load and absent block as the joint descent explanation|D02.S02;D05.S02;D08.S02|Final explanation uses leakage alone as sufficient
Retain both motions/contact holding as the relative-withdrawal explanation|D02.S04;D07.S02|Final explanation substitutes absolute yoke motion or an incorrect serial arrow
Retain relative withdrawal beyond 30 mm as the primary seating-loss explanation|D02.S05;D07.S02|Lose the threshold relationship in the final artifact
Retain the specific keeper-release mechanism as unresolved|D07.S03;D10.S03|Force complete keeper-path confirmation
Retain recovered attachment and centered geometry as limits rather than proof of dynamic retention|D14.S01;D10.S02|Use intact attachment/centered overlap to rule out dynamic release
Retain the crane/contact negative with its time/envelope limits|D07.S04|Drop the scoped negative or expand it beyond coverage
Retain gross keeper fracture/separation refutation within inspection scope|D14.S01;D14.S03|Substitute initial beam/yoke no-fracture reporting for the keeper finding'''
}

def main():
 for d in ['public/records','private/evaluator','clean/packets','frozen/prompts','review','verification']:(ROOT/d).mkdir(parents=True,exist_ok=True)
 docs={}
 manifest=json.loads((OLD/'source-manifest.json').read_text())
 for p in sorted((OLD/'records').glob('*.json')):
  j=json.loads(p.read_text());original=BASE.parent/'Try 8/benchmarks/R3-internal-2026-09-29/records'/p.name
  assert p.read_bytes()==original.read_bytes();assert sha(original)==manifest[str(original)]
  shutil.copy2(p,ROOT/'public/records'/p.name);docs[j['id']]=j
 sections={s['id'] for d in docs.values() for s in d['sections']}
 chart=Path('/Users/dhwanilchauhan/Downloads/RCA Chart');assert sha(chart)==manifest[str(chart)]
 shutil.copy2(chart,ROOT/'private/evaluator/original-chart.pdf')
 gt=BASE.parent/'Try 8/benchmarks/R3-internal-2026-09-29/evaluator/GROUND_TRUTH.md';assert sha(gt)==manifest[str(gt)]
 shutil.copy2(gt,ROOT/'private/evaluator/PRIOR_GROUND_TRUTH.md')
 for role in ['intake','lead','specialist','evidence','assessor']:write('frozen/prompts/'+role+'.txt',prompts.prompt(role))
 save('frozen/output-schema.json',__import__('rca.schema',fromlist=['OUTPUT']).OUTPUT)
 files=[*sorted((PROTO/'rca').glob('*.py')),PROTO/'rca/ui.html',PROTO/'harness.py',PROTO/'CONTRACT.md',PROTO/'tests/test_runtime.py']
 for p in files:
  target=ROOT/'frozen/prototype'/p.relative_to(PROTO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 for p in (OLD/'prompts').glob('*.txt'):
  target=ROOT/'frozen/baseline-prompts'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 save('frozen/original-path-manifest.json',{str(p):sha(p) for p in files+list((OLD/'prompts').glob('*.txt'))})
 shutil.copy2(PROTO/'cases/r3-walkthrough/state.json',ROOT/'review/prior-case-state.json')
 shutil.copy2(PROTO/'acceptance/semantic-grades.json',ROOT/'review/prior-semantic-grades.json')
 shutil.copy2('/tmp/r3-runtime-review-tests.txt',ROOT/'verification/prototype-tests.txt')
 criteria=[]
 for stage,name,role,wave in STAGES:
  lines=TEXT[stage].splitlines();assert len(lines)==8
  for i,line in enumerate(lines,1):
   expected,refs,fail=line.split('|');refs=refs.split(';')
   assert all(r in sections or r.startswith(('fixture:','harness:')) for r in refs),(stage,refs)
   criteria.append(dict(id=f'{stage}.{i:02}',stage=stage,stage_name=name,role=role,expected=expected,source_refs=refs,not_credit=fail,points=1,acceptable='Equivalent supported meaning with the necessary conditions and scope. No exact wording, node ID or layout requirement.',contradiction_rule='Credit presence separately; record any contradictory assertion and its exact location. Do not award a consistent-correct result when contradiction remains.',clean_packet=None))
 save('private/evaluator/criteria.json',criteria)
 save('private/evaluator/stages.json',[dict(id=s,name=n,role=r,evidence_band=w,max_points=8) for s,n,r,w in STAGES])
 inventory=[dict(id=k,title=v['title'],sha256=sha(ROOT/'public/records'/f'{k}.json'),sections=[x['id'] for x in v['sections']],provenance='Authored synthetic surrounding record; unchanged from R3-INT-01',initial=k in ['D01','D02','D04','D15']) for k,v in docs.items()]
 save('public/inventory.json',inventory)
 save('public/start.json',dict(description='At 13:24 on 14 October 2024 the R3 delivery carrier beam fell into the mill pit and struck the sled and scaffold. Investigate the physical mechanism and relevant upstream causes, preserving evidence limits.',initial_source_ids=['D01','D02','D04','D15']))
 save('private/evaluator/verification.json',dict(record_count=len(docs),record_copies_exact=True,original_chart_hash_matches=True,prior_ground_truth_hash_matches=True,all_criterion_section_refs_exist=True,arithmetic=dict(volume_cm3=[390,410],area_cm2=100,hydraulic_motion_mm=[390/100*10,410/100*10],relative_motion_mm=[39-1,41-(-1)],seat_threshold_mm=30),scope='Internal source consistency and assistant review; no independent engineering certification.',model_calls_this_preparation=0))
 return criteria,docs

if __name__=='__main__':main()

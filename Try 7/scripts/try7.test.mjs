import test from 'node:test';
import assert from 'node:assert/strict';
import {database,model,cases,document,finding,fixtureRunner,drain,savedState} from './investigation-test-support.mjs';
import {initializeState,planNext} from '../src/engine/tasks/planner.ts';
import {ingestFinding,ingestQuestion} from '../src/engine/records.ts';
import {bindQuestion,mergeQuestions,activeQuestion,queueDeliveries} from '../src/engine/questions/ledger.ts';
import {applyInvestigationTask,syncBoardEvidence} from '../src/engine/investigation/apply.ts';
import {investigationBase} from '../src/engine/investigation/context.ts';
import {applyRole} from '../src/engine/validation/role.ts';
import {refreshIntegrity} from '../src/engine/validation/integrity.ts';
import {applyCorrections,applyImpacts} from '../src/engine/revisions/apply.ts';
import {project} from '../src/engine/board/projection.ts';
import {registerSources} from '../src/knowledge/sources/registry.ts';
import {enqueueRevision,latestInput} from '../src/server/engine-repository.ts';
import {D1EngineStore} from '../src/engine/tasks/d1-store.ts';
import {exportExperiment,redactSecrets} from '../src/experiments/export.ts';
import {exportArchive} from '../src/experiments/archive.ts';
import {unzipSync,strFromU8} from 'fflate';
import {executeTask} from '../src/engine/tasks/executor.ts';
import {failureCategory} from '../src/engine/validation/execution.ts';
import {TaskContextError} from '../src/engine/context/planner.ts';
import {recoverReferenceQuestions} from '../src/engine/questions/reference-recovery.ts';

const input={...cases[0],model,answers:[]};
const task=(kind,id=kind,owner='causal-analysis',targetIds=[])=>({id,kind,owner,targetIds,requiredSpanIds:[],query:'incident',dependsOn:[]});
const refsFor=s=>({sources:new Map(s.sources.flatMap(s=>s.spans).map((s,i)=>[`S${i+1}`,s.id])),findings:new Map(s.findings.map((f,i)=>[`F${i+1}`,f.id])),questions:new Map(s.questions.map((q,i)=>[`Q${i+1}`,q.id]))});
const question=(decision='Check restraint',intent='Measurement')=>({text:'What did the gauge show?',decision,intent,subject:'P1',location:'Bay',time:'10:00',references:[]});
const decision={summary:'Scripted reducer verification, not a model result.'};
async function stateWithNode() {
  const s=await initializeState(input,1,null),refs=refsFor(s);
  const id=ingestFinding(s,task('read'),finding('Gauge P1 indicated 4.5 bar at 11:00.','S2'),refs),f=s.findings[0];
  s.investigation.selectedFindingIds=[id];
  f.status='supported';f.reviewExecution='complete';
  s.propositions.push({id:'p:'+id,findingId:id,type:'barrier',label:f.statement,detail:'',spanIds:f.spanIds,status:'supported',reviewReason:'',humanStatus:'accepted'});
  return s;
}

test('same wording retains separate decisions; merge preserves both purposes and all answer parts',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s);
  ingestQuestion(s,task('consult','a','stored-energy'),question('Check restraint','Measurement'),r);
  ingestQuestion(s,task('consult','b','equipment-tools'),question('Check instrument validity','Calibration'),r);
  assert.equal(s.questions.length,2);
  const [a,b]=s.questions;
  bindQuestion(a,task('consult','a','stored-energy'),{parts:['Pressure at event','Measurement time']});
  assert.equal(a.parts.length,2,'Explicit subparts replace the placeholder');
  mergeQuestions(s,b,a,'Same scoped gauge observation; preserve calibration need and both decisions.');
  assert.equal(a.parts.length,3);assert.equal(a.subscriptions.some(x=>x.decision==='Check instrument validity'),true);
  assert.deepEqual(new Set(a.owners),new Set(['stored-energy','equipment-tools']));
  assert.throws(()=>mergeQuestions(s,a,b,'Circular'),/canonical/);
});

test('scope mismatch cannot be merged despite identical question text',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s);
  ingestQuestion(s,task('consult'),question(),r);
  ingestQuestion(s,task('consult'),{...question(),time:'11:00'},r);
  assert.throws(()=>mergeQuestions(s,s.questions[1],s.questions[0],'Equivalent'),/time scopes/);
  assert.equal(s.questions[1].coveredBy,null);
});

test('partial coverage remains partial, returns original citations, and receives each owner receipt',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s);
  const id=ingestQuestion(s,task('consult','a','stored-energy'),question(),r),q=s.questions[0];
  bindQuestion(q,task('consult','b','equipment-tools'),{parts:['Pressure','Calibration']});q.owners.push('equipment-tools');r.questions.set('Q1',id);
  await applyInvestigationTask(s,task('resolve','resolve','answer-fetching',[id]),{answers:[{question:'Q1',status:'answered',answer:'4.5 bar.',references:[],findings:[],equivalentTo:null,evidenceNeeded:'Calibration unknown',coverage:[{part:q.parts[0].id,status:'answered',answer:'4.5 bar.',references:['S2'],gap:''}]}],decision},r);
  assert.equal(q.status,'partial');assert.equal(q.answerCompleteness,'partial');assert.ok(q.answerSpanIds.includes(r.sources.get('S2')));
  for(const owner of q.owners)await applyInvestigationTask(s,task('respond',owner,owner,[id]),{responses:[{question:'Q1',answerRevision:1,implication:'Pressure is known; calibration remains unestablished.'}],directions:[],decision},r);
  assert.equal(q.deliveries.length,2);assert.ok(q.deliveries.every(d=>d.status==='received'));
});

test('unavailable and conflicting answers do not collapse to not-found or answered',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s);
  const id=ingestQuestion(s,task('consult'),question(),r);r.questions.set('Q1',id);
  const out={question:'Q1',status:'unavailable',answer:'',references:[],findings:[],equivalentTo:null,evidenceNeeded:'Record access denied.'};
  await applyInvestigationTask(s,task('resolve','x','answer-fetching',[id]),{answers:[out],decision},r);
  assert.equal(s.questions[0].status,'unavailable');assert.equal(s.questions[0].answerCompleteness,'unavailable');
  await applyInvestigationTask(s,task('resolve','y','answer-fetching',[id]),{answers:[{...out,status:'conflicting',answer:'The supplied accounts disagree.',references:['S1','S2']}],decision},r);
  assert.equal(s.questions[0].status,'conflicting');assert.equal(s.questions[0].answerRevision,2);
});

test('supported indicator is not a verified barrier without an independently evidenced protective function',async()=>{
  const s=await stateWithNode(),r=refsFor(s),p=s.propositions[0];
  assert.equal(project(s,input,'completed').causalBoard.nodes[1].verified,false);
  assert.throws(()=>applyRole(s,task('role','role','causal-verification',[p.findingId]),{status:'valid',reason:'It is a gauge.',protectiveFunction:'',references:['S2'],decision},r),/protective function/);
  applyRole(s,task('role','role','causal-verification',[p.findingId]),{status:'invalid',reason:'A displayed reading is not an established protective function.',protectiveFunction:'',references:['S2'],decision},r);
  assert.equal(p.humanStatus,'reopened');assert.equal(p.status,'supported');assert.equal(p.roleAssessment.status,'invalid');
});

test('opposite strict precedence is flagged without banning physical feedback links',async()=>{
  const s=await initializeState(input,1,null);
  s.relationships=[{id:'a',from:'A',to:'B',type:'preceded',proposedBy:['map'],status:'supported'},{id:'b',from:'B',to:'A',type:'preceded',proposedBy:['map'],status:'supported'}];
  refreshIntegrity(s);assert.ok(s.relationships.every(e=>e.status==='unknown'&&e.integrityIssues.length));
  s.relationships.forEach(e=>{e.type='enabled';e.status='proposed';});refreshIntegrity(s);
  assert.ok(s.relationships.every(e=>!e.integrityIssues.length));
});

test('sourced timestamp correction revises current wording, preserves history, and reopens roles and links',async()=>{
  const s=await stateWithNode(),old=structuredClone(s),r=refsFor(s),f=s.findings[0],p=s.propositions[0];
  p.roleAssessment={status:'valid',role:'barrier',reason:'Previous judgment',protectiveFunction:'Previous function',spanIds:f.spanIds,findingRevision:1,version:1};
  s.relationships.push({id:'edge',from:p.id,to:'focal',findingIds:[f.id],spanIds:f.spanIds,type:'enabled',proposedBy:['map'],status:'supported',rationale:'Test',counterfactual:'Test',alternative:'Unknown',gap:'',reviewReason:''});
  const correction={finding:'F1',expectedRevision:1,statement:'Gauge P1 indicated 4.5 bar at 10:00.',subject:'P1',predicate:'indicated',location:'',time:'10:00',unit:'bar',qualifiers:'',references:['S2'],reason:'Original timestamp is 10:00.'};
  const applied=applyCorrections(s,task('revise'),{corrections:[correction]},r);syncBoardEvidence(s);
  assert.ok(applied.has(f.id));assert.equal(f.revision,2);assert.equal(f.statement,correction.statement);assert.equal(f.history[0].statement,old.findings[0].statement);
  assert.equal(p.label,correction.statement);assert.equal(p.roleAssessment,undefined);assert.equal(p.humanStatus,'reopened');assert.equal(s.relationships[0].status,'proposed');
  assert.equal(project(s,input,'completed').causalBoard.nodes[1].label,correction.statement);
  applyCorrections(s,task('revise','stale'),{corrections:[correction]},r);assert.equal(f.revision,2);assert.match(s.quarantine.at(-1).reason,/Stale correction/);
  applyImpacts(s,task('revise','stale','causal-analysis',[f.id]),{impacts:[{target:'F1',action:'correct',reason:'Pretend it worked',findings:['F1']}]},r);
  assert.deepEqual(s.investigation.pendingImpacts,[f.id]);
});

test('reviewer-origin questions reach resolver and return a receipt before publication',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[],runner=fixtureRunner(log);
  try {
    await enqueueRevision(db,'track',input.incident,model,input.documents);
    await drain(store,async request=>{
      const result=await runner(request);
      if(request.schemaName==='try7_verify')result.output.questions=[{...question('Check mechanical path','Applicable drawing'),text:'Which drawing establishes this mechanical path?',references:[request.evidencePacket.evidence[0].ref]}];
      return result;
    });
    const s=await savedState(db),q=s.questions.find(q=>q.text.startsWith('Which drawing'));
    assert.ok(q&&activeQuestion(s,q));assert.ok(q.inventory);assert.ok(q.deliveries.some(d=>d.owner==='causal-verification'&&d.status==='received'));
    assert.ok(project(s,input,'completed').questions.some(item=>item.id===q.id));
  }finally{db.close();}
});

test('framing includes original sources even when generic lexical relevance is weak',async()=>{
  const s=await initializeState({...input,documents:[...input.documents,document('unrelated-title','HIDDEN-IN-PLAIN-SIGHT: the fixture record has a reversed time column.')]},1,null);
  let packet;
  await executeTask(s,task('frame'),model,'track',{cached:async()=>null},async request=>{packet=request.evidencePacket;return {output:{decision},durationMs:0};});
  assert.ok(packet.evidence.some(e=>e.text.includes('HIDDEN-IN-PLAIN-SIGHT')));
});

test('release is idempotent, parent-bound, and frozen independently per model track',async()=>{
  const db=database();
  try {
    const options={releaseId:'intake',expectedVersion:0};
    const first=await enqueueRevision(db,'track',input.incident,model,input.documents,[],options);
    const second=await enqueueRevision(db,'track',input.incident,model,input.documents,[],options);
    assert.equal(first.version,1);assert.equal(second.version,1);assert.equal(second.replayed,true);
    await assert.rejects(enqueueRevision(db,'track','Changed incident',model,input.documents,[],options),/different payload/);
    await assert.rejects(enqueueRevision(db,'track',input.incident,model,input.documents,[],{releaseId:'late',expectedVersion:0}),/stale/);
    await enqueueRevision(db,'other',input.incident,model,input.documents,[],options);
    assert.equal((await latestInput(db,'other')).row.number,1);
    assert.equal((await latestInput(db,'track')).input.release.trackId,'track');
  }finally{db.close();}
});

test('private/future/cross-model source canaries are rejected before registration or queueing',async()=>{
  const db=database();
  try {
    for(const extra of [{visibility:'controller-only'},{visibility:'future'},{trackId:'other'},{introducedVersion:2}]) {
      const docs=[{...document('canary','NEVER_EXPOSE_CONTROLLER_TRUTH'),...extra}];
      await assert.rejects(enqueueRevision(db,'track','incident',model,docs),/Controller-only|different model track|future evidence/);
    }
    await assert.rejects(registerSources({...input,documents:[{...input.documents[0],visibility:'controller-only'}]}),/Controller-only/);
    assert.equal((await db.prepare('SELECT COUNT(*) AS n FROM engine_runs').first()).n,0);
  }finally{db.close();}
});

test('experiment export preserves committed snapshots, prompts, original text and raw outputs without keys',async()=>{
  const db=database(),store=new D1EngineStore(db);
  try {
    await enqueueRevision(db,'track',input.incident,{...model,apiKey:'SECRET_DO_NOT_EXPORT'},input.documents);
    await drain(store,fixtureRunner([]));
    const exported=await exportExperiment(db,'track'),v=exported.versions[0];
    assert.equal(v.input.documents[0].extractedText,input.documents[0].extractedText);
    assert.ok(v.calls.some(c=>c.request?.system&&c.result?.output));assert.equal(v.snapshot.investigationPosition.ready,true);
    assert.equal(JSON.stringify(exported).includes('SECRET_DO_NOT_EXPORT'),false);
    assert.deepEqual(redactSecrets({apiKey:'secret',nested:{authorization:'Bearer secret'}}),{apiKey:'[REDACTED]',nested:{authorization:'[REDACTED]'}});
  }finally{db.close();}
});

test('generic execution errors are not automatically blamed on the model',()=>{
  assert.equal(failureCategory(Error('Unexpected reducer failure')),'unattributed');
  assert.equal(failureCategory(new TaskContextError('Context overflow')),'harness');
  assert.equal(failureCategory(Error('ECONNREFUSED')),'environment');
});

test('durable post-review revision corrects a timestamp and independently rechecks the corrected claim',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[],runner=fixtureRunner(log);
  try {
    await enqueueRevision(db,'track',input.incident,model,input.documents);
    await drain(store,async request=>{
      const result=await runner(request),p=request.evidencePacket;
      if(request.schemaName==='try7_read'&&p.evidence[0].text.includes('4.5'))result.output.findings[0].statement='Gauge P1 indicated 4.5 bar at 11:00.';
      if(request.schemaName==='try7_review'&&p.target.statement.includes('11:00')) {
        const source=p.evidence.find(e=>e.text.includes('4.5'));
        Object.assign(result.output,{relation:'contradicted',reason:'The original timestamp is 10:00, not 11:00.',
          evidence:[{source:source.ref,lines:[1]}]});
      }
      if(request.schemaName==='try7_revise') {
        const f=p.notebook.find(f=>f.statement.includes('11:00')),source=p.evidence.find(e=>e.text.includes('4.5'));
        result.output.corrections=[{finding:f.ref,expectedRevision:f.revision,statement:'Gauge P1 indicated 4.5 bar at 10:00.',subject:'P1',predicate:'indicated',location:'',time:'10:00',unit:'bar',qualifiers:'',references:[source.ref],reason:'Use the original timestamp.'}];
        result.output.impacts=p.impactTargets.map(t=>({target:t.target,action:t.target===f.ref?'correct':'retain',reason:'Apply the source-bound correction; retain unrelated observations.',findings:[f.ref]}));
        result.output.summary='The reported movement remains unexplained; the gauge observation is at 10:00.';
      }
      return result;
    });
    const s=await savedState(db),f=s.findings.find(f=>f.statement.includes('4.5'));
    assert.equal(f.statement,'Gauge P1 indicated 4.5 bar at 10:00.');assert.equal(f.status,'supported');assert.equal(f.revision,2);
    assert.equal(s.investigation.ready,true);assert.equal(s.quarantine.length,0);assert.equal(s.investigation.pendingImpacts.length,0);
    const reviewCalls=log.filter(r=>r.schemaName==='try7_review'&&r.evidencePacket.target.statement.includes('4.5'));
    assert.equal(reviewCalls.length,2);assert.ok(reviewCalls[0].evidencePacket.target.statement.includes('11:00'));assert.ok(reviewCalls[1].evidencePacket.target.statement.includes('10:00'));
    const exported=await exportExperiment(db,'track');assert.ok(exported.versions[0].snapshot.causalBoard.nodes.some(n=>n.label===f.statement));
  }finally{db.close();}
});

test('joint condition requirements are distinct from an ordinary pair of arrows',async()=>{
  const db=database(),store=new D1EngineStore(db);
  try {
    await enqueueRevision(db,'track',input.incident,model,input.documents);await drain(store,fixtureRunner([]));
    const s=await savedState(db),t=task('connect'),r=investigationBase(s,t).refs;
    await applyInvestigationTask(s,t,{edges:[{from:'F1',to:'EVENT',type:'enabled',rationale:'Test joint mechanism',counterfactual:'Both conditions would be required.',alternative:'Another mechanism',gap:'Proposed only',findings:[],jointConditions:['F1','F2']}],withdrawnEdges:[],nodeRequests:[],decision},r);
    const edge=s.relationships.find(e=>e.jointConditions?.length);
    assert.equal(edge.jointConditions.length,2);assert.ok(edge.jointConditions.every(id=>edge.findingIds.includes(id)));assert.equal(edge.status,'proposed');
    assert.deepEqual(project(s,input,'completed').causalBoard.edges.find(e=>e.id===edge.id).jointConditions,edge.jointConditions);
  }finally{db.close();}
});

test('branch split retains the predecessor and explicit successor lineage',async()=>{
  const db=database(),store=new D1EngineStore(db);
  try {
    await enqueueRevision(db,'track',input.incident,model,input.documents);await drain(store,fixtureRunner([]));
    const s=await savedState(db),t=task('refine'),r=investigationBase(s,t).refs;
    const old=s.investigation.branches[0],branch={...old,supporting:['F1'],opposing:[],replaces:[old.id]};
    await applyInvestigationTask(s,t,{summary:s.summary,focalEvent:s.focalEvent,normalState:'Unknown',eventState:'Reported',tags:[],nodes:[],edges:[],
      branches:[{...branch,id:'alternative-a',title:'First possibility'},{...branch,id:'alternative-b',title:'Second possibility'}],consultations:[],directions:[],retiredNodes:[],withdrawnEdges:[],decision},r);
    assert.equal(old.status,'superseded');assert.equal(s.investigation.branches.length,3);
    assert.ok(s.investigation.branches.filter(b=>b.id!==old.id).every(b=>b.replaces.includes(old.id)));
  }finally{db.close();}
});

test('archive includes exact original bytes and marks inaccessible originals explicitly',async()=>{
  const db=database();
  try {
    await enqueueRevision(db,'track',input.incident,model,input.documents);
    const body=new TextEncoder().encode(input.documents[0].extractedText);
    const archive=await exportArchive(db,'track',async key=>key===input.documents[0].fileKey?{arrayBuffer:async()=>body.buffer}:null);
    const files=unzipSync(archive.bytes),manifest=JSON.parse(strFromU8(files['experiment.json']));
    assert.equal(manifest.originalFiles.status,'partial');
    assert.equal(manifest.originalFiles.records.filter(r=>!r.archivePath).length,1);
    assert.equal(strFromU8(files[manifest.originalFiles.records[0].archivePath]),input.documents[0].extractedText);
    const denied=await exportArchive(db,'track',async()=>null);assert.ok(denied.manifest.originalFiles.records.every(r=>r.limitation));
  }finally{db.close();}
});

test('response directions reuse exact question identities and parts without printing IDs or losing the new purpose',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s),t=task('respond');
  const id=ingestQuestion(s,task('consult'),question(),r),q=s.questions[0];r.questions.set('Q1',id);
  bindQuestion(q,t,{parts:['Pressure','Calibration']});
  s.investigation.branches.push({id:'branch'});
  const direction={branch:'branch',question:'Q1',decision:'Check instrument validity',subject:q.subject,location:q.location,time:q.time,
    parts:q.parts.map(p=>p.id),evidenceNeeded:'Measurement',ifPresent:'Compare measurement',ifAbsent:'Keep unknown',priority:'discriminating',findings:[]};
  await applyInvestigationTask(s,t,{responses:[],directions:[direction],decision},r);
  assert.equal(s.questions.length,1);assert.equal(q.text,question().text);assert.deepEqual(q.parts.map(p=>p.text),['Pressure','Calibration']);
  assert.ok(q.subscriptions.some(sub=>sub.decision==='Check instrument validity'));
  await applyInvestigationTask(s,t,{responses:[],directions:[{...direction,existingQuestion:'Q1',question:q.text}],decision},r);
  assert.equal(s.questions.length,1);assert.equal(s.quarantine.length,0);
  await applyInvestigationTask(s,t,{responses:[],directions:[{...direction,location:'Different bay'}],decision},r);
  assert.equal(s.questions.length,1);assert.match(s.quarantine.at(-1).reason,/scope/);
});

test('adding a genuinely new part reopens search and cannot leave an answered badge',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s),t=task('consult');
  ingestQuestion(s,t,question(),r);const q=s.questions[0];
  q.answerRevision=1;q.answer='4.5 bar';q.status='answered';q.answerCompleteness='answered';q.inventory='searched';
  bindQuestion(q,t,{parts:['Gauge calibration']});
  assert.equal(q.status,'partial');assert.equal(q.answerCompleteness,'partial');assert.equal(q.inventory,'');assert.equal(q.answer,'4.5 bar');
});

test('reference-only checkpoint recovery is explicit, idempotent, and never changes causal verdicts',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s),t=task('consult');
  const id=ingestQuestion(s,t,question(),r),canonical=s.questions[0];r.questions.set('Q1',id);
  bindQuestion(canonical,t,{parts:['Pressure','Calibration']});
  ingestQuestion(s,t,{...question('Different decision'),text:'Q1'},r);const duplicate=s.questions[1];
  bindQuestion(duplicate,t,{parts:canonical.parts.map(p=>p.id)});
  s.investigation.directions=[{questionId:canonical.id,branchIds:['a']},{questionId:duplicate.id,branchIds:['b']}];
  const verdicts=JSON.stringify([s.findings,s.propositions,s.relationships]);
  recoverReferenceQuestions(s);
  assert.equal(duplicate.coveredBy,canonical.id);assert.equal(duplicate.text,canonical.text);
  assert.deepEqual(canonical.parts.map(p=>p.text),['Pressure','Calibration']);
  assert.ok(canonical.subscriptions.some(sub=>sub.decision==='Different decision'));
  assert.equal(JSON.stringify([s.findings,s.propositions,s.relationships]),verdicts);
  assert.match(s.changes.at(-1).before,/⟦question:/);assert.equal(project(s,input,'running').investigationPosition.directions.length,1);
  const count=s.changes.length;recoverReferenceQuestions(s);assert.equal(s.changes.length,count);
});

test('answer and receipt grammars constrain assigned IDs without hiding other canonical equivalence candidates',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s);
  const one=ingestQuestion(s,task('consult'),question('First decision'),r);
  const two=ingestQuestion(s,task('consult'),question('Second decision'),r);
  s.investigation.directions=[{questionId:one,branchIds:[]},{questionId:two,branchIds:[]}];
  let request;
  const runner=async req=>{request=req;return {output:{decision},durationMs:0};};
  await executeTask(s,task('resolve','resolve','answer-fetching',[two]),model,'track',{cached:async()=>null},runner);
  assert.equal(request.evidencePacket.questions.length,2);assert.deepEqual(request.evidencePacket.assignedQuestions,['Q2']);
  const answer={question:'Q2',status:'covered',answer:'',coverage:[],findings:[],references:[],equivalentTo:'Q1',evidenceNeeded:'Same observation, distinct decisions.'};
  assert.equal(request.schema.safeParse({answers:[answer],decision}).success,true);
  assert.equal(request.schema.safeParse({answers:[{...answer,question:'Q1'}],decision}).success,false);
  assert.equal(request.schema.safeParse({answers:[answer,answer],decision}).success,false);
  await executeTask(s,task('respond','respond','causal-analysis',[two]),model,'track',{cached:async()=>null},runner);
  const response={question:'Q2',answerRevision:1,implication:'Still unresolved.'};
  assert.equal(request.schema.safeParse({responses:[response],directions:[],decision}).success,true);
  assert.equal(request.schema.safeParse({responses:[{...response,question:'Q1'}],directions:[],decision}).success,false);
});

test('rejected corrections cannot publish the model claim that those changes succeeded',async()=>{
  const s=await stateWithNode(),r=refsFor(s),f=s.findings[0];s.summary='Prior incident summary.';
  await applyInvestigationTask(s,task('revise','revision','causal-analysis',[f.id]),{
    corrections:[{finding:'F1',expectedRevision:99,statement:'An unsupported replacement.',subject:'P1',predicate:'indicated',location:'',time:'',unit:'',qualifiers:'',references:['S2'],reason:'Test stale update.'}],
    branches:[],impacts:[{target:'F1',action:'retain',reason:'Retain the original.',findings:['F1']}],nodes:[{finding:'F1',type:'condition',reason:'Test proposal.'}],retiredNodes:[],withdrawnEdges:[],directions:[],
    summary:'All corrections succeeded.',decision:{summary:'Revision complete.'}
  },r);
  assert.match(s.summary,/only partly admitted/);assert.equal(s.investigation.proposedNarrative.summary,'All corrections succeeded.');
  assert.equal(f.revision,1);assert.match(f.statement,/4.5 bar/);assert.equal(s.quarantine.length,1);
  const snapshot=project(s,input,'partial');assert.equal(snapshot.structuredIncident.summary,s.summary);
  assert.equal(snapshot.investigationPosition.proposedNarrative.reason,'Revision complete.');
});

test('revision grammar binds the current finding revision instead of asking the model to invent bookkeeping',async()=>{
  const s=await stateWithNode();let request;
  await executeTask(s,task('revise','revise','causal-analysis',[s.findings[0].id]),model,'track',{cached:async()=>null},async req=>{request=req;return {output:{decision},durationMs:0};});
  const correction={finding:'F1',expectedRevision:1,statement:'A proposed correction.',subject:'',predicate:'',location:'',time:'',unit:'',qualifiers:'',references:['S2'],reason:'Test grammar, not factual acceptance.'};
  const base={corrections:[correction],branches:[],impacts:[],nodes:[],retiredNodes:[],withdrawnEdges:[],directions:[],summary:'Proposed only',decision};
  assert.equal(request.schema.safeParse(base).success,true);
  assert.equal(request.schema.safeParse({...base,corrections:[{...correction,expectedRevision:2}]}).success,false);
});

test('an owner subscribed during revision receives the existing answer before publication',async()=>{
  const s=await initializeState(input,1,null),r=refsFor(s);
  const id=ingestQuestion(s,task('review','review','claim-review'),question(),r),q=s.questions[0];
  q.answerRevision=1;queueDeliveries(q);q.deliveries[0].status='received';
  q.owners.push('causal-analysis');bindQuestion(q,task('revise'),{});queueDeliveries(q);
  s.phase=8;s.investigation.settleStarted=true;
  const next=await planNext(s);
  assert.equal(next.kind,'respond');assert.equal(next.owner,'causal-analysis');assert.deepEqual(next.targetIds,[id]);
  r.questions.set('Q1',id);
  await applyInvestigationTask(s,next,{responses:[{question:'Q1',answerRevision:1,implication:'No new evidence; retain uncertainty.'}],directions:[],decision},r);
  assert.ok(q.deliveries.every(d=>d.status==='received'));
});

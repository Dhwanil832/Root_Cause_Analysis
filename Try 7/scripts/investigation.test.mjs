import test from 'node:test';
import assert from 'node:assert/strict';
import { database, model, cases, fixtureRunner, drain, savedState, finding, direction } from './investigation-test-support.mjs';
import { D1EngineStore } from '../src/engine/tasks/d1-store.ts';
import { enqueueRevision, engineVersions, retryFailedTasks } from '../src/server/engine-repository.ts';
import { workerStep } from '../src/engine/tasks/worker.ts';
import { initializeState, planNext } from '../src/engine/tasks/planner.ts';
import { investigationBase } from '../src/engine/investigation/context.ts';
import { project } from '../src/engine/board/projection.ts';
import { applyInvestigationTask } from '../src/engine/investigation/apply.ts';
import { ingestFinding } from '../src/engine/records.ts';
import { migrateContinuousExecution } from '../src/server/engine-migration.ts';

for (const [index, sample] of cases.entries()) test(`V1→V2 publishes evidence-led positions, case ${index+1}; original version immutable`, async () => {
  const db=database(), store=new D1EngineStore(db), log=[];
  try {
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    await drain(store,fixtureRunner(log));
    const [v1]=await engineVersions(db,'track'), state1=await savedState(db);
    assert.equal(v1.executionStatus,'completed', JSON.stringify(v1.analysis.stageErrors));
    assert.equal(state1.findings.length,3, 'Only original readers produce findings.');
    assert.equal(state1.investigation.readingNotes.length,3);
    assert.equal(state1.tasks.filter(t=>t.kind==='review').length,2,'Background does not trigger review.');
    assert.equal(state1.tasks.filter(t=>t.kind==='consult').length,1);
    assert.equal(state1.tasks.filter(t=>t.kind==='resolve').length,1);
    assert.ok(state1.tasks.findIndex(t=>t.kind==='frame')<state1.tasks.findIndex(t=>t.kind==='consult'));
    assert.ok(state1.propositions.length>0 && state1.relationships.length>0);
    assert.equal(v1.analysis.investigationPosition.ready,true);
    assert.equal(v1.analysis.status,'awaiting-evidence');
    assert.ok(!state1.tasks.some(t=>['tag','specialist','broker','answer','causal','interpret'].includes(t.kind)));
    const first=JSON.stringify(v1), ids=state1.findings.map(f=>f.id), q=state1.investigation.directions[0].questionId;
    await enqueueRevision(db,'track',sample.incident,model,sample.documents,[{questionId:q,text:sample.update,answeredAt:'2026-09-20T01:00:00Z'}]);
    const boundary=log.length;
    await drain(store,fixtureRunner(log));
    const versions=await engineVersions(db,'track'), state2=await savedState(db);
    assert.equal(versions[1].executionStatus,'completed',JSON.stringify(versions[1].analysis.stageErrors));
    assert.equal(JSON.stringify(versions[0]),first);
    assert.equal(state2.findings.length,4); assert.ok(ids.every(id=>state2.findings.some(f=>f.id===id)));
    assert.equal(log.slice(boundary).filter(r=>r.schemaName==='try7_read').length,1,'Only new answer is read.');
    assert.equal(state2.investigation.branches[0].status,'disfavored');
    assert.ok(state2.questions.find(q2=>q2.id===q).answer.includes(sample.update));
    assert.equal(versions[1].analysis.investigationPosition.reusedSourceSpans,3);
  } finally { db.close(); }
});

test('no fixed question-count quota; 17 directions share one branch search without expanding facts',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[],sample=cases[0];
  try {
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    await drain(store,fixtureRunner(log,{questionCount:17,noConsult:true}));
    const s=await savedState(db);
    assert.equal(s.investigation.directions.length,17);assert.equal(s.findings.length,3);
    assert.equal(s.tasks.filter(t=>t.kind==='resolve').length,1);assert.equal(s.investigation.ready,true);
  }finally{db.close();}
});

test('failed selected claim leaves an honest partial board; independent connection still checked',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[],sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    await drain(store,fixtureRunner(log,{fail:r=>r.schemaName==='try7_review'&&r.evidencePacket.target.statement.includes('4.5')}));
    const [v]=await engineVersions(db,'track'),s=await savedState(db);
    assert.equal(v.executionStatus,'partial');assert.equal(s.investigation.ready,true);
    assert.ok(s.propositions.some(p=>p.status==='supported'));assert.ok(s.propositions.some(p=>p.status==='proposed'));
    assert.ok(s.relationships.some(e=>e.status==='unknown'));assert.ok(s.relationships.some(e=>e.status==='supported'));
  }finally{db.close();}
});

test('failed optional consultation publishes partial position and retains concrete requests',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    await drain(store,fixtureRunner([],{fail:r=>r.schemaName==='try7_consult'}));
    const [v]=await engineVersions(db,'track');
    assert.equal(v.executionStatus,'partial');assert.ok(v.analysis.investigationPosition.branches.length);
    assert.ok(v.analysis.questions.length);assert.ok(v.analysis.causalBoard.nodes.length>1);
  }finally{db.close();}
});

test('failed framing stops before specialists; recovery retains failure audit without rereading',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0],log=[];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    await drain(store,fixtureRunner(log,{fail:r=>r.schemaName==='try7_frame'}));
    let [v]=await engineVersions(db,'track');assert.equal(v.executionStatus,'paused');
    assert.ok(!log.some(r=>r.schemaName==='try7_consult'));
    await retryFailedTasks(db,'track');const after=[];await drain(store,fixtureRunner(after));
    [v]=await engineVersions(db,'track');assert.equal(v.executionStatus,'partial');
    assert.equal(v.analysis.investigationPosition.ready,true);
    assert.ok(!after.some(r=>r.schemaName==='try7_read'));
  }finally{db.close();}
});

test('V2 reuses unchanged consultation; omitted prior branches are not silently discarded',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);await drain(store,fixtureRunner([]));
    const s1=await savedState(db),q=s1.investigation.directions[0].questionId;
    await enqueueRevision(db,'track',sample.incident,model,sample.documents,[{questionId:q,text:sample.update,answeredAt:'new'}]);
    await drain(store,fixtureRunner([],{omitOldBranch:true}));const s2=await savedState(db);
    assert.equal(s2.investigation.branches[0].id,s1.investigation.branches[0].id);
    assert.ok(s2.changes.some(c=>c.kind==='retained'&&c.targetId==='branch:mechanism'));
    assert.equal(s2.tasks.filter(t=>t.kind==='consult').length,0);
  }finally{db.close();}
});

test('same original assertion cannot multiply because generated subject labels differ',async()=>{
  const input={...cases[0],model,answers:[]},s=await initializeState(input,1,null),span=s.sources[0].spans[0];
  const refs={sources:new Map([['S1',span.id]]),findings:new Map(),questions:new Map()},t={id:'read-test',kind:'read',owner:'evidence-reading'};
  const id=ingestFinding(s,t,finding('Same complete scoped statement.'),refs);
  assert.equal(ingestFinding(s,t,{...finding('Same complete scoped statement.'),subject:'paraphrased subject'},refs),id);
  assert.equal(s.findings.length,1);
});

test('broker rejects coverage cycles; common answers preserve ownership and cannot inject new facts',async()=>{
  const s=await initializeState({...cases[0],model,answers:[]},1,null),span=s.sources[0].spans[0];
  s.investigation.branches=[{id:'b',title:'B',mechanism:'Unresolved',status:'open',supporting:[],opposing:[],gap:'Need evidence',changeReason:'Test',updatedVersion:1}];
  const base={summary:'Test',focalEvent:'Test',normalState:'',eventState:'',tags:[],nodes:[],edges:[],branches:[],consultations:[],directions:[direction('b',0),direction('b',1)],retiredNodes:[],withdrawnEdges:[],decision:{summary:'Test'}};
  await applyInvestigationTask(s,{kind:'frame',id:'map',owner:'causal-analysis'},base,{sources:new Map(),findings:new Map(),questions:new Map()});
  const [a,b]=s.questions;a.owners=['stored-energy'];b.owners=['equipment-tools'];
  const refs={sources:new Map([['S1',span.id]]),findings:new Map(),questions:new Map([['Q1',a.id],['Q2',b.id]])};
  await applyInvestigationTask(s,{id:'resolve',kind:'resolve',targetIds:[a.id,b.id],owner:'answer-fetching'},
    {answers:[{question:'Q1',status:'not-found',answer:'',findings:[],references:[],equivalentTo:null,evidenceNeeded:'Missing original.'},
      {question:'Q2',status:'covered',answer:'',findings:[],references:[],equivalentTo:'Q1',evidenceNeeded:'Equivalent scoped decision.'}],decision:{summary:'Test'}},refs);
  assert.equal(b.coveredBy,a.id);assert.deepEqual(a.owners,['stored-energy','equipment-tools']);assert.equal(s.findings.length,0);
  const before=s.quarantine.length;
  await applyInvestigationTask(s,{id:'bad',kind:'resolve',targetIds:[a.id],owner:'answer-fetching'},
    {answers:[{question:'Q1',status:'covered',answer:'',findings:[],references:[],equivalentTo:'Q2',evidenceNeeded:''}],decision:{summary:'Test'}},refs);
  assert.ok(s.quarantine.length>before);assert.equal(a.coveredBy,null);
});

test('model tracks and credentials remain isolated; stale leases cannot commit',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,{...model,apiKey:'never-store-this'},sample.documents);
    const first=await store.claim(Date.now(),1),second=await store.claim(Date.now()+20,90000);
    assert.notEqual(first.lease,second.lease);assert.equal(await store.save(first,first.generation,{}),false);
    await store.pause(second.id,'Test pause',second.lease);
    await retryFailedTasks(db,'track');await drain(store,fixtureRunner([]));
    const row=await db.prepare('SELECT input_json FROM engine_runs WHERE track_id=?').bind('track').first();assert.ok(!row.input_json.includes('never-store-this'));
    const cached=await db.prepare('SELECT cache_key FROM engine_task_cache WHERE track_id=? LIMIT 1').bind('track').first();assert.equal(await store.cached('other',cached.cache_key),null);
  }finally{db.close();}
});

test('map is visible before review and no arbitrary notebook item schedules a task',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0],log=[],runner=fixtureRunner(log);
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    for(let i=0;i<4;i++)await workerStep(store,async()=>model,runner);
    const [v]=await engineVersions(db,'track');
    assert.equal(v.executionStatus,'running');assert.ok(v.analysis.causalBoard.nodes.length>1);
    assert.ok(v.analysis.causalBoard.nodes.every(n=>!n.verified));
    assert.ok(!log.some(r=>r.schemaName==='try7_review'));
  }finally{db.close();}
});

test('Try 5 migration is explicitly disabled in Try 6',async()=>{
  await assert.rejects(()=>migrateContinuousExecution({},'old',1,'hash','reason'),/fresh model track/);
});

test('retirement is explicit: withdraw arrows, stop reviewing an obsolete node, retain original evidence',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);await drain(store,fixtureRunner([]));
    const s=await savedState(db),id=s.propositions[0].findingId;
    const t={id:'retire',kind:'refine',owner:'causal-analysis',targetIds:[]}, {refs}=investigationBase(s,t);
    const fref=[...refs.findings].find(([,f])=>f===id)[0];
    const raw={summary:'Revised position',focalEvent:s.focalEvent,normalState:'',eventState:'',tags:[],nodes:[],edges:[],branches:[],consultations:[],directions:[],
      retiredNodes:[{finding:fref,reason:'The observation no longer distinguishes active explanations.'}],
      withdrawnEdges:s.relationships.filter(e=>e.findingIds.includes(id)).map(e=>({id:e.id,reason:'The proposed mechanism was withdrawn.'})),decision:{summary:'Explicit withdrawal, not deletion.'}};
    await applyInvestigationTask(s,t,raw,refs);
    assert.ok(s.findings.some(f=>f.id===id));assert.ok(!s.investigation.selectedFindingIds.includes(id));
    const view=project(s,{...sample,model,answers:[]},'completed');assert.ok(!view.causalBoard.nodes.some(n=>n.claimIds?.includes(id)));
    s.phase=5;s.tasks=[];await planNext(s);assert.ok(!s.tasks.some(t=>t.kind==='review'&&t.targetIds.includes(id)));
    assert.ok(s.changes.some(c=>c.kind==='rejected'));
  }finally{db.close();}
});

test('empty framing and unsupported answer text cannot masquerade as completed knowledge',async()=>{
  const s=await initializeState({...cases[0],model,answers:[]},1,null), refs={sources:new Map(),findings:new Map(),questions:new Map()};
  const empty={summary:'No useful map',focalEvent:'Reported event',normalState:'',eventState:'',tags:[],nodes:[],edges:[],branches:[],consultations:[],directions:[],retiredNodes:[],withdrawnEdges:[],decision:{summary:'No evidence'}};
  await assert.rejects(()=>applyInvestigationTask(s,{id:'empty',kind:'frame',owner:'causal-analysis'},empty,refs),/No usable investigative position/);
  s.investigation.branches=[{id:'b',title:'B',mechanism:'Possible',status:'open',supporting:[],opposing:[],gap:'Unknown',changeReason:'Test',updatedVersion:1}];
  await applyInvestigationTask(s,{id:'map',kind:'frame',owner:'causal-analysis'},{...empty,directions:[direction('b')]},refs);
  const q=s.questions[0];refs.questions.set('Q1',q.id);
  await applyInvestigationTask(s,{id:'answer',kind:'resolve',owner:'answer-fetching',targetIds:[q.id]},
    {answers:[{question:'Q1',status:'answered',answer:'Confident but uncited answer',findings:[],references:[],equivalentTo:null,evidenceNeeded:''}],decision:{summary:'Test'}},refs);
  assert.equal(q.status,'awaiting-user');assert.equal(q.answer,'');assert.equal(s.findings.length,0);
});

test('new sources revoke stale map support; removed sources retain addressable IDs for retirement',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);await drain(store,fixtureRunner([]));
    const old=await savedState(db),pressure=old.findings.find(f=>f.statement.includes('4.5'));
    const next=await initializeState({...sample,documents:sample.documents.filter(d=>d.id!=='pressure'),model,answers:[]},2,old);
    const finding=next.findings.find(f=>f.id===pressure.id);assert.equal(finding.spanIds.length,0);assert.notEqual(finding.status,'supported');
    assert.ok(next.propositions.every(p=>p.status!=='supported'));
    const {base,refs}=investigationBase(next,{kind:'frame',targetIds:[],owner:'causal-analysis'});
    const local=[...refs.findings].find(([,id])=>id===finding.id)[0];
    assert.equal(base.notebook.find(f=>f.ref===local).sourceAvailable,false);
    assert.equal(old.findings.find(f=>f.id===pressure.id).status,'supported','Prior version is untouched.');
  }finally{db.close();}
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {database, model, cases, fixtureRunner, drain, savedState} from './investigation-test-support.mjs';
import {D1EngineStore} from '../src/engine/tasks/d1-store.ts';
import {enqueueRevision, engineVersions} from '../src/server/engine-repository.ts';
import {workerStep} from '../src/engine/tasks/worker.ts';
import {readJSON, putJSON, putState} from '../src/engine/tasks/artifacts.ts';
import {digest} from '../src/engine/identity.ts';
import {recoverPartialFrame} from '../src/server/frame-recovery.ts';
import {investigationSchema} from '../src/engine/investigation/contracts.ts';
import {investigationBase} from '../src/engine/investigation/context.ts';
import {applyInvestigationTask} from '../src/engine/investigation/apply.ts';
import {currentBoardPremiseIds, retireObsoleteQueuedReviews} from '../src/engine/investigation/review-dependencies.ts';

const edge = {from:'F1',to:'F3',type:'preceded',rationale:'Test ordering proposal',counterfactual:'',alternative:'',gap:'Not established',findings:[]};
test('Try 7 refuses legacy frame migration and preserves the original paused checkpoint', async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0],log=[];
  try {
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    for(let i=0;i<4;i++)await workerStep(store,async()=>model,fixtureRunner(log));
    const row=await db.prepare('SELECT * FROM engine_runs WHERE track_id=?').bind('track').first();
    const state=await savedState(db),frame=state.tasks.find(t=>t.kind==='frame');
    const reads=JSON.stringify(state.tasks.filter(t=>t.kind==='read')),facts=JSON.stringify(state.findings);
    const input=await readJSON(db,row.input_json);input.engineVersion='try6.0.0';
    const call=await db.prepare('SELECT * FROM engine_calls WHERE id=?').bind(frame.traceId).first();
    const result=await readJSON(db,call.result_json);result.output.edges=[edge];
    await db.prepare("UPDATE engine_calls SET status='failed',result_json=? WHERE id=?").bind(await putJSON(db,result),call.id).run();
    frame.status='failed';frame.error='Invalid endpoint';state.pauseReason='Prerequisite frame failed';
    state.quarantine.push({taskId:frame.id,item:edge,reason:'Relationship endpoints must be distinct selected observations or EVENT.'});
    await db.prepare("UPDATE engine_runs SET status='paused',state_json=?,input_json=?,lease_until=0 WHERE id=?")
      .bind(await putState(db,state),await putJSON(db,input),row.id).run();
    const paused=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first();
    const hash=await digest([paused.input_json,paused.state_json,paused.snapshot_json]);
    await assert.rejects(recoverPartialFrame(db,row.id,row.generation+1,hash,'Test authorization'),/exact idle/);
    await assert.rejects(recoverPartialFrame(db,row.id,row.generation,'0'.repeat(64),'Test authorization'),/hash/);
    await assert.rejects(recoverPartialFrame(db,row.id,row.generation,hash,'Test authorization'),/compatible/);
    const restored=await savedState(db);
    assert.equal(JSON.stringify(restored.tasks.filter(t=>t.kind==='read')),reads);
    assert.equal(JSON.stringify(restored.findings),facts);
    assert.deepEqual(restored.quarantine,state.quarantine);
    assert.equal(restored.tasks.find(t=>t.id===frame.id).status,'failed');
    assert.equal(restored.executionMigrations,undefined);
    const [v]=await engineVersions(db,'track');assert.equal(v.executionStatus,'paused');
    const retained=await db.prepare('SELECT * FROM engine_calls WHERE id=?').bind(call.id).first();
    assert.equal(retained.status,'failed');assert.deepEqual((await readJSON(db,retained.result_json)).output.edges,[edge]);
  }finally{db.close();}
});

test('connection catalog excludes supporting premises; rejected siblings and node requests do not invent nodes',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    for(let i=0;i<4;i++)await workerStep(store,async()=>model,fixtureRunner([]));
    const state=await savedState(db),task={...state.tasks.at(-1),kind:'connect',id:'test-connect'};
    state.investigation.selectedFindingIds.push(state.findings[2].id); // supporting premise, NOT a node
    const {base,refs}=investigationBase(state,task);
    assert.deepEqual(base.boardNodes.map(n=>n.ref),['F1','F2']);
    const invalid={edges:[edge],withdrawnEdges:[],nodeRequests:[],decision:{summary:'Test'}};
    assert.equal(investigationSchema('connect',[...refs.findings.keys()],[],[],['F1','F2']).safeParse(invalid).success,false);
    const count=state.propositions.length;
    await applyInvestigationTask(state,task,{...invalid,edges:[{...edge,to:'EVENT'},edge],nodeRequests:[{finding:'F3',reason:'Consider in next map'}]},refs);
    assert.equal(state.relationships.length,1);assert.equal(state.quarantine.length,1);
    assert.equal(state.propositions.length,count);assert.equal(state.investigation.nodeRequests.length,1);
  }finally{db.close();}
});

test('new map grammar separates selection from arrows and unusable frames still pause',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0],runner=fixtureRunner([]);
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    await drain(store,async request=>{
      const result=await runner(request);
      if(request.schemaName==='try7_frame'){
        assert.equal(request.schema.safeParse({...result.output,edges:[edge]}).success,false);
        result.output.nodes=[];result.output.branches=[];result.output.directions=[];result.output.consultations=[];
      }
      return result;
    });
    const [v]=await engineVersions(db,'track');assert.equal(v.executionStatus,'paused');
    const state=await savedState(db);assert.ok(!state.tasks.some(t=>t.kind==='connect'||t.kind==='resolve'));
  }finally{db.close();}
});

test('usable frame with a rejected individual node continues to partial publication',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0],runner=fixtureRunner([]);
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    // The source reader labels a speculative statement as a hypothesis. A mapper
    // can reference it, but the evidence gate must reject it as a factual node.
    await drain(store,async request=>{
      const result=await runner(request);
      if(request.schemaName==='try7_read'&&request.evidencePacket.evidence[0].text.includes('4.5'))
        result.output.findings[0].kind='hypothesis';
      return result;
    });
    const [v]=await engineVersions(db,'track'),state=await savedState(db);
    assert.equal(v.executionStatus,'partial');assert.equal(state.investigation.ready,true);
    const frame=state.tasks.find(t=>t.kind==='frame');assert.equal(frame.status,'completed');assert.equal(frame.partial,true);
    assert.ok(state.quarantine.some(q=>q.taskId===frame.id));
    assert.ok(!state.propositions.some(p=>state.findings.find(f=>f.id===p.findingId)?.kind==='hypothesis'));
  }finally{db.close();}
});

test('obsolete review pruning follows live dependencies, not a count limit, and never changes evidence verdicts',async()=>{
  const db=database(),store=new D1EngineStore(db),sample=cases[0];
  try{
    await enqueueRevision(db,'track',sample.incident,model,sample.documents);
    for(let i=0;i<4;i++)await workerStep(store,async()=>model,fixtureRunner([]));
    const state=await savedState(db),unused=state.findings[2].id,used=state.findings[0].id;
    const template=state.tasks[0],tasks=[
      {...template,id:'obsolete',kind:'review',targetIds:[unused],status:'queued'},
      {...template,id:'completed',kind:'review',targetIds:[unused],status:'completed'},
      {...template,id:'inflight',kind:'review',targetIds:[unused],status:'running'},
      {...template,id:'needed',kind:'review',targetIds:[used],status:'queued'},
    ];
    state.tasks.push(...tasks);state.investigation.selectedFindingIds.push(unused);
    const findings=JSON.stringify(state.findings);
    retireObsoleteQueuedReviews(state);
    assert.equal(tasks[0].status,'superseded');assert.equal(tasks[1].status,'completed');assert.equal(tasks[2].status,'running');assert.equal(tasks[3].status,'queued');
    assert.equal(JSON.stringify(state.findings),findings);assert.ok(!currentBoardPremiseIds(state).includes(unused));
    state.relationships.push({id:'edge',proposedBy:['map'],findingIds:[used,unused]});
    tasks[0].status='queued';retireObsoleteQueuedReviews(state);
    assert.equal(tasks[0].status,'queued','A supporting premise need not itself be a node to require review.');
    assert.ok(state.investigation.selectedFindingIds.includes(unused));
  }finally{db.close();}
});

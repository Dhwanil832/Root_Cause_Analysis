import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { textBlocks, registerSources } from '../src/knowledge/sources/registry.ts';
import { EvidenceIndex } from '../src/knowledge/retrieval/index.ts';
import { planContext } from '../src/engine/context/planner.ts';
import { readSchema, taskSchema } from '../src/engine/contracts.ts';
import { putJSON,readJSON,readState,putState } from '../src/engine/tasks/artifacts.ts';
import { migrateContinuousExecution } from '../src/server/engine-migration.ts';
import { activateReviewFormatting } from '../src/server/review-formatting-migration.ts';
import { checkpointVersion } from '../src/engine/tasks/checkpoint-version.ts';
import { digest } from '../src/engine/identity.ts';
import { ollamaProvider } from '../src/providers/ollama.ts';
import { StreamRepetitionGuard, StreamRepetitionError, STREAM_REPETITION_POLICY } from '../src/providers/stream-repetition.ts';
import { D1EngineStore } from '../src/engine/tasks/d1-store.ts';
import { enqueueRevision, engineVersions, retryFailedTasks } from '../src/server/engine-repository.ts';
import { workerStep } from '../src/engine/tasks/worker.ts';
import { ingestRows, ingestQuestion } from '../src/engine/records.ts';
import { initializeState, planNext } from '../src/engine/tasks/planner.ts';
import { applyQuestionTask, reconcileAnswers } from '../src/stages/question-broker/task.ts';
import { applyBoardTask } from '../src/engine/board/changes.ts';
import { storyPassages } from '../src/story-agent/contracts.ts';
import { storyPacket } from '../src/story-agent/run.ts';
import { storyWorkerStep } from '../src/story-agent/worker.ts';
import { executeTask } from '../src/engine/tasks/executor.ts';
import { assessLiteralClaim as assessClaim } from '../src/engine/review/literal-decision.ts';
import { applyEvidenceTask } from '../src/stages/evidence-reading/task.ts';
import { CLAIM_REVIEW_POLICY } from '../src/engine/review/literal-contract.ts';
import { REVIEW_FORMATTING_POLICY, normalizeReviewFormatting } from '../src/engine/review/formatting.ts';
import { QWEN_REVIEW_SAMPLING } from '../src/engine/review/inference-profile.ts';
import { project } from '../src/engine/board/projection.ts';
import { bindCommentary } from '../src/engine/citations.ts';

// Real SQLite SQL/transactions with the same D1 interface used in production.
function database() {
  const sqlite = new DatabaseSync(':memory:');
  for (const name of fs.readdirSync(new URL('../drizzle/', import.meta.url)).filter(n => n.endsWith('.sql')).sort())
    sqlite.exec(fs.readFileSync(new URL('../drizzle/' + name, import.meta.url), 'utf8'));
  const db = {
    prepare(sql) { let values = []; return {
      bind(...bindings) {
        if(bindings.reduce((n,v)=>n+(typeof v==='string'?Buffer.byteLength(v):0),0)>2_000_000)throw new Error('D1_ERROR: string or blob too big: SQLITE_TOOBIG');
        values = bindings; return this;
      },
      async first() { return sqlite.prepare(sql).get(...values) || null; },
      async all() { return { results: sqlite.prepare(sql).all(...values), success: true, meta: {} }; },
      async run() { const r = sqlite.prepare(sql).run(...values); return { success: true, meta: { changes: Number(r.changes) }, results: [] }; },
    }; },
    async batch(statements) {
      sqlite.exec('BEGIN');
      try { const result = []; for (const s of statements) result.push(await s.run()); sqlite.exec('COMMIT'); return result; }
      catch(e) { sqlite.exec('ROLLBACK'); throw e; }
    },
    close() { sqlite.close(); },
  };
  return db;
}
const model = { id: 'ollama:test-only', name: 'test-only', provider: 'ollama', digest: 'frozen-test-digest', available: true, detail: 'Deterministic test adapter, not a model evaluation', contextWindow: 32768 };
const incident = 'During maintenance a carriage moved unexpectedly while the line was isolated. No injury was reported.';
function document(id, text) { return { id, scope: 'starter', title: id, fileName: id+'.md', fileKey: id, contentType: 'text/markdown', size: text.length, sha256: id,
  revision: '1', plant: 'Test', extractionStatus: 'ready', extractionNotes: '', extractedText: text, createdAt: '2026-09-18T00:00:00Z' }; }
const docs = [document('pressure', '# Measurements\n| Time | P-1 bar |\n|---|---|\n|09:54|6.8|\n|10:00|4.5|\nP-1 is the downstream measurement.')];
const input = { incident, model, answers: [], documents: docs };
const decision = { summary: 'Test fixture decision; not real RCA reasoning.' };
const row = (statement, ref='S1') => ({ statement, kind: 'observation', subject: statement, predicate: 'reported', location: 'test line', time: 'incident', unit: '',
  qualifiers: 'Reported in source', references: [ref], tags: ['stored-energy'], replaces: null });
function fixtureRunner(log, fail = () => false) {
  return async request => {
    log.push(request);
    if (fail(request)) throw new Error('Injected independent task failure');
    const p = request.evidencePacket, kind = request.schemaName.replace(/^try[567]_/, ''), ref = p.evidence?.[0]?.ref;
    let output;
    if (kind === 'read') output = { findings: [row(p.evidence[0].text.includes('6.8') ? 'P-1 recorded 6.8 bar at 09:54.' : 'The carriage moved during maintenance.', ref)], questions: [], decision };
    if (kind === 'understand') output = { summary: 'Reported carriage movement.', focalEvent: 'Carriage moved unexpectedly', normalState: 'Unknown', eventState: 'Maintenance', entities: [], questions: [], decision };
    if (kind === 'tag') output = { tags: [{ id: 'stored-energy', reason: 'Investigate movement energy.', references: ref ? [ref] : [] }], decision };
    if (kind === 'specialist') output = { findings: [], questions: [{ text: 'What restraint was present during maintenance?', intent: 'Establish restraint', decision: 'Determine whether movement was restrained.', subject: 'carriage', location: 'test line', time: 'incident', references: ref ? [ref] : [] }], decision };
    if (kind === 'broker') output = { equivalentTo: p.possibleDuplicates[0]?.ref || null, reason: 'Test duplicate.', decision };
    if (kind === 'answer') output = { status: 'not-found', answer: '', references: [], findings: [], evidenceRequest: 'Supply the restraint record.', decision };
    if (kind === 'review' || kind === 'verify') output = { status: 'supported', reason: 'Test adapter support.', supporting: ref ? [ref] : [], opposing: [], questions: [], decision };
    if(kind==='interpret')output={targetStatement:p.target.statement,parts:[{claimText:p.target.statement,claimType:'actual-state',
      assertion:p.target.statement,truthConditions:'Fixture truth condition',scope:{subject:'',location:'',time:''},ambiguities:[]}],decision};
    if (kind==='review')output={targetStatement:p.target.statement,claimType:'actual-state',evidenceConflicts:[],
      evidence:[{source:ref,lines:p.evidence[0].text.split('\n').flatMap((line,i)=>line.replace(/^\d+\|/,'').trim()?[i+1]:[])}],
      establishes:'Fixture assertion only, not a semantic evaluation.',relation:'entailed',missingPremises:[],reason:'Fixture evidence comparison.',questions:[],decision};
    if (kind === 'causal') output = { disposition: 'node', type: 'condition', label: p.findings[0].statement, detail: p.findings[0].statement, reason: 'Test adapter proposal.', references: ref ? [ref] : [],
      edges: [{ from: 'F1', to: 'EVENT', type: 'enabled', rationale: 'Fixture relationship, not scientific inference.', counterfactual: 'Fixture counterfactual.', alternative: 'Fixture alternative.', gap: '', references: ref ? [ref] : [] }], questions: [], decision };
    if (kind === 'actions') output = { actions: [{ title: 'Fixture action', description: 'Test only', type: 'engineering', ownerRole: 'Reviewer', completionEvidence: 'Fixture check', effectivenessCheck: 'Fixture followup' }], decision };
    request.schema.parse(output);
    return { output, durationMs: 1, engine: 'test-adapter', validation: 'valid', usage: { inputTokens: 100, outputTokens: 30 } };
  };
}
async function drain(store, runner) {
  for (let i = 0; i < 200; i++) { const r = await workerStep(store, async () => model, runner); if (r.idle) return; }
  throw new Error('Test watchdog: unexpected task-generation loop.');
}

test('lossless passages preserve decimal tables, newlines, headers, and exact offsets', async () => {
  const text = ('# Pressure\n| Time | bar |\n|---|---|\n' + '|09:54|6.8|\n'.repeat(25));
  const blocks = textBlocks(text, 90);
  assert.equal(blocks.map(b => b.text).join(''), text);
  for (const b of blocks) assert.equal(text.slice(b.start,b.end), b.text);
  assert.ok(blocks.some(b => b.tableHeader.includes('bar')));
  const one = await registerSources(input), two = await registerSources(input, one.sources);
  assert.equal(two.changed.length, 0);
  assert.deepEqual(two.sources, one.sources);
});

test('context is bounded with a growing archive and never drops required evidence', async () => {
  const all = [...docs, ...Array.from({length:148}, (_,i)=>document('d'+i, ('pressure valve condition ' + i+'\n').repeat(300)))];
  const registered = await registerSources({...input, documents: all});
  const index = new EvidenceIndex(registered.sources);
  const required = registered.sources.find(s=>s.id==='pressure').spans.map(s=>s.id);
  const packet = planContext({ model, system: 'Evidence only', schema: readSchema, base: {task:'test'}, index, query:'pressure valve', required });
  assert.ok(required.every(id=>packet.selected.some(s=>s.id===id)));
  assert.ok(packet.bytes <= (model.contextWindow-2048)*2);
  assert.ok(packet.omitted.length > 0);
  assert.throws(()=>planContext({ model, system:'', schema:readSchema, base:{}, index, query:'', required:['missing'] }), /missing/);
});

test('malformed sibling findings are quarantined without turning them into facts', async () => {
  const state = await initializeState(input,1,null);
  const span = state.sources[0].spans[0];
  const task = { id:'t', owner:'stored-energy', kind:'read' };
  ingestRows(state,task,{findings:[row('Good','S1'),row('Invalid','S999')],questions:[]},{sources:new Map([['S1',span.id]]),findings:new Map(),questions:new Map()});
  assert.equal(state.findings.length,1); assert.equal(state.quarantine.length,1); assert.equal(state.findings[0].status,'proposed');
});

test('durable SQL worker produces immutable V1/V2, preserves identities, and reuses calls', async () => {
  const db=database(), store=new D1EngineStore(db), log=[];
  await enqueueRevision(db,'track-a',incident,model,docs);
  await drain(store,fixtureRunner(log));
  const v1=(await engineVersions(db,'track-a'))[0];
  assert.equal(v1.executionStatus,'completed');
  assert.ok(v1.analysis.causalBoard.edges.length>0);
  const serialized=JSON.stringify(v1);
  const ids=v1.analysis.evidenceClaims.map(c=>c.id);
  await enqueueRevision(db,'track-a',incident,model,docs,[{questionId:'new-answer',text:'The maintenance record does not identify a restraint.',answeredAt:'2026-09-18T01:00:00Z'}]);
  await drain(store,fixtureRunner(log));
  const versions=await engineVersions(db,'track-a');
  assert.equal(versions.length,2); assert.equal(JSON.stringify(versions[0]),serialized);
  assert.ok(ids.every(id=>versions[1].analysis.evidenceClaims.some(c=>c.id===id)));
  assert.ok(versions[1].analysis.engineProgress.tasks.some(t=>t.reused));
  assert.equal(versions[1].executionStatus,'completed');
  db.close();
});

test('one failed task creates an honest partial snapshot while independent work completes', async () => {
  const db=database(), store=new D1EngineStore(db), log=[];
  await enqueueRevision(db,'track',incident,model,docs);
  await drain(store,fixtureRunner(log,r=>r.schemaName==='try5_review'&&r.evidencePacket.target.statement.includes('6.8')));
  const v=(await engineVersions(db,'track'))[0];
  assert.equal(v.executionStatus,'partial');
  assert.ok(v.analysis.engineProgress.tasks.some(t=>t.kind==='review'&&t.status==='failed'));
  assert.ok(v.analysis.engineProgress.tasks.some(t=>t.kind==='verify'&&t.status==='completed'));
  db.close();
});

test('leases reject stale commits and preserve per-track revision order', async () => {
  const db=database(), store=new D1EngineStore(db);
  await enqueueRevision(db,'track',incident,model,docs);
  await enqueueRevision(db,'track',incident,model,docs,[{questionId:'q',text:'Additional evidence.',answeredAt:'now'}]);
  const now=Date.now(), first=await store.claim(now,10);
  assert.equal(first.number,1);
  assert.equal(await store.claim(now+1,10),null);
  const recovered=await store.claim(now+20,10);
  assert.equal(recovered.number,1); assert.notEqual(first.lease,recovered.lease);
  assert.equal(await store.save(first,first.generation,{}),false);
  db.close();
});

test('task cache and credentials do not cross model tracks', async () => {
  const db=database();
  await enqueueRevision(db,'one',incident,{...model,apiKey:'DO-NOT-PERSIST'},docs);
  const row=await db.prepare('SELECT input_json FROM engine_runs WHERE track_id=?').bind('one').first();
  assert.ok(!row.input_json.includes('DO-NOT-PERSIST'));
  const store=new D1EngineStore(db); await drain(store,fixtureRunner([]));
  const entry=await db.prepare('SELECT cache_key FROM engine_task_cache WHERE track_id=? LIMIT 1').bind('one').first();
  assert.ok(entry); assert.equal(await store.cached('two',entry.cache_key),null);
  db.close();
});
test('partial answers stay partial after supported findings are routed to all owners', async () => {
  const state=await initializeState(input,1,null), span=state.sources[0].spans[0];
  const refs={sources:new Map([['S1',span.id]]),findings:new Map(),questions:new Map()};
  const id=ingestQuestion(state,{owner:'stored-energy'},{text:'Which restraints were fitted and inspected?',intent:'restraint',decision:'Verify both installation and inspection',subject:'carriage',location:'line',time:'incident',references:[]},refs);
  const task={id:'answer-task',owner:'answer-fetching',kind:'answer',targetIds:[id],evidenceIds:[span.id]};
  applyQuestionTask(state,task,{status:'partial',answer:'Installation reported; inspection unknown.',references:['S1'],findings:[row('Restraint installation was reported.')],evidenceRequest:'Inspection record still required.',decision},refs);
  state.findings.forEach(f=>f.status='supported');
  reconcileAnswers(state);
  assert.equal(state.questions[0].status,'partial');
  assert.ok(state.findings[0].owners.includes('stored-energy'));
});

test('a causal verifier cannot promote an unsupported premise; stale proposals are withdrawn',async()=>{
  const state=await initializeState(input,1,null), span=state.sources[0].spans[0], refs={sources:new Map([['S1',span.id]]),findings:new Map(),questions:new Map()};
  ingestRows(state,{id:'read',kind:'read',owner:'evidence-reading'},{findings:[row('Reported motion')],questions:[]},refs);
  const f=state.findings[0];refs.findings.set('F1',f.id);
  const causal={disposition:'node',type:'condition',label:'Condition: Reported motion',detail:'Report',reason:'test',references:['S1'],
    edges:[{from:'F1',to:'EVENT',type:'enabled',rationale:'test',counterfactual:'test',alternative:'test',gap:'',references:['S1']}],questions:[],decision};
  applyBoardTask(state,{id:'c',kind:'causal',owner:'causal-analysis',targetIds:[f.id]},causal,refs);
  const node=state.propositions[0], edge=state.relationships[0];
  assert.equal(node.label,'Reported motion');
  for(const target of [node,edge])applyBoardTask(state,{id:'v',kind:'verify',owner:'causal-verification',targetIds:[target.id]},
    {status:'supported',reason:'overconfident reviewer',supporting:['S1'],opposing:[],questions:[],decision},refs);
  assert.equal(node.status,'unknown');assert.equal(edge.status,'unknown');
  f.status='supported';
  applyBoardTask(state,{id:'c2',kind:'causal',owner:'causal-analysis',targetIds:[f.id]},{...causal,edges:[]},refs);
  assert.equal(edge.status,'unknown');assert.equal(edge.proposedBy.length,0);
});

test('provider outage pauses rather than exhausting every task; revisions wait and resume in order',async()=>{
  const db=database(),store=new D1EngineStore(db);
  await enqueueRevision(db,'paused-track',incident,model,docs);
  const result=await workerStep(store,async()=>model,async()=>{throw new Error('fetch failed: ECONNREFUSED');});
  assert.equal(result.status,'paused');
  await enqueueRevision(db,'paused-track',incident,model,docs,[{questionId:'q',text:'New evidence',answeredAt:'now'}]);
  assert.equal(await store.claim(Date.now(),90000),null);
  await retryFailedTasks(db,'paused-track');
  await drain(store,fixtureRunner([]));
  assert.deepEqual((await engineVersions(db,'paused-track')).map(v=>v.executionStatus),['completed','completed']);
  db.close();
});

test('story retrieval preserves decimals and excludes hidden/unavailable answer keys',()=>{
  const scenario={title:'Frozen test',hiddenTruth:'PRIVATE EXPECTED ROOT CAUSE MUST STAY PRIVATE',
    sources:[{id:'available',title:'Pressure record',sourceClass:'synthetic',available:true,text:'Pressure record: 6.8 bar at 09:54 and 4.5 bar at 10:00.'},
      {id:'secret',title:'Unavailable log',sourceClass:'withheld',available:false,text:'DO NOT RELEASE THIS SOURCE'}]};
  const passages=storyPassages(scenario);
  assert.ok(passages[0].quote.includes('6.8 bar'));
  const packet=storyPacket(model,scenario,{id:'q1',text:'What pressure readings were recorded?'},[]);
  assert.ok(!JSON.stringify(packet).includes(scenario.hiddenTruth));
  assert.ok(!JSON.stringify(packet).includes('DO NOT RELEASE'));
  assert.ok(packet.passageCatalog.length);
});

test('story tasks persist independently, retain valid answers, and retry only failed questions',async()=>{
  const db=database(),now=new Date().toISOString();
  const scenario={title:'Test world',hiddenTruth:'Private fixed facts for test only.',sources:[{id:'s',title:'Test evidence',sourceClass:'synthetic',text:'A reading was recorded.',available:true}]};
  await db.prepare('INSERT INTO story_scenarios (id,track_id,title,model_id,scenario_json,created_at) VALUES (?,?,?,?,?,?)').bind('scenario','track','Test',model.id,JSON.stringify(scenario),now).run();
  await db.prepare('INSERT INTO story_rounds (id,scenario_id,base_version,status,questions_json,output_json,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)')
    .bind('round','scenario',1,'generating','[]','{}','',now,now).run();
  for(const id of ['a','b'])await db.prepare('INSERT INTO story_jobs (id,round_id,question_id,question_json,created_at,updated_at) VALUES (?,?,?,?,?,?)')
    .bind(id,'round',id,JSON.stringify({id,text:'Question '+id}),now,now).run();
  const calls=[];
  const answer=async(_m,_s,questions)=>{const id=questions[0].id;calls.push(id);if(id==='b')throw Error('Injected story failure');
    return {output:{answers:[{questionId:id,status:'unknown',answer:'Not established.',citations:[],limitation:'Test fixture'}]},attempts:[]};};
  await storyWorkerStep(db,async()=>model,answer);await storyWorkerStep(db,async()=>model,answer);
  let round=await db.prepare('SELECT * FROM story_rounds WHERE id=?').bind('round').first();
  assert.equal(round.status,'partial');assert.equal(JSON.parse(round.output_json).output.answers.length,1);
  await db.prepare("UPDATE story_rounds SET status='generating' WHERE id='round'").run();
  await db.prepare("UPDATE story_jobs SET status='queued' WHERE id='b'").run();
  await storyWorkerStep(db,async()=>model,async(_m,_s,questions)=>{calls.push(questions[0].id);return {output:{answers:[{questionId:'b',status:'unknown',answer:'Unknown',citations:[],limitation:'Test'}]},attempts:[]};});
  round=await db.prepare('SELECT * FROM story_rounds WHERE id=?').bind('round').first();
  assert.equal(round.status,'ready');assert.deepEqual(calls,['a','b','b']);
  assert.equal(JSON.parse(round.output_json).output.answers.length,2);db.close();
});

test('visual source requires original media and cannot be interpreted from its placeholder',async()=>{
  const image={...document('photo',''),contentType:'image/png',fileName:'photo.png'};
  const state=await initializeState({...input,documents:[image]},1,null);
  const span=state.sources.find(s=>s.id==='photo').spans[0];
  assert.equal(span.modality,'image');
  const task={id:'visual',kind:'read',owner:'evidence-reading',targetIds:[span.id],requiredSpanIds:[span.id],query:'photo'};
  let called=false;
  await assert.rejects(executeTask(state,task,model,'test',{cached:async()=>null},async()=>{called=true;}),/could not be loaded/);
  assert.equal(called,false);
});

test('answer-source attribution retains the question context for short replies',async()=>{
  const state=await initializeState({...input,answerQuestions:{q:'Was the carriage restrained?'},answers:[{questionId:'q',text:'No.',answeredAt:'now'}]},1,null);
  const source=state.sources.find(s=>s.questionId==='q');
  assert.equal(source.spans[0].text,'No.');
  assert.ok(source.label.includes('Was the carriage restrained?'));
});

test('large payloads are lossless artifacts; checkpoints stay below the D1 row limit',async()=>{
  const db=database(),value={unicode:'A'+'🧪'.repeat(600000),nested:{meaning:'Do not summarize the original'}};
  const encoded=await putJSON(db,value);
  assert.ok(encoded.length<200);
  assert.deepEqual(await readJSON(db,encoded),value);
  const store=new D1EngineStore(db);
  await enqueueRevision(db,'large',incident,model,[document('large-doc','Original evidence '.repeat(150000))]);
  const run=await store.claim(Date.now(),90000);
  run.state=await initializeState(run.input,1,null);
  assert.equal(await store.save(run,run.generation,{large:value}),true);
  const row=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(run.id).first();
  assert.ok(Buffer.byteLength(row.input_json+row.state_json+row.snapshot_json)<100000);
  assert.deepEqual(await readState(db,row.state_json),JSON.parse(JSON.stringify(run.state)));
  db.close();
});

test('call-local grammar rejects decorated citations and finding IDs as source IDs',()=>{
  const schema=taskSchema('read',['S1'],[],[]);
  assert.equal(schema.safeParse({findings:[row('Valid')],questions:[],decision}).success,true);
  for(const ref of ['F1','S1: explanation','S2'])assert.equal(schema.safeParse({findings:[row('Invalid',ref)],questions:[],decision}).success,false);
  const review=taskSchema('review',['S1'],['F1'],[],'The log records a stop.');
  assert.equal(review.safeParse({status:'supported',reason:'recorded',supporting:['S1'],opposing:[],questions:[],decision,
    targetStatement:'Something about the root cause',causalRole:'event',causalRelevance:'stop'}).success,false);
});

test('read task includes only its original target; output has no application token cap',async()=>{
  const state=await initializeState(input,1,null),span=state.sources.find(s=>s.scope==='starter').spans[0];
  const task={id:'read-target',kind:'read',owner:'evidence-reading',targetIds:[span.id],requiredSpanIds:[span.id],query:'pressure maintenance'};
  const log=[];
  await executeTask(state,task,model,'t',{cached:async()=>null},fixtureRunner(log));
  assert.equal(log[0].evidencePacket.evidence.length,1);
  assert.equal(log[0].evidencePacket.evidence[0].text,span.text);
  assert.equal(log[0].outputTokens,undefined);
  assert.equal(log[0].noTruncation,true);
  assert.equal(log[0].contextWindow,model.contextWindow);
});

test('failed reading stops before any dependent interpretation; raw failure remains inspectable',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[];
  await enqueueRevision(db,'foundation',incident,model,docs);
  await drain(store,fixtureRunner(log,()=>true));
  assert.equal(log.length,1);
  const row=await db.prepare('SELECT * FROM engine_runs WHERE track_id=?').bind('foundation').first();
  assert.equal(row.status,'paused');assert.match(row.pause_reason,/Prerequisite read failed/);
  const calls=await db.prepare('SELECT * FROM engine_calls WHERE run_id=?').bind(row.id).all();
  assert.equal(calls.results.length,1);assert.equal(calls.results[0].status,'failed');
  db.close();
});

test('an invalid optional question is isolated without discarding the primary evidence read',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[];
  await enqueueRevision(db,'optional-question',incident,model,docs,[],{reviewAfterReading:true});
  const fixture=fixtureRunner(log);
  await drain(store,async request=>{
    const result=await fixture(request);
    if(request.schemaName==='try5_read')result.output.questions=[{text:'What would resolve this gap?',intent:'Test',decision:'',subject:'carriage',location:'',time:'',references:['S1']}];
    return result;
  });
  const v=(await engineVersions(db,'optional-question'))[0];
  assert.equal(v.executionStatus,'paused');
  assert.match(v.analysis.engineProgress.pauseReason,/Evidence-reading checkpoint/);
  assert.ok(v.analysis.engineProgress.tasks.every(t=>t.status==='completed'));
  assert.equal(v.analysis.engineProgress.quarantineCount,2);
  assert.equal(v.analysis.evidenceClaims.length,2);
  assert.equal(log.length,2);
  db.close();
});

test('save failure pauses with a small independent write and no repeated inference',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[];
  await enqueueRevision(db,'save-fault',incident,model,docs);
  const realSave=store.save.bind(store);let saves=0;
  store.save=async(...args)=>{if(++saves===2)throw Error('Injected checkpoint storage failure');return realSave(...args);};
  const result=await workerStep(store,async()=>model,fixtureRunner(log));
  assert.equal(result.status,'paused');assert.equal(log.length,1);
  assert.equal((await workerStep(store,async()=>model,fixtureRunner(log))).idle,true);
  db.close();
});

test('evidence checkpoint requires explicit approval and pause rejects in-flight commits',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[];
  const previous=process.env.RCA_REVIEW_AFTER_READING;process.env.RCA_REVIEW_AFTER_READING='true';
  try {await enqueueRevision(db,'checkpoint',incident,model,docs);}
  finally {if(previous===undefined)delete process.env.RCA_REVIEW_AFTER_READING;else process.env.RCA_REVIEW_AFTER_READING=previous;}
  await drain(store,fixtureRunner(log));
  assert.ok(log.every(r=>r.schemaName==='try5_read'));
  let version=(await engineVersions(db,'checkpoint'))[0];assert.equal(version.executionStatus,'paused');
  await retryFailedTasks(db,'checkpoint');
  await drain(store,fixtureRunner(log));
  version=(await engineVersions(db,'checkpoint'))[0];assert.equal(version.executionStatus,'completed');
  await enqueueRevision(db,'manual',incident,model,docs);
  const run=await store.claim(Date.now(),90000);
  assert.equal(await store.pause(run.id,'Test manual pause'),true);
  assert.equal(await store.renew(run.id,run.lease,Date.now()+90000),false);
  assert.equal(await store.save(run,run.generation,{}),false);
  db.close();
});

test('streaming provider preserves output beyond 3200 tokens and partial output on broken stream',async()=>{
  const originalFetch=globalThis.fetch,raw=JSON.stringify({findings:[],questions:[],decision:{summary:'streamed fixture'}});
  const captured=[];let sent;
  globalThis.fetch=async(_url,options)=>{
    sent=JSON.parse(options.body);
    return new Response(new ReadableStream({start(c){
      c.enqueue(new TextEncoder().encode(JSON.stringify({message:{thinking:'Provider-private deliberation, not answer JSON.'},done:false})+'\n'));
      c.enqueue(new TextEncoder().encode(JSON.stringify({message:{content:raw.slice(0,20)},done:false})+'\n'));
      c.enqueue(new TextEncoder().encode(JSON.stringify({message:{content:raw.slice(20)},done:true,done_reason:'stop',eval_count:5000})+'\n'));c.close();
    }}));
  };
  try {
    const request={stage:'evidence-reading',model,systemPrompt:'Test',schema:readSchema,schemaName:'test',evidencePacket:{},maxAttempts:1,
      noTruncation:true,thinking:true,sampling:{temperature:1,top_p:.95,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42},outputTokens:20000,onChunk:async text=>captured.push(text)};
    const result=await ollamaProvider.run(request);
    assert.ok(sent.messages[1].content.includes('RESPONSE CONTRACT'));
    assert.ok(sent.messages[1].content.includes('"findings"'));
    assert.equal(sent.think,true);
    assert.equal(result.usage.thinkingCharacters,'Provider-private deliberation, not answer JSON.'.length);
    assert.ok(!result.attempts[0].raw.includes('Provider-private'));
    assert.equal(sent.options.temperature,1);assert.equal(sent.options.seed,42);assert.equal(sent.options.top_p,.95);
    assert.equal(result.usage.outputTokens,5000);assert.equal(sent.stream,true);assert.equal(sent.options.num_predict,-1);assert.equal(captured.join(''),raw);
    captured.length=0;
    globalThis.fetch=async()=>new Response(JSON.stringify({message:{content:'{"findings":['},done:false})+'\n');
    await assert.rejects(ollamaProvider.run(request),/without a completion marker/);
    assert.equal(captured.join(''),'{"findings":[');
  }finally{globalThis.fetch=originalFetch;}
});

test('stream repetition detects whole-record cycles across chunks, ignoring object key order',()=>{
  const a=row('Repeated record with escaped "quotes", braces { [] } and a newline\n.'),b=row('Other record');
  const reordered=Object.fromEntries(Object.entries(a).reverse());
  const raw=JSON.stringify({findings:[a,b,reordered,b,a],questions:[],decision});
  const guard=new StreamRepetitionGuard();
  for(let i=0;i<raw.length;i+=7)guard.push(raw.slice(i,i+7));
  assert.deepEqual(guard.stats,{records:5,duplicateRecords:3,maxConsecutiveDuplicates:3});
});

test('stream novelty preserves repeated words, distinct metadata and independent collections without a count cap',()=>{
  const rows=Array.from({length:200},(_,i)=>({...row('Same measurement description'),time:`09:${i}`,qualifiers:'Same phrase '.repeat(20),
    details:[{reference:'shared'},{reference:'shared'},{reference:'shared'},{reference:'shared'}]}));
  const raw=JSON.stringify({findings:rows,questions:rows});
  const guard=new StreamRepetitionGuard();
  for(let i=0;i<raw.length;i+=13)guard.push(raw.slice(i,i+13));
  const a=row('Same statement'),variants=[a,{...a,time:'later'},{...a,location:'other'},{...a,references:['S2']},
    {...a,qualifiers:'Different qualification'},{...a,subject:'Other asset'}, {...a,kind:'hypothesis'}];
  new StreamRepetitionGuard().push(JSON.stringify({findings:variants}));
  // Novel records reset the streak; a few legitimate duplicates aren't a loop.
  new StreamRepetitionGuard().push(JSON.stringify({findings:[a,a,row('New'),a,a,row('Newer'),a,a]}));
});

test('repetitive provider output continues to completion with telemetry and no record-count stop',async()=>{
  const originalFetch=globalThis.fetch,captured=[],controller=new AbortController();
  let requests=0,cancelled=false,signal;
  const record=JSON.stringify(row('A repeatedly emitted finding'));
  const parts=['{"findings":[',...Array.from({length:50},(_,i)=>(i?',':'')+record),'],"questions":[],"decision":{"summary":"end"}}'];
  globalThis.fetch=async(_url,options)=>{
    requests++;signal=options.signal;let i=0;
    return new Response(new ReadableStream({
      pull(c){if(i===parts.length){c.enqueue(new TextEncoder().encode('{"done":true}\n'));c.close();return;}
        c.enqueue(new TextEncoder().encode(JSON.stringify({message:{content:parts[i++]},done:false})+'\n'));},
      cancel(){cancelled=true;},
    }));
  };
  try {
    const result=await ollamaProvider.run({stage:'equipment-tool',model,systemPrompt:'Test',schema:readSchema,schemaName:'test',evidencePacket:{},
      noTruncation:true,outputTokens:25000,maxAttempts:2,signal:controller.signal,onChunk:async text=>captured.push(text)});
    assert.equal(result.attempts.length,1);
    assert.equal(result.attempts[0].raw,captured.join(''));
    assert.equal(result.output.findings.length,50);
    assert.equal(result.attempts[0].repetition.duplicateRecords,49);
    assert.equal(requests,1);assert.equal(cancelled,false);assert.equal(signal.aborted,false);
  }finally{globalThis.fetch=originalFetch;}
});

test('explicit single-task recovery after service outage preserves earlier work',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[];
  await enqueueRevision(db,'repetition',incident,model,docs);
  const fixture=fixtureRunner(log);
  await drain(store,async request=>{
    if(request.schemaName==='try5_specialist')throw Object.assign(new Error('ECONNREFUSED injected service outage'),{attempts:[{attempt:1,raw:'retained partial raw',error:'ECONNREFUSED'}]});
    return fixture(request);
  });
  const before=await db.prepare('SELECT * FROM engine_runs WHERE track_id=?').bind('repetition').first();
  const stateBefore=await readState(db,before.state_json);
  assert.equal(before.status,'paused');assert.match(before.pause_reason,/ECONNREFUSED/);
  assert.ok(stateBefore.propositions.length>0);
  const target=stateBefore.tasks.find(t=>t.kind==='specialist'),completed=stateBefore.tasks.filter(t=>t.status==='completed');
  const callsBefore=(await db.prepare('SELECT * FROM engine_calls WHERE run_id=? ORDER BY created_at, rowid').bind(before.id).all()).results;
  assert.ok(callsBefore.find(c=>c.task_id===target.id).result_json.includes('retained partial raw'));
  await assert.rejects(retryFailedTasks(db,'repetition',{taskId:completed[0].id,pauseAfterTask:true}),/already completed/);
  await retryFailedTasks(db,'repetition',{taskId:target.id,pauseAfterTask:true});
  const retryLog=[];
  await drain(store,fixtureRunner(retryLog));
  assert.equal(retryLog.length,1);assert.equal(retryLog[0].schemaName,'try5_specialist');
  assert.ok(retryLog[0].evidencePacket.targetReferences.length);
  assert.match(retryLog[0].systemPrompt,/existing notebook, not a list to reproduce/);
  const after=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(before.id).first();
  const stateAfter=await readState(db,after.state_json);
  assert.equal(after.status,'paused');assert.match(after.pause_reason,/Task recovery checkpoint/);
  assert.equal(after.number,1);assert.equal(after.input_json,before.input_json);
  assert.deepEqual(stateAfter.tasks.filter(t=>completed.some(c=>c.id===t.id)),completed);
  assert.equal(stateAfter.tasks.find(t=>t.id===target.id).attempts,2);
  const callsAfter=(await db.prepare('SELECT * FROM engine_calls WHERE run_id=? ORDER BY created_at, rowid').bind(before.id).all()).results;
  assert.equal(callsAfter.length,callsBefore.length+1);
  assert.deepEqual(callsAfter.slice(0,-1),callsBefore);
  assert.equal((await readJSON(db,callsAfter.at(-1).request_json)).streamPolicy,STREAM_REPETITION_POLICY);
  // Explicit continuation leaves the recovery checkpoint; no full rerun occurs.
  await retryFailedTasks(db,'repetition');await drain(store,fixtureRunner([]));
  assert.equal((await engineVersions(db,'repetition'))[0].executionStatus,'completed');
  db.close();
});

test('continuous execution isolates unusable specialist responses and preserves an honest partial board',async()=>{
  for(const error of [new StreamRepetitionError(10,3,100),new Error('Ollama stream ended without a completion marker'),
    new Error('Output reached its token limit before completion'),new Error('Required joint evidence exceeds this task allowance')]) {
    const db=database(),store=new D1EngineStore(db),log=[];
    await enqueueRevision(db,'continuous',incident,model,docs);
    const fixture=fixtureRunner(log);
    await drain(store,async request=>{if(request.schemaName==='try5_specialist')throw error;return fixture(request);});
    const v=(await engineVersions(db,'continuous'))[0];
    assert.equal(v.executionStatus,'partial');
    assert.ok(v.analysis.engineProgress.tasks.some(t=>t.kind==='specialist'&&t.status==='failed'));
    assert.ok(v.analysis.engineProgress.tasks.some(t=>t.kind==='verify'&&t.status==='completed'));
    assert.ok(v.analysis.causalBoard.nodes.length>1);
    assert.ok(!v.analysis.engineProgress.pauseReason);
    db.close();
  }
});

test('progressive board schedules reviewed source findings before waiting for all specialists',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[];
  await enqueueRevision(db,'progressive',incident,model,docs);
  await drain(store,fixtureRunner(log));
  const kinds=log.map(r=>r.schemaName);
  assert.ok(kinds.indexOf('try5_review')<kinds.indexOf('try5_causal'));
  assert.ok(kinds.indexOf('try5_causal')<kinds.indexOf('try5_specialist'));
  assert.ok(kinds.indexOf('try5_verify')<kinds.indexOf('try5_specialist'));
  assert.equal((await engineVersions(db,'progressive'))[0].executionStatus,'completed');
  db.close();
});

test('continuous migration preserves immutable input and completed evidence in the same V1',async()=>{
  const db=database(),store=new D1EngineStore(db);
  await enqueueRevision(db,'migration',incident,model,docs);
  await workerStep(store,async()=>model,fixtureRunner([]));
  let row=await db.prepare('SELECT * FROM engine_runs WHERE track_id=?').bind('migration').first();
  await store.pause(row.id,'Operator migration checkpoint');
  const oldInput=await readJSON(db,row.input_json);oldInput.engineVersion='try5.2.2';
  const oldState=await readState(db,row.state_json);
  for(const t of oldState.tasks)if(t.engineVersion)t.engineVersion='try5.2.2';
  await db.prepare('UPDATE engine_runs SET input_json=?,state_json=? WHERE id=?')
    .bind(await putJSON(db,oldInput),await putState(db,oldState),row.id).run();
  row=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first();
  const hash=await digest([row.input_json,row.state_json,row.snapshot_json]);
  await assert.rejects(migrateContinuousExecution(db,row.id,row.generation,'bad','Operator approved'),/hash/);
  const result=await migrateContinuousExecution(db,row.id,row.generation,hash,'Operator approved continued execution');
  assert.equal(result.version,1);assert.equal(result.completedRetained,1);
  const after=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first(),state=await readState(db,after.state_json);
  assert.equal(after.input_json,row.input_json);assert.equal(after.number,1);assert.equal(after.status,'queued');
  assert.deepEqual(state.findings,oldState.findings);assert.deepEqual(state.tasks,oldState.tasks);
  assert.equal(checkpointVersion(oldInput,state),'try5.2.3');assert.equal(state.reviewAfterReading,false);
  assert.equal(state.progressiveBoard,true);
  await drain(store,fixtureRunner([]));
  assert.equal((await engineVersions(db,'migration'))[0].executionStatus,'completed');
  await assert.rejects(migrateContinuousExecution(db,row.id,after.generation,hash,'Again'),/paused/);
  db.close();
});

test('long complete findings are not rejected by an arbitrary text-length ceiling',()=>{
  assert.ok(readSchema.safeParse({findings:[row('Long source-grounded statement '.repeat(150))],questions:[],decision}).success);
});

async function reviewFixture(statement='The pump stopped at 09:10, but the trip caused it.') {
  const state=await initializeState(input,1,null),span=state.sources[0].spans[0];
  span.text='The pump stopped at 09:10. The cause has not been established.';
  const refs={sources:new Map([['S1',span.id]]),findings:new Map(),questions:new Map()};
  ingestRows(state,{id:'r',kind:'read',owner:'evidence-reading'},{findings:[row(statement)],questions:[]},refs);
  const finding=state.findings[0];
  const output=(extra={})=>({targetStatement:statement,claimType:'actual-event',evidence:[{source:'S1',lines:[1]}],
    establishes:'A stop is recorded.',relation:'entailed',missingPremises:[],evidenceConflicts:[],
    reason:'The source records the stop.',questions:[],decision,...extra});
  return {state,refs,finding,output};
}

test('stable literal response shape does not require generated wording maps',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The register lists room 12 and the name field is blank.');
  state.sources[0].spans[0].text='Room: 12\nName: [blank]';
  const evidence=[{source:'S1',lines:[1,2]}];
  assert.equal(assessClaim(state,finding,output({evidence}),refs).assessment.status,'supported');
  assert.throws(()=>assessClaim(state,finding,output({evidence:[{...evidence[0],claimText:'Generated map'}]}),refs));
});

test('review formatting normalizes explicit empty markers without mutating raw responses',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The log records that the pump stopped.');
  state.reviewFormattingPolicy=REVIEW_FORMATTING_POLICY;
  for(const marker of ['None',' NONE. ','No missing premises','No missing premises identified','No unresolved necessary premises','No missing premises for this claim','None for establishing the record observation itself']) {
    const raw=output({claimType:'record-observation',missingPremises:[marker]});
    const before=JSON.stringify(raw),result=assessClaim(state,finding,raw,refs);
    assert.equal(result.assessment.status,'supported');assert.equal(result.causalRole,'context');
    assert.deepEqual(result.out.missingPremises,[]);assert.equal(JSON.stringify(raw),before);
    assert.deepEqual(result.assessment.formattingNormalization,{policy:REVIEW_FORMATTING_POLICY,field:'missingPremises',removed:[marker]});
  }
  const raw=output({claimType:'record-observation',missingPremises:['None']});
  const task={id:'format-review',kind:'review',owner:'claim-review',targetIds:[finding.id]};
  applyEvidenceTask(state,task,raw,refs);
  assert.equal(finding.reviewExecution,'complete');assert.equal(state.questions.length,0);
  assert.deepEqual(raw.missingPremises,['None']);
});

test('review formatting preserves real caveats, partial requirements, and provenance checks',async()=>{
  const {state,refs,finding,output}=await reviewFixture();state.reviewFormattingPolicy=REVIEW_FORMATTING_POLICY;
  for(const gap of ['None of the witnesses observed the stop.','None, except the timing is unknown.','Unknown','N/A','',
    'None for establishing the record observation itself','Whether shift start preceded the record is unknown.'])
    assert.throws(()=>assessClaim(state,finding,output({missingPremises:[gap]}),refs));
  const raw=output({missingPremises:['None','The trip timing is unknown.']});
  assert.deepEqual(normalizeReviewFormatting(raw,REVIEW_FORMATTING_POLICY).output.missingPremises,['The trip timing is unknown.']);
  const task={id:'real-gap',kind:'review',owner:'claim-review',targetIds:[finding.id]};
  assert.throws(()=>applyEvidenceTask(state,task,raw,refs),/unresolved necessary premise/);
  assert.equal(state.questions.length,1);assert.ok(state.questions[0].text.includes('trip timing'));assert.ok(!state.questions[0].text.includes('None'));
  assert.throws(()=>assessClaim(state,finding,output({relation:'partially-established',missingPremises:['None']}),refs),/concrete missing premise/);
  for(const extra of [{targetStatement:'Another target'},{evidence:[{source:'forged',lines:[1]}]},{evidence:[{source:'S1',lines:[999]}]},{evidence:[]}])
    assert.throws(()=>assessClaim(state,finding,output({...extra,missingPremises:['None']}),refs));
  // Do not coerce malformed structures or accept an absent missingPremises field.
  for(const missingPremises of ['None',null,undefined])assert.throws(()=>assessClaim(state,finding,output({missingPremises}),refs));
});

test('review formatting is explicit per revision and isolated from legacy call caches',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pump stopped at 09:10.');
  assert.equal(state.reviewFormattingPolicy,undefined);
  const raw=output({missingPremises:['None']});
  assert.throws(()=>assessClaim(state,finding,raw,refs),/unresolved necessary premise/);
  const task={id:'format-cache',kind:'review',owner:'claim-review',targetIds:[finding.id],query:finding.statement,requiredSpanIds:finding.spanIds};
  const requests=[],first=await executeTask(state,task,model,'format-cache',{cached:async()=>null},fixtureRunner(requests));
  state.reviewFormattingPolicy=REVIEW_FORMATTING_POLICY;
  const second=await executeTask(state,task,model,'format-cache',{cached:async(_track,key)=>key===first.cacheKey?{output:first.output}:null},fixtureRunner(requests));
  assert.notEqual(first.cacheKey,second.cacheKey);assert.equal(second.reused,false);
  const db=database();await enqueueRevision(db,'format-new',incident,model,docs);
  const saved=await db.prepare('SELECT input_json FROM engine_runs WHERE track_id=?').bind('format-new').first();
  const frozen=await readJSON(db,saved.input_json);
  assert.equal(frozen.reviewFormattingPolicy,REVIEW_FORMATTING_POLICY);
  assert.equal((await initializeState(frozen,1,null)).reviewFormattingPolicy,REVIEW_FORMATTING_POLICY);
  db.close();
});

async function formattingMigrationFixture(missingPremises=['None']) {
  const db=database(),{state,refs,finding,output}=await reviewFixture('The log records that the pump stopped.');
  const raw=output({claimType:'record-observation',missingPremises});
  const task={id:'saved-review',kind:'review',owner:'claim-review',targetIds:[finding.id],targetRevision:finding.revision,
    dependsOn:[],status:'failed',attempts:1,traceId:'saved-call',producedIds:[],evidenceIds:finding.spanIds,omittedEvidenceIds:[],
    contextBytes:0,durationMs:12,inputTokens:10,outputTokens:10,createdAt:'2026-09-20T00:00:00Z',completedAt:'2026-09-20T00:00:01Z'};
  try{applyEvidenceTask(state,task,raw,refs);}catch(error){task.error=error.message;}
  state.tasks.push(task);state.quarantine.push({taskId:task.id,item:{traceId:task.traceId},reason:task.error});
  state.phase=5;
  await enqueueRevision(db,'formatting-migration',incident,model,docs);
  let row=await db.prepare('SELECT * FROM engine_runs WHERE track_id=?').bind('formatting-migration').first();
  await db.prepare("UPDATE engine_runs SET input_json=?,state_json=?,status='paused',lease_until=0 WHERE id=?")
    .bind(await putJSON(db,input),await putState(db,state),row.id).run();
  row=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first();
  const span=state.sources[0].spans[0];
  const request={kind:'review',packet:{target:{statement:finding.statement},evidence:[{ref:'S1',text:span.text.split('\n').map((line,n)=>`${n+1}|${line}`).join('\n')}]},selectedEvidence:[span.id]};
  await db.prepare("INSERT INTO engine_calls (id,run_id,task_id,attempt,status,request_json,result_json,created_at,updated_at) VALUES (?,?,?,1,'failed',?,?,'now','now')")
    .bind(task.traceId,row.id,task.id,await putJSON(db,request),await putJSON(db,{output:{output:raw}})).run();
  const hash=await digest([row.input_json,row.state_json,row.snapshot_json]);
  return {db,row,state,task,finding,hash};
}

test('review formatting migration revalidates saved output and archives only the placeholder',async()=>{
  const {db,row,state,task,hash}=await formattingMigrationFixture();
  const originalCall=await db.prepare('SELECT * FROM engine_calls WHERE id=?').bind(task.traceId).first();
  const result=await activateReviewFormatting(db,row.id,row.generation,hash,'User approved current V1',[task.id]);
  const after=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first(),updated=await readState(db,after.state_json);
  assert.equal(after.status,'queued');assert.equal(after.input_json,row.input_json);assert.equal(after.number,row.number);
  assert.equal(updated.reviewFormattingPolicy,REVIEW_FORMATTING_POLICY);assert.equal(updated.tasks[0].status,'completed');
  assert.equal(updated.tasks[0].attempts,1);assert.equal(updated.tasks[0].completedAt,task.completedAt);
  assert.equal(updated.tasks[0].formattingRecovery.traceId,task.traceId);
  assert.equal(updated.findings[0].reviewExecution,'complete');assert.equal(updated.questions.length,0);assert.equal(updated.quarantine.length,0);
  assert.deepEqual(result.retiredQuestionIds,state.questions.map(q=>q.id));
  assert.deepEqual(await readJSON(db,result.backup),{...row});
  assert.deepEqual(await db.prepare('SELECT * FROM engine_calls WHERE id=?').bind(task.traceId).first(),originalCall);
  assert.equal((await db.prepare('SELECT COUNT(*) AS n FROM engine_calls').first()).n,1);
  // Planner must not resample completed work after enabling the policy.
  updated.progressiveBoard=false;updated.phase=6;
  await planNext(updated);assert.equal(updated.tasks.filter(t=>t.kind==='review').length,1);
  db.close();
});

test('review formatting migration refuses real gaps, changed evidence, active work and stale checkpoints',async()=>{
  for(const mode of ['real-gap','evidence','running','hash','published']) {
    const {db,row,state,task,hash}=await formattingMigrationFixture(mode==='real-gap'?['None','Timing is unproved.']:['None']);
    let expectedHash=hash;
    if(mode==='evidence'||mode==='running') {
      if(mode==='evidence')state.sources[0].spans[0].text='Changed evidence';else state.tasks[0].status='running';
      row.state_json=await putState(db,state);
      await db.prepare('UPDATE engine_runs SET state_json=? WHERE id=?').bind(row.state_json,row.id).run();
      expectedHash=await digest([row.input_json,row.state_json,row.snapshot_json]);
    }
    if(mode==='published')await db.prepare('INSERT INTO versions (id,track_id,number,trigger,analysis_json,created_at) VALUES (?,?,?,?,?,?)')
      .bind(row.id,row.track_id,row.number,'Published',row.snapshot_json,'now').run();
    const before=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first();
    await assert.rejects(activateReviewFormatting(db,row.id,row.generation,mode==='hash'?'wrong':expectedHash,'User approved',[task.id]));
    assert.deepEqual(await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(row.id).first(),before);
    db.close();
  }
});

test('inconsistent review preserves a deduplicated gap question, never a repaired verdict or new fact',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The room was empty.');
  const task={id:'gap-review',kind:'review',owner:'claim-review',targetIds:[finding.id]};
  const bad=output({missingPremises:['A complete observation of the room at the stated time.']});
  assert.equal(taskSchema('review',['S1'],[],[],finding.statement,{S1:[1]}).safeParse(bad).success,true);
  for(let i=0;i<2;i++)assert.throws(()=>applyEvidenceTask(state,task,bad,refs),/unresolved necessary premise/);
  assert.equal(state.findings.length,1);assert.equal(finding.status,'proposed');assert.equal(finding.reviewExecution,'incomplete');
  assert.equal(state.questions.length,1);assert.deepEqual(state.questions[0].reviewTargets,[finding.id]);
  assert.equal(state.questions[0].status,'open');assert.equal(state.questions[0].answer,'');
  assert.match(state.questions[0].reason,/inconsistent review/);assert.deepEqual(task.producedIds,[state.questions[0].id]);
  assert.ok(state.questions[0].owners.includes('evidence-reading'));
  const recovered=state.questions[0];
  state.questions.unshift({...structuredClone(recovered),id:'canonical-question',owners:['stored-energy'],reviewTargets:['other-claim']});
  applyQuestionTask(state,{id:'merge',kind:'broker',owner:'question-broker',targetIds:[recovered.id]},
    {equivalentTo:'Q1',reason:'Same missing evidence in this fixture.',decision},
    {...refs,questions:new Map([['Q1','canonical-question']])});
  assert.deepEqual(state.questions[0].reviewTargets,['other-claim',finding.id]);
  assert.ok(state.questions[0].owners.includes('evidence-reading'));
  for(const invalid of [{...bad,targetStatement:'Another target'},{...bad,evidence:[{source:'forged',lines:[1]}]},{...bad,unexpected:1}]) {
    state.questions=[];
    assert.throws(()=>applyEvidenceTask(state,task,invalid,refs));assert.equal(state.questions.length,0);
  }
});

test('durable failed review keeps its gap routable while independent causal work completes',async()=>{
  const db=database(),store=new D1EngineStore(db),log=[],base=fixtureRunner(log);
  await enqueueRevision(db,'review-gap-route',incident,model,docs);
  await drain(store,async request=>{
    const result=await base(request);
    if(request.schemaName==='try5_review'&&request.evidencePacket.target.statement.includes('6.8'))
      result.output.missingPremises=['Confirm the measurement scope with the original instrument record.'];
    // This test is about routing, not the fixture broker's deliberately broad
    // default merge. The instrument gap and restraint question are distinct.
    if(request.schemaName==='try5_broker'&&request.evidencePacket.question.text.includes('original instrument record'))
      result.output.equivalentTo=null;
    request.schema.parse(result.output);return result;
  });
  const v=(await engineVersions(db,'review-gap-route'))[0];
  assert.equal(v.executionStatus,'partial');
  const failed=v.analysis.engineProgress.tasks.find(t=>t.kind==='review'&&t.status==='failed');
  assert.ok(failed);assert.match(failed.error,/unresolved necessary premise/);
  assert.ok(log.some(r=>r.schemaName==='try5_answer'&&r.evidencePacket.question.text.includes('original instrument record')));
  assert.ok(v.analysis.engineProgress.tasks.some(t=>t.kind==='causal'&&t.status==='completed'));
  assert.ok(!v.analysis.facts.some(f=>f.includes('6.8')));
  db.close();
});

test('complete literal claim is preserved; partial support requires a concrete missing premise',async()=>{
  const {state,refs,finding,output}=await reviewFixture();
  const raw=output({relation:'partially-established',missingPremises:['Trip activation and mechanism unproved.']});
  assert.throws(()=>assessClaim(state,finding,{...raw,status:'supported'},refs));
  const result=assessClaim(state,finding,raw,refs);
  assert.equal(result.assessment.status,'partial');assert.equal(result.assessment.parts.length,1);
  assert.equal(result.assessment.parts[0].claimText,finding.statement);
  assert.equal(result.causalRole,'hypothesis');
  assert.throws(()=>assessClaim(state,finding,output({missingPremises:['A necessary premise is missing.']}),refs));
  assert.throws(()=>assessClaim(state,finding,output({relation:'partially-established'}),refs));
});

test('review checks original lines and exact target; optional causal questions do not erase established facts',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pump stopped at 09:10.');
  assert.equal(assessClaim(state,finding,output(),refs).assessment.status,'supported');
  for(const evidence of [[{source:'S99',lines:[1]}],[{source:'S1',lines:[999]}],[]])
    assert.throws(()=>assessClaim(state,finding,output({evidence}),refs));
  const questions=[{text:'What caused the stop?',intent:'Cause',decision:'Determine mechanism',subject:'pump',location:'',time:'',references:['S1']}];
  assert.equal(assessClaim(state,finding,output({questions}),refs).assessment.status,'supported');
  assert.throws(()=>assessClaim(state,finding,output({targetStatement:'Another claim'}),refs),/differs/);
});

test('scope-aware negatives may be supported; record metadata stays context and contrary evidence stays distinct',async()=>{
  const {state,refs,finding,output}=await reviewFixture('No bolt was present in socket B at 10:21.');
  state.sources[0].spans[0].text=finding.statement;
  assert.equal(assessClaim(state,finding,output({claimType:'actual-state'}),refs).assessment.status,'supported');
  assert.equal(assessClaim(state,finding,output({relation:'contradicted',missingPremises:['Approval premise disproved.']}),refs).assessment.status,'contradicted');
  assert.equal(assessClaim(state,finding,output({claimType:'record-observation'}),refs).causalRole,'context');
  applyEvidenceTask(state,{id:'review',kind:'review',owner:'claim-review',targetIds:[finding.id]},output(),refs);
  assert.equal(finding.reviewAssessment.policy,CLAIM_REVIEW_POLICY);
  ingestRows(state,{id:'update',kind:'read',owner:'evidence-reading'},{findings:[{...row('A changed proposition'),replaces:'F1'}],questions:[]},
    {...refs,findings:new Map([['F1',finding.id]])});
  assert.equal(finding.status,'proposed');assert.equal(finding.reviewAssessment,undefined);assert.equal(finding.interpretation,undefined);
});

test('review citations copy nonadjacent original lines; revised sources invalidate the assessment',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pump stopped at 09:10.');
  state.sources[0].spans[0].text='| Item | Value |\n| Other | 4 |\n| Pump | stopped |\n\n';
  const raw=output({evidence:[{source:'S1',lines:[1,3]}]});
  const assessed=assessClaim(state,finding,raw,refs);
  assert.deepEqual(assessed.assessment.parts[0].quotes.map(q=>({source:q.source,line:q.line,quote:q.quote})),[{source:finding.spanIds[0],line:1,quote:'| Item | Value |'},{source:finding.spanIds[0],line:3,quote:'| Pump | stopped |'}]);
  assert.equal(assessed.assessment.parts[0].quotes[0].localRef,'S1');
  assert.equal(assessed.assessment.parts[0].quotes[0].revision,state.sources[0].spans[0].revision);
  assert.throws(()=>assessClaim(state,finding,output({evidence:[{source:'S1',lines:[4]}]}),refs),/no original text/);
  applyEvidenceTask(state,{id:'review',kind:'review',owner:'claim-review',targetIds:[finding.id]},raw,refs);
  const view=project(state,input,'paused');
  assert.equal(view.evidenceClaims[0].review.claimParts.policy,CLAIM_REVIEW_POLICY);
  assert.deepEqual(view.evidenceClaims[0].review.claimParts.parts[0].originalQuotes,assessed.assessment.parts[0].quotes);
  const updated=await initializeState({...input,incident:'Revised incident account'},2,state);
  assert.equal(updated.findings[0].status,'proposed');assert.equal(updated.findings[0].reviewExecution,'unreviewed');
  assert.equal(updated.findings[0].reviewAssessment,undefined);assert.ok(state.findings[0].reviewAssessment);
});

test('review request excludes producer labels and stale interpretation; real evidence changes invalidate cache',async()=>{
  const {state,finding}=await reviewFixture('The pump stopped at 09:10.');
  finding.qualifiers='PRIOR MODEL ASSERTION';finding.causalRole='barrier';finding.status='supported';
  finding.interpretation={policy:'obsolete',parts:[{ambiguities:['INVENTED WORD AMBIGUITY']} ]};
  const task={id:'review-neutral',kind:'review',owner:'claim-review',targetIds:[finding.id],query:finding.statement,requiredSpanIds:finding.spanIds};
  const requests=[],first=await executeTask(state,task,model,'neutral-review',{cached:async()=>null},fixtureRunner(requests));
  const request=requests[0];
  assert.deepEqual(request.evidencePacket.target,{statement:finding.statement});
  assert.equal(request.evidencePacket.findings,undefined);assert.equal(request.evidencePacket.fixedMeaning,undefined);
  assert.ok(!JSON.stringify(request.evidencePacket).includes('PRIOR MODEL ASSERTION'));
  assert.ok(!JSON.stringify(request.evidencePacket).includes('INVENTED WORD AMBIGUITY'));
  assert.ok(request.evidencePacket.evidence.every(s=>s.text.startsWith('1|')));
  state.sources[0].spans[0].text='The pump stopped at 09:11.';state.sources[0].textHash='changed';
  const second=await executeTask(state,task,model,'neutral-review',{cached:async()=>null},fixtureRunner(requests));
  assert.notEqual(first.cacheKey,second.cacheKey);
});

test('review grammar permits only real source-line combinations and the exact original target',async()=>{
  const {finding,output}=await reviewFixture('The pump stopped at 09:10.');
  const schema=taskSchema('review',['S1','S2'],[],[],finding.statement,{S1:[1,3],S2:[2]});
  for(const [source,lines,valid] of [['S1',[1,3],true],['S2',[2],true],['S1',[2],false],['S2',[1],false],['S9',[1],false],['S1',[],false]])
    assert.equal(schema.safeParse(output({evidence:[{source,lines}]})).success,valid);
  assert.equal(schema.safeParse(output({targetStatement:'Altered target'})).success,false);
  assert.equal(taskSchema('review',[],[],[],finding.statement,{}).safeParse(output({evidence:[]})).success,false);
  assert.equal(taskSchema('review',[],[],[],finding.statement,{}).safeParse(output({evidence:[],relation:'not-established'})).success,true);
});

test('native thinking is explicit in provider requests and cannot reuse non-thinking review cache',async()=>{
  const {state,finding}=await reviewFixture('The pump stopped at 09:10.');
  const task={id:'mode',kind:'review',owner:'claim-review',targetIds:[finding.id],query:finding.statement,requiredSpanIds:finding.spanIds};
  const requests=[],traces=[];
  const trace={request:async r=>traces.push(r),append:async()=>{},complete:async()=>{}};
  const first=await executeTask(state,task,model,'mode',{cached:async()=>null},fixtureRunner(requests),undefined,{trace,thinking:false});
  const second=await executeTask(state,task,model,'mode',{cached:async(_track,key)=>key===first.cacheKey?{output:first.output}:null},fixtureRunner(requests),undefined,{trace,thinking:true});
  assert.notEqual(first.cacheKey,second.cacheKey);assert.equal(second.reused,false);
  assert.deepEqual(requests.map(r=>r.thinking),[false,true]);
  assert.deepEqual(traces.map(r=>r.thinking),[false,true]);
  const sampling={temperature:1,top_p:.95,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42};
  const third=await executeTask(state,task,model,'mode',{cached:async()=>null},fixtureRunner(requests),undefined,{trace,thinking:true,sampling});
  assert.notEqual(third.cacheKey,second.cacheKey);assert.deepEqual(traces[2].sampling,sampling);assert.deepEqual(requests[2].sampling,sampling);
});

test('production Qwen uses mode-specific profiles without changing other models',async()=>{
  const {state,finding}=await reviewFixture('The pump stopped at 09:10.');
  const task={id:'profile',kind:'review',owner:'claim-review',targetIds:[finding.id],query:finding.statement,requiredSpanIds:finding.spanIds};
  const qwen={...model,id:'ollama:qwen3.5:latest',capabilities:['thinking']},requests=[];
  await executeTask(state,task,qwen,'profile',{cached:async()=>null},fixtureRunner(requests));
  assert.equal(requests[0].thinking,true);assert.deepEqual(requests[0].sampling,QWEN_REVIEW_SAMPLING);
  await executeTask(state,{...task,kind:'tag',owner:'tagging'},qwen,'profile',{cached:async()=>null},fixtureRunner(requests));
  assert.equal(requests[1].thinking,false);assert.deepEqual(requests[1].sampling,{temperature:.7,top_p:.8,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42});
  await executeTask(state,task,model,'profile',{cached:async()=>null},fixtureRunner(requests));
  assert.equal(requests[2].thinking,false);
  await assert.rejects(executeTask(state,task,{...qwen,capabilities:[]},'profile',{cached:async()=>null},fixtureRunner(requests)),/confirmed thinking capability/);
  assert.equal(requests.length,3);
});

test('partial whole claims cannot be promoted by a later causal verifier',async()=>{
  const {state,refs,finding,output}=await reviewFixture();refs.findings.set('F1',finding.id);
  applyEvidenceTask(state,{id:'r',kind:'review',owner:'claim-review',targetIds:[finding.id]},
    output({relation:'partially-established',missingPremises:['No trip evidence.']}),refs);
  assert.equal(finding.status,'partial');
  applyBoardTask(state,{id:'c',kind:'causal',owner:'causal-analysis',targetIds:[finding.id]},
    {disposition:'node',type:'event',label:finding.statement,detail:finding.statement,reason:'Fixture proposal',references:['S1'],
      edges:[{from:'F1',to:'EVENT',type:'enabled',rationale:'Fixture only',counterfactual:'Fixture',alternative:'Fixture',gap:'',references:['S1']}],questions:[],decision},refs);
  for(const target of [...state.propositions,...state.relationships]) {
    applyBoardTask(state,{id:'v',kind:'verify',owner:'causal-verification',targetIds:[target.id]},
      {status:'supported',reason:'Overconfident fixture verdict',supporting:['S1'],opposing:[],questions:[],decision},refs);
    assert.equal(target.status,'unknown');
  }
  assert.ok(!project(state,input,'completed').facts.includes(finding.statement));
});

test('node truth and relationship mechanism use distinct verification prompts and packets',async()=>{
  const {state,finding}=await reviewFixture('The boundary was preparation-only.');
  finding.status='supported';
  state.propositions.push({id:'node',findingId:finding.id,type:'condition',label:finding.statement,detail:finding.statement,spanIds:finding.spanIds,status:'proposed',humanStatus:'unreviewed'});
  state.relationships.push({id:'link',from:'node',to:'focal',type:'caused',rationale:'Preparation caused the event.',counterfactual:'No preparation, no event.',alternative:'Unrelated pressure disturbance.',gap:'Mechanism unknown.',findingIds:[finding.id],spanIds:finding.spanIds,proposedBy:[finding.id],status:'proposed'});
  const requests=[];
  for(const id of ['node','link']) {
    const task={id:'verify-'+id,kind:'verify',owner:'causal-verification',targetIds:[id],query:id,requiredSpanIds:finding.spanIds};
    const result=await executeTask(state,task,model,'verify-scope',{cached:async()=>null},async request=>{
      requests.push(request);
      const output={status:request.evidencePacket.verificationTarget==='node'?'supported':'unknown',
        reason:'Deterministic scope fixture, not a semantic model result.',supporting:['S1'],opposing:[],questions:[],decision};
      request.schema.parse(output);return {output,durationMs:1};
    });
    applyBoardTask(state,task,result.output,result.refs);
  }
  assert.equal(requests[0].evidencePacket.verificationTarget,'node');
  assert.equal(requests[1].evidencePacket.verificationTarget,'relationship');
  assert.match(requests[0].systemPrompt,/NODE, not a relationship/);
  assert.match(requests[1].systemPrompt,/Two supported endpoint statements do not establish/);
  assert.notEqual(requests[0].systemPrompt,requests[1].systemPrompt);
  assert.equal(state.propositions[0].status,'supported');assert.equal(state.relationships[0].status,'unknown');
});

test('old speculative ambiguity cannot veto a cited decision; success clears obsolete interpretation',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pump stopped at 09:10.');
  finding.interpretation={policy:'claim-meaning-v1',targetStatement:finding.statement,parts:[{ambiguities:['What does stopped mean?']}]};
  applyEvidenceTask(state,{id:'r',kind:'review',owner:'claim-review',targetIds:[finding.id]},output(),refs);
  assert.equal(finding.status,'supported');assert.equal(finding.interpretation,undefined);
});

test('incomplete output stays unreviewed, not epistemically unknown, and invalidates dependent approvals',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pump stopped at 09:10.');
  const raw=output();
  state.propositions.push({id:'retained-node',findingId:finding.id,status:'supported',humanStatus:'accepted'});
  state.relationships.push({id:'retained-edge',from:'retained-node',to:'focal',findingIds:[finding.id],status:'supported'});
  for(const bad of [{...raw,parts:[]},{...raw,targetStatement:'Different statement'},{...raw,evidence:[]},
    {...raw,missingPremises:['A required fact is unavailable.']}]) {
    finding.status='supported';
    assert.throws(()=>applyEvidenceTask(state,{id:'r',kind:'review',owner:'claim-review',targetIds:[finding.id]},bad,refs));
    assert.equal(finding.status,'proposed');assert.equal(finding.reviewExecution,'incomplete');
    assert.equal(finding.reviewAssessment,undefined);
    assert.equal(state.propositions[0].status,'proposed');assert.equal(state.propositions[0].humanStatus,'reopened');
    assert.equal(state.relationships[0].status,'proposed');
  }
});

test('truth uncertainty and two-sided source conflict survive independently into the dashboard',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pressure was 2 bar at 11:00.');
  state.sources[0].spans[0].text='Gauge A at the port at 11:00: 2 bar.\nGauge B at the same port at 11:00: 4 bar.';
  const raw=output({claimType:'actual-state',relation:'contradicted',evidenceConflicts:[{
    impact:'claim-truth',scope:{subject:'pressure',location:'same port',time:'11:00'},
    sideA:{assertion:'Gauge A reports 2 bar',evidence:[{source:'S1',lines:[1]}]},
    sideB:{assertion:'Gauge B reports 4 bar',evidence:[{source:'S1',lines:[2]}]},
    reason:'Simultaneous same-port readings disagree.',resolutionNeeded:'Resolve measurement reliability.'}]});
  applyEvidenceTask(state,{id:'r',kind:'review',owner:'claim-review',targetIds:[finding.id]},raw,refs);
  assert.equal(finding.status,'unknown');assert.equal(finding.reviewExecution,'complete');
  const view=project(state,input,'completed');
  assert.equal(view.evidenceClaims[0].status,'unknown');assert.equal(view.conflicts.length,1);
  assert.equal(view.conflicts[0].sides.length,2);assert.equal(view.conflicts[0].sides[1].originalQuotes[0].line,2);
  assert.equal(view.status,'contradictions-unresolved');
  raw.evidenceConflicts=[];
  applyEvidenceTask(state,{id:'r',kind:'review',owner:'claim-review',targetIds:[finding.id]},raw,refs);
  assert.equal(project(state,input,'completed').conflicts.length,0);assert.equal(finding.status,'contradicted');
  finding.statement='Gauge A recorded 2 bar at 11:00.';
  const record=output({targetStatement:finding.statement,claimType:'record-observation',evidence:[{source:'S1',lines:[1]}]});
  record.evidenceConflicts=[{...view.conflicts[0],impact:'underlying-event-only'}];
  // Use the same two raw evidence selections, not projected UI fields.
  record.evidenceConflicts=[{impact:'underlying-event-only',scope:{subject:'pressure',location:'same port',time:'11:00'},
    sideA:{assertion:'A reports 2',evidence:[{source:'S1',lines:[1]}]},
    sideB:{assertion:'B reports 4',evidence:[{source:'S1',lines:[2]}]},reason:'Readings disagree.',resolutionNeeded:'Check gauges.'}];
  applyEvidenceTask(state,{id:'r',kind:'review',owner:'claim-review',targetIds:[finding.id]},record,refs);
  assert.equal(finding.status,'supported');assert.equal(finding.causalRole,'context');assert.equal(project(state,input,'completed').conflicts.length,1);
});

test('planner schedules review directly; failure blocks only that claim, not independent reviews',async()=>{
  const {state,finding}=await reviewFixture('The pump stopped at 09:10.');
  state.phase=6;state.tasks=[];
  const other={...structuredClone(finding),id:'independent',statement:'A different assertion'};state.findings.push(other);
  const first=await planNext(state);
  assert.equal(first.kind,'review');assert.ok(!state.tasks.some(t=>t.kind==='interpret'));
  assert.deepEqual(first.dependsOn,[]);
  first.status='failed';first.error='Bad review';
  const next=await planNext(state);
  assert.equal(next.kind,'review');assert.deepEqual(next.targetIds,[other.id]);
});

test('factual nodes preserve reviewed wording; proposed additions never enter verification',async()=>{
  const {state,refs,finding}=await reviewFixture('Preparation only; maintenance release is pending.');
  finding.status='supported';refs.findings.set('F1',finding.id);
  const raw={disposition:'node',type:'condition',label:'Condition: Incomplete system state',detail:'Isolation failed according to S1.',reason:'From S1',references:['S1'],edges:[],questions:[],decision};
  applyBoardTask(state,{id:'c',kind:'causal',targetIds:[finding.id]},raw,refs);
  const node=state.propositions[0];assert.equal(node.label,finding.statement);assert.equal(node.detail,'');
  assert.match(node.proposedWording.detail,/⟦evidence:/);assert.equal(raw.detail,'Isolation failed according to S1.');
  const requests=[];
  await executeTask(state,{id:'v',kind:'verify',targetIds:[node.id],query:node.label,requiredSpanIds:node.spanIds},model,'safe-node',{cached:async()=>null},fixtureRunner(requests));
  assert.equal(requests[0].evidencePacket.target.label,finding.statement);assert.equal(requests[0].evidencePacket.target.detail,'');
  assert.ok(!JSON.stringify(requests[0].evidencePacket).includes('Isolation failed'));
});

test('commentary citations bind to original span IDs, not the next calls numbering',async()=>{
  const refs={sources:new Map([['S1','span:original']]),findings:new Map([['F1','finding:original']]),questions:new Map()};
  const text=bindCommentary('From S1, F1 is a lead.',refs);
  const next={...refs,sources:new Map([['S1','span:different']])};
  assert.equal(bindCommentary(text,next),text);assert.ok(text.includes('span:original'));assert.ok(!text.includes('span:different'));
});

test('scope reclassification is recorded and does not suppress a reviewed observation',async()=>{
  const {state,refs,finding,output}=await reviewFixture('The pump stopped at 09:10.');
  applyEvidenceTask(state,{id:'r1',kind:'review',owner:'claim-review',targetIds:[finding.id]},output({claimType:'actual-event'}),refs);
  applyEvidenceTask(state,{id:'r2',kind:'review',owner:'claim-review',targetIds:[finding.id]},output({claimType:'record-observation'}),refs);
  assert.deepEqual(finding.scopeHistory.map(s=>s.claimType),['actual-event','record-observation']);
  assert.equal(finding.statement,'The pump stopped at 09:10.');assert.equal(finding.status,'supported');
  state.phase=7;state.tasks=[{id:'r2',kind:'review',targetIds:[finding.id],status:'completed',evidenceIds:[],omittedEvidenceIds:[],dependsOn:[]}];
  const next=await planNext(state);assert.equal(next.kind,'causal');assert.ok(next.targetIds.includes(finding.id));
  assert.equal(project(state,input,'partial').evidenceClaims[0].scopeHistory.length,2);
});

test('focused inquiry remains proposed and routes valid questions through the existing broker',async()=>{
  const {state,refs,finding}=await reviewFixture('The carriage moved during maintenance.');
  const before=JSON.stringify({findings:state.findings,nodes:state.propositions,edges:state.relationships});
  const task={id:'inquiry',kind:'inquiry',owner:'causal-analysis',targetIds:[finding.id],status:'completed'};
  const q={text:'Which restraint state was recorded?',intent:'Distinguish explanations',decision:'Test restraint hypothesis',subject:'restraint',location:'line',time:'incident',references:['S1'],evidenceNeeded:'Contemporaneous record',contrasts:[{explanationId:'H1',expectedObservation:'Restraint absent',implication:'Supports possibility, not sufficient proof'}]};
  applyBoardTask(state,task,{observations:[{statement:'Reported motion',references:['S1'],limitation:'Not direct observation'}],
    explanations:[{id:'H1',title:'Restraint issue',mechanism:'Possible unrestrained movement',supporting:['S1'],opposing:[],unresolved:'Restraint unknown'}],
    questions:[q,{...q,text:'Invalid second question',contrasts:[{...q.contrasts[0],explanationId:'invented'}]}],decision},refs);
  assert.equal(before,JSON.stringify({findings:state.findings,nodes:state.propositions,edges:state.relationships}));
  assert.equal(state.inquiries[0].status,'proposed');assert.equal(state.questions.length,1);assert.equal(state.quarantine.length,1);
  assert.equal(state.inquiries[0].questions[0].questionId,state.questions[0].id);
  state.phase=9;state.tasks=[task];state.followupPass=false;
  const next=await planNext(state);assert.equal(next.kind,'broker');assert.deepEqual(next.targetIds,[state.questions[0].id]);
});

test('broker merges inquiry ownership and evidence, and returns a reviewed answer to both requests',async()=>{
  const {state,refs,finding}=await reviewFixture('The carriage moved during maintenance.');
  const base={intent:'Test restraint',decision:'Distinguish causes',subject:'carriage',location:'line',time:'incident',references:['S1']};
  const a=ingestQuestion(state,{owner:'mechanical-equipment'},{...base,text:'What restrained the carriage?'},refs);
  const b=ingestQuestion(state,{owner:'causal-analysis'},{...base,text:'Which restraint was installed?'},refs);
  const original=state.questions.find(q=>q.id===a), proposed=state.questions.find(q=>q.id===b);
  proposed.inquiryTargets=['inquiry:test'];refs.questions.set('Q1',a);
  applyQuestionTask(state,{kind:'broker',targetIds:[b]},{equivalentTo:'Q1',reason:'Same request',decision},refs);
  assert.deepEqual(original.inquiryTargets,['inquiry:test']);assert.equal(proposed.coveredBy,a);
  original.answer='Recorded carriage movement, restraint unknown.';original.answerSpanIds=finding.spanIds;original.findingIds=[finding.id];original.answerCompleteness='partial';
  finding.status='supported';reconcileAnswers(state);
  assert.equal(proposed.answer,original.answer);assert.ok(finding.owners.includes('causal-analysis'));assert.equal(original.status,'partial');
});

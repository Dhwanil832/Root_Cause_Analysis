// Focused live diagnostic: production executor/prompt/provider on saved findings.
// The app DB is read-only; generated traces live in a new outputs directory.
// No grading instructions, hidden answers, or other diagnostic outputs enter a request.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { readJSON, readState } from '../src/engine/tasks/artifacts.ts';
import { executeTask } from '../src/engine/tasks/executor.ts';
import { applyEvidenceTask } from '../src/stages/evidence-reading/task.ts';
import { findingText } from '../src/engine/records.ts';
import { ENGINE_VERSION } from '../src/engine/types.ts';
import { digest } from '../src/engine/identity.ts';
import { initializeState } from '../src/engine/tasks/planner.ts';
import { CLAIM_REVIEW_POLICY } from '../src/engine/review/literal-contract.ts';
import { reviewInference } from '../src/engine/review/inference-profile.ts';

const [runId, producerTaskId] = process.argv.slice(2);
if (!runId || !producerTaskId) throw Error('Usage: node --import ./scripts/register-test-loader.mjs scripts/review-saved-findings.mjs RUN_ID PRODUCER_TASK_ID|--fixtures=PATH');
const fixturePath=producerTaskId.startsWith('--fixtures=') ? path.resolve(producerTaskId.slice('--fixtures='.length)) : null;
const resumeArg=process.argv.slice(4).find(a=>a.startsWith('--resume-diagnostic='));
const thinking=process.argv.slice(4).includes('--thinking=true');
const sampling=process.argv.slice(4).includes('--sampling=qwen-reasoning')?{temperature:1,top_p:0.95,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42}:undefined;
const onlyArg=process.argv.slice(4).find(a=>a.startsWith('--only-finding='));
const skipArg=process.argv.slice(4).find(a=>a.startsWith('--skip-finding='));
const runtimeDefaults=process.argv.slice(4).includes('--runtime-defaults');
for(const option of process.argv.slice(4))if(!/^(--resume-diagnostic=.+|--thinking=(true|false)|--sampling=qwen-reasoning|--only-finding=.+|--skip-finding=.+|--runtime-defaults)$/.test(option))throw Error('Unknown diagnostic option: '+option);
if(onlyArg&&skipArg)throw Error('Choose only-finding or skip-finding, not both.');
if(runtimeDefaults&&process.argv.slice(4).some(a=>a.startsWith('--thinking=')||a.startsWith('--sampling=')))throw Error('Runtime defaults cannot be combined with a diagnostic inference override.');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const matches=[];
for (const name of fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite'))) {
  const candidate=new DatabaseSync(path.join(folder,name),{readOnly:true});
  try {
    if (candidate.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='engine_runs'").get()
      && candidate.prepare('SELECT id FROM engine_runs WHERE id=?').get(runId)) matches.push(path.join(folder,name));
  } finally { candidate.close(); }
}
if (matches.length!==1) throw Error('Could not uniquely locate run.');
const sqlite=new DatabaseSync(matches[0],{readOnly:true});
const db={prepare(sql){let args=[];return {
  bind(...values){args=values;return this;},
  async all(){return {results:sqlite.prepare(sql).all(...args)};},
  async first(){return sqlite.prepare(sql).get(...args)||null;},
};}};
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const controller=new AbortController();
process.once('SIGINT',()=>controller.abort(new Error('Diagnostic interrupted.')));
process.once('SIGTERM',()=>controller.abort(new Error('Diagnostic interrupted.')));
try {
  const row=sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);
  if(row.status!=='paused')throw Error('Keep the application run paused during this focused diagnostic.');
  if(sqlite.prepare("SELECT id FROM engine_runs WHERE status IN ('queued','running') LIMIT 1").get()) throw Error('An application run is active; do not compete for model inference.');
  const input=await readJSON(db,row.input_json),state=await readState(db,row.state_json);
  const inference=runtimeDefaults?reviewInference(input.model,'review'):{thinking,sampling};
  if(input.engineVersion!==ENGINE_VERSION)throw Error('Saved engine version differs; do not substitute a new engine silently.');
  if(input.model.provider!=='ollama'||!input.model.digest)throw Error('This diagnostic requires a fixed installed Ollama model digest.');
  const modelName=input.model.id.replace(/^ollama:/,'');
  const response=await fetch(`${process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434'}/api/tags`);
  if(!response.ok)throw Error(`Ollama inventory returned ${response.status}`);
  const inventory=await response.json(),installed=inventory.models?.find(m=>m.name===modelName||m.model===modelName);
  if(installed?.digest!==input.model.digest)throw Error('Installed model differs from frozen run identity.');
  const producer=state.tasks.find(t=>t.id===producerTaskId);
  const cases=[];
  if(fixturePath) {
    const fixtures=JSON.parse(fs.readFileSync(fixturePath,'utf8'));
    for(const fixture of fixtures) {
      // Only this case's neutral claim and original sources enter the model packet.
      // Labels, expectations, previous cases and application evidence stay out.
      if(Object.keys(fixture).some(k=>!['id','statement','sources'].includes(k)))throw Error('Fixture has non-input fields. Keep answer keys separate.');
      const documents=fixture.sources.map((s,i)=>({id:`${fixture.id}-${i}`,scope:'starter',title:`Record ${i+1}`,fileName:`record-${i+1}.md`,
        fileKey:'diagnostic-only',contentType:'text/markdown',size:s.length,sha256:hash(s),revision:'1',plant:'Fictional diagnostic',
        extractionStatus:'ready',extractionNotes:'',extractedText:s,createdAt:new Date().toISOString()}));
      const caseState=await initializeState({incident:'Review the supplied records. No other incident facts are provided.',model:input.model,documents,answers:[]},1,null);
      const finding={id:fixture.id,revision:1,statement:fixture.statement,kind:'observation',subject:'',predicate:'',location:'',time:'',unit:'',qualifiers:'',
        spanIds:caseState.sources.filter(s=>s.scope==='starter').flatMap(s=>s.spans.map(p=>p.id)),tags:[],owners:['evidence-reading'],status:'proposed',
        reviewReason:'',opposedBy:[],history:[],introducedVersion:1,updatedVersion:1};
      caseState.findings.push(finding);cases.push({finding,state:caseState});
    }
  } else {
    if(producer?.status!=='completed')throw Error('Selected producer has not completed.');
    for(const finding of state.findings.filter(f=>producer.producedIds?.includes(f.id))) cases.push({finding,state});
  }
  if(onlyArg){const selected=cases.filter(c=>c.finding.id===onlyArg.slice('--only-finding='.length));cases.splice(0,cases.length,...selected);}
  if(skipArg){const excluded=skipArg.slice('--skip-finding='.length);if(!cases.some(c=>c.finding.id===excluded))throw Error('Excluded finding is not in this batch.');const selected=cases.filter(c=>c.finding.id!==excluded);cases.splice(0,cases.length,...selected);}
  if(!cases.length)throw Error('No findings to review.');
  if(state.sources.some(s=>s.spans.some(p=>p.modality)))throw Error('This text-only diagnostic does not load visual evidence.');
  const outputRoot=path.resolve('outputs');fs.mkdirSync(outputRoot,{recursive:true});
  const output=resumeArg?path.resolve(resumeArg.slice('--resume-diagnostic='.length))
    :fs.mkdtempSync(path.join(outputRoot,fixturePath?'claim-review-fresh-':'claim-review-check-'));
  if(!output.startsWith(outputRoot+path.sep))throw Error('Diagnostic output must be under the application outputs directory.');
  const write=(name,value)=>fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
  const baseline={runId,producerTaskId,generation:row.generation,status:row.status,inputHash:hash(input),stateHash:hash(state),snapshotHash:hash(row.snapshot_json)};
  const manifest={...baseline,createdAt:new Date().toISOString(),model:input.model,engine:ENGINE_VERSION,reviewPolicy:CLAIM_REVIEW_POLICY,
    fixturePath,fixtureHash:fixturePath?hash(JSON.parse(fs.readFileSync(fixturePath,'utf8'))):undefined,
    promptHash:hash(fs.readFileSync('prompts/claim-review/literal.md','utf8')),thinking:inference.thinking,sampling:inference.sampling,runtimeDefaults,
    execution:'Production executor/apply; read-only app DB. One fresh same-model call reviews the complete original claim against original evidence. No generated interpretation. No outputs cross cases.',
    targets:cases.map(({finding:f})=>({id:f.id,statement:f.statement,qualifiers:f.qualifiers,spanIds:f.spanIds}))};
  if(resumeArg) {
    const previous=JSON.parse(fs.readFileSync(path.join(output,'manifest.json'),'utf8'));
    for(const key of ['runId','producerTaskId','generation','inputHash','stateHash','snapshotHash','reviewPolicy','promptHash','thinking','fixtureHash'])
      if(previous[key]!==manifest[key])throw Error('Cannot continue a diagnostic whose inputs or policy changed: '+key);
    if(hash(previous.model)!==hash(manifest.model)||hash(previous.targets)!==hash(manifest.targets))throw Error('Diagnostic targets/model changed.');
    if(JSON.stringify(previous.sampling)!==JSON.stringify(manifest.sampling))throw Error('Diagnostic sampling changed.');
    if(fs.existsSync(path.join(output,'summary.json')))throw Error('Completed diagnostic is immutable; create a new explicitly labeled evaluation.');
  } else write('manifest.json',manifest);
  console.log(JSON.stringify({event:'started',output,targets:cases.length,runId}));
  const results=[];
  for(const [index,{finding,state:caseState}] of cases.entries()) {
    const current=sqlite.prepare('SELECT status,generation FROM engine_runs WHERE id=?').get(runId);
    if(current.status!=='paused'||current.generation!==row.generation)throw Error('Application run changed during diagnostic; stop before further inference.');
    if(controller.signal.aborted)throw controller.signal.reason;
    const ids=[finding.id],query=findingText(finding),required=finding.spanIds;
    const task={id:await digest(['review','claim-review',ids,query,required]),kind:'review',owner:'claim-review',targetIds:ids,
      dependsOn:producer?[producer.id]:[],status:'running',attempts:1,query,requiredSpanIds:required,cacheKey:'',error:'',reused:false,
      evidenceIds:[],omittedEvidenceIds:[],contextBytes:0,durationMs:0,inputTokens:0,outputTokens:0,createdAt:new Date().toISOString()};
    const prefix=String(index+1).padStart(2,'0');
    const outcomePath=path.join(output,`${prefix}-outcome.json`),failurePath=path.join(output,`${prefix}-failure.json`);
    if(fs.existsSync(outcomePath)) {results.push(JSON.parse(fs.readFileSync(outcomePath,'utf8')));continue;}
    if(fs.existsSync(failurePath)) {
      results.push({findingId:finding.id,statement:finding.statement,failure:JSON.parse(fs.readFileSync(failurePath,'utf8'))});continue;
    }
    if(fs.readdirSync(output).some(name=>name.startsWith(prefix+'-')))throw Error('Unfinished call exists; do not silently retry an uncertain request: '+prefix);
    const traceFor=stage=>{
      const streamPath=path.join(output,`${prefix}-${stage}-stream.txt`);
      fs.writeFileSync(streamPath,'',{flag:'wx'});
      return {request:async value=>write(`${prefix}-${stage}-request.json`,value),append:async value=>fs.appendFileSync(streamPath,value),
        complete:async(status,result,error='')=>write(`${prefix}-${stage}-provider.json`,{status,result,error,completedAt:new Date().toISOString()})};
    };
    console.log(JSON.stringify({event:'reviewing',index:index+1,findingId:finding.id,statement:finding.statement}));
    const copy=structuredClone(caseState);
    let appliedOutput;
    try {
      const result=await executeTask(copy,task,input.model,row.track_id,{cached:async()=>null},undefined,undefined,{signal:controller.signal,trace:traceFor('review'),...(runtimeDefaults?{}:inference)});
      appliedOutput=result.output;
      applyEvidenceTask(copy,task,result.output,result.refs);
      const reviewed=copy.findings.find(f=>f.id===finding.id);
      const outcome={findingId:finding.id,statement:finding.statement,output:result.output,effectiveFinding:reviewed,
        newQuestions:copy.questions.filter(q=>!caseState.questions.some(old=>old.id===q.id)),newQuarantine:copy.quarantine.slice(caseState.quarantine.length),
        references:{sources:[...result.refs.sources],findings:[...result.refs.findings]},durationMs:result.durationMs,
        inputTokens:result.inputTokens,outputTokens:result.outputTokens,cacheKey:result.cacheKey};
      write(`${prefix}-outcome.json`,outcome);results.push(outcome);
      console.log(JSON.stringify({event:'reviewed',index:index+1,status:reviewed.status,reviewExecution:reviewed.reviewExecution,conflicts:reviewed.reviewAssessment?.evidenceConflicts?.length,causalRole:reviewed.causalRole,
        reason:reviewed.reviewReason,durationMs:result.durationMs}));
    } catch(error) {
      const failure={message:error.message,attempts:error.attempts,failedAt:new Date().toISOString(),output:appliedOutput,
        effectiveFinding:copy.findings.find(f=>f.id===finding.id),
        recoveredQuestions:copy.questions.filter(q=>!caseState.questions.some(old=>old.id===q.id))};
      write(`${prefix}-failure.json`,failure);results.push({findingId:finding.id,statement:finding.statement,failure});
      console.log(JSON.stringify({event:'case-failed',index:index+1,...failure}));
      // No retry or repaired output. Independent cases still provide useful data.
      if(/fetch failed|ECONN|unreachable|HTTP (401|403|429|50\d)|digest changed/i.test(error.message))throw error;
    }
  }
  const after=sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);
  const preserved=after.generation===row.generation&&after.status===row.status&&hash(await readState(db,after.state_json))===baseline.stateHash
    &&hash(await readJSON(db,after.input_json))===baseline.inputHash&&hash(after.snapshot_json)===baseline.snapshotHash;
  write('summary.json',{runId,finishedAt:new Date().toISOString(),applicationRunUnchanged:preserved,
    results:results.map(r=>r.failure?{findingId:r.findingId,statement:r.statement,status:'unreviewed',reviewExecution:'incomplete',failure:r.failure}:{findingId:r.findingId,statement:r.statement,status:r.effectiveFinding.status,reviewExecution:r.effectiveFinding.reviewExecution,
      conflicts:r.effectiveFinding.reviewAssessment?.evidenceConflicts?.length||0,causalRole:r.effectiveFinding.causalRole,
      reason:r.effectiveFinding.reviewReason,durationMs:r.durationMs,inputTokens:r.inputTokens,outputTokens:r.outputTokens})});
  if(!preserved)throw Error('Application state changed during diagnostic; inspect before relying on comparisons.');
  console.log(JSON.stringify({event:'completed',output,reviews:results.length,applicationRunUnchanged:preserved}));
} finally {sqlite.close();}

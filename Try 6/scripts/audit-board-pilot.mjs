// Bounded, read-only investigation pilot. Uses the production executor/apply
// functions and real model; never commits diagnostic judgments to the app.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {readJSON,readState} from '../src/engine/tasks/artifacts.ts';
import {executeTask} from '../src/engine/tasks/executor.ts';
import {applyEvidenceTask} from '../src/stages/evidence-reading/task.ts';
import {applyBoardTask} from '../src/engine/board/changes.ts';
import {project} from '../src/engine/board/projection.ts';
import {findingText} from '../src/engine/records.ts';
import {CLAIM_REVIEW_POLICY} from '../src/engine/review/literal-contract.ts';
import {ENGINE_VERSION} from '../src/engine/types.ts';
import {initializeState} from '../src/engine/tasks/planner.ts';
import {invalidateReview} from '../src/engine/review/interpretation.ts';

const [runId,selectionFile,...args]=process.argv.slice(2);
if(!runId||!selectionFile)throw Error('Usage: audit-board-pilot.mjs RUN_ID SELECTION_JSON [COMPLETED_REVIEW_DIRECTORY ...] [--previous=DIR --document=MD]');
const previousPath=args.find(a=>a.startsWith('--previous='))?.slice('--previous='.length);
const documentPath=args.find(a=>a.startsWith('--document='))?.slice('--document='.length);
const reverifyPath=args.find(a=>a.startsWith('--reverify='))?.slice('--reverify='.length);
if(!!previousPath!==!!documentPath)throw Error('Controlled comparison requires both a completed previous pilot and one document.');
if(args.some(a=>a.startsWith('--')&&!a.startsWith('--previous=')&&!a.startsWith('--document=')&&!a.startsWith('--reverify=')))throw Error('Unknown pilot option.');
const reviewDirectories=args.filter(a=>!a.startsWith('--'));
if(previousPath&&reviewDirectories.length)throw Error('New evidence requires fresh reviews; do not import earlier review outputs.');
if(reverifyPath&&(previousPath||documentPath||reviewDirectories.length))throw Error('Reverification takes only a completed baseline pilot, no other imports.');
const selected=JSON.parse(fs.readFileSync(selectionFile,'utf8'));
if(!Array.isArray(selected)||!selected.length||selected.some(id=>typeof id!=='string')||new Set(selected).size!==selected.length)
  throw Error('Selection must be a nonempty unique list of existing finding IDs, not expected answers.');
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const matches=[];
for(const name of fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite'))) {
  const db=new DatabaseSync(path.join(folder,name),{readOnly:true});
  try {if(db.prepare("SELECT name FROM sqlite_master WHERE name='engine_runs'").get()
    &&db.prepare('SELECT id FROM engine_runs WHERE id=?').get(runId))matches.push(path.join(folder,name));}finally{db.close();}
}
if(matches.length!==1)throw Error('Saved run not uniquely identified.');
const sqlite=new DatabaseSync(matches[0],{readOnly:true});
const db={prepare(sql){let args=[];return {bind(...a){args=a;return this;},async first(){return sqlite.prepare(sql).get(...args);},async all(){return {results:sqlite.prepare(sql).all(...args)};}};}};
const controller=new AbortController();
process.once('SIGINT',()=>controller.abort(new Error('Pilot interrupted; no hidden retry.')));
process.once('SIGTERM',()=>controller.abort(new Error('Pilot interrupted; no hidden retry.')));
try {
  const saved=sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);
  if(saved.status!=='paused'||sqlite.prepare("SELECT id FROM engine_runs WHERE status IN ('queued','running') LIMIT 1").get())throw Error('Keep all application inference paused during the pilot.');
  const input=await readJSON(db,saved.input_json),original=await readState(db,saved.state_json);
  if(input.engineVersion!==ENGINE_VERSION||input.model.provider!=='ollama'||!input.model.digest)throw Error('Pilot requires matching engine and frozen Ollama identity.');
  const installed=await fetch(`${process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434'}/api/tags`).then(r=>r.json());
  if(!installed.models?.some(m=>(m.name===input.model.id.replace(/^ollama:/,'')||m.model===input.model.id.replace(/^ollama:/,''))&&m.digest===input.model.digest))throw Error('Model digest changed.');
  if(selected.some(id=>!original.findings.some(f=>f.id===id)))throw Error('Selected finding does not belong to this run.');
  let state=structuredClone(original);
  const baseline={inputHash:hash(input),stateHash:hash(original),snapshotHash:hash(saved.snapshot_json),generation:saved.generation};
  // Explicit study scope, not deletions or new count limits in the RCA engine.
  // Retain original sources and questions, but keep unrelated unreviewed claims
  // out of the causal neighborhood for this bounded pilot.
  state.findings=state.findings.filter(f=>selected.includes(f.id));
  state.tasks=[];state.propositions=[];state.relationships=[];state.changes=[];state.quarantine=[];
  delete state.pauseReason;delete state.pauseAfterTaskId;
  let controlledDocument,parentPilotStateHash;
  if(reverifyPath) {
    const parent=JSON.parse(fs.readFileSync(path.join(reverifyPath,'manifest.json'),'utf8'));
    const summary=JSON.parse(fs.readFileSync(path.join(reverifyPath,'summary.json'),'utf8'));
    if(parent.runId!==runId||parent.reviewPolicy!==CLAIM_REVIEW_POLICY||parent.controlledDocument||!summary.applicationRunUnchanged||summary.failed?.length
      ||hash(parent.selected)!==hash(selected)||['inputHash','stateHash','snapshotHash','generation'].some(k=>parent[k]!==baseline[k]))throw Error('Reverification parent does not match this checkpoint.');
    state=JSON.parse(fs.readFileSync(path.join(reverifyPath,'state.json'),'utf8'));
    parentPilotStateHash=hash(state);state.tasks=[];state.changes=[];
  }
  if(previousPath) {
    const parent=JSON.parse(fs.readFileSync(path.join(previousPath,'manifest.json'),'utf8'));
    const summary=JSON.parse(fs.readFileSync(path.join(previousPath,'summary.json'),'utf8'));
    if(parent.runId!==runId||parent.reviewPolicy!==CLAIM_REVIEW_POLICY||parent.controlledDocument||!summary.applicationRunUnchanged||summary.failed?.length
      ||hash(parent.selected)!==hash(selected)||['inputHash','stateHash','snapshotHash','generation'].some(k=>parent[k]!==baseline[k]))throw Error('Parent is not the completed baseline pilot for this checkpoint and selection.');
    const previous=JSON.parse(fs.readFileSync(path.join(previousPath,'state.json'),'utf8'));
    parentPilotStateHash=hash(previous);
    if(path.extname(documentPath)!=='.md')throw Error('This text-only controlled comparison accepts one markdown source.');
    const extractedText=fs.readFileSync(documentPath,'utf8'),sha256=createHash('sha256').update(extractedText).digest('hex');
    const doc={id:'controlled:'+sha256,scope:'answer',title:path.basename(documentPath),fileName:path.basename(documentPath),
      fileKey:path.resolve(documentPath),contentType:'text/markdown',size:Buffer.byteLength(extractedText),sha256,revision:'1',plant:'Synthetic diagnostic',
      extractionStatus:'ready',extractionNotes:'Existing synthetic progressive document; preserved verbatim for this controlled comparison.',extractedText,createdAt:new Date().toISOString()};
    input.documents=[...input.documents,doc];
    state=await initializeState(input,previous.version+1,previous);
    controlledDocument={path:path.resolve(documentPath),id:doc.id,sha256};
  }
  const addedSpans=controlledDocument?state.sources.filter(s=>s.id===controlledDocument.id).flatMap(s=>s.spans.map(p=>p.id)):[];
  const imported=[];
  for(const directory of reviewDirectories) {
    const manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'),'utf8'));
    const summary=JSON.parse(fs.readFileSync(path.join(directory,'summary.json'),'utf8'));
    if(manifest.runId!==runId||manifest.reviewPolicy!==CLAIM_REVIEW_POLICY||!summary.applicationRunUnchanged
      ||['inputHash','stateHash','snapshotHash','generation'].some(k=>manifest[k]!==baseline[k]))throw Error('Review source is not the same preserved checkpoint/policy.');
    for(const name of fs.readdirSync(directory).filter(n=>/^\d+-outcome.json$/.test(n))) {
      const result=JSON.parse(fs.readFileSync(path.join(directory,name),'utf8'));
      if(!selected.includes(result.findingId))continue;
      const finding=state.findings.find(f=>f.id===result.findingId);
      if(finding.statement!==result.statement)throw Error('Saved claim changed.');
      // Reapply the original output through the current gate; do not copy an
      // approved flag or author a new verdict in this diagnostic.
      const task={id:`import:${result.cacheKey}`,kind:'review',owner:'claim-review',targetIds:[finding.id],reused:true};
      applyEvidenceTask(state,task,result.output,{sources:new Map(result.references.sources),findings:new Map(result.references.findings),questions:new Map()});
      imported.push({findingId:finding.id,artifact:path.resolve(directory,name),cacheKey:result.cacheKey});
    }
  }
  fs.mkdirSync('outputs',{recursive:true});
  const output=fs.mkdtempSync(path.resolve('outputs/audited-board-pilot-'));
  const write=(name,data)=>fs.writeFileSync(path.join(output,name),JSON.stringify(data,null,2)+'\n',{flag:'wx'});
  write('manifest.json',{runId,...baseline,createdAt:new Date().toISOString(),model:input.model,reviewPolicy:CLAIM_REVIEW_POLICY,selected,imported,
    controlledDocument,parentPilot:previousPath||reverifyPath?path.resolve(previousPath||reverifyPath):undefined,parentPilotStateHash,studyInputHash:hash(input),
    verificationOnly:!!reverifyPath,
    boundary:'Read-only diagnostic from a saved checkpoint, not a production version or overall acceptance. No storyteller, hidden evidence, fallback, retry or edited model verdict. Any added document is explicitly identified above.'});
  write('input.json',input);
  let sequence=0;
  async function execute(kind,id,query,required) {
    controller.signal.throwIfAborted();
    const live=sqlite.prepare('SELECT status,generation FROM engine_runs WHERE id=?').get(runId);
    if(live.status!=='paused'||live.generation!==saved.generation)throw Error('Application changed; stop before inference.');
    const prefix=String(++sequence).padStart(2,'0')+'-'+kind;
    const task={id:`pilot:${prefix}`,kind,owner:kind==='review'?'claim-review':kind==='causal'?'causal-analysis':'causal-verification',targetIds:[id],query,
      requiredSpanIds:[...new Set([...required,...addedSpans])],dependsOn:[],status:'running',attempts:1,cacheKey:'',error:'',reused:false,evidenceIds:[],omittedEvidenceIds:[],contextBytes:0,durationMs:0,inputTokens:0,outputTokens:0,createdAt:new Date().toISOString()};
    state.tasks.push(task);
    if(kind==='review')invalidateReview(state.findings.find(f=>f.id===id),'unreviewed','New review pending; no stale approval.',state);
    const stream=path.join(output,prefix+'-stream.txt');fs.writeFileSync(stream,'',{flag:'wx'});
    const trace={request:async data=>write(prefix+'-request.json',data),append:async text=>fs.appendFileSync(stream,text),
      complete:async(status,result,error)=>write(prefix+'-provider.json',{status,result,error})};
    console.log(JSON.stringify({event:'task',output,prefix,kind,target:id}));
    try {
      const result=await executeTask(state,task,input.model,saved.track_id,{cached:async()=>null},undefined,undefined,{signal:controller.signal,trace});
      Object.assign(task,{durationMs:result.durationMs,inputTokens:result.inputTokens,outputTokens:result.outputTokens,cacheKey:result.cacheKey,evidenceIds:result.evidenceIds});
      if(kind==='review')applyEvidenceTask(state,task,result.output,result.refs);else applyBoardTask(state,task,result.output,result.refs);
      task.status='completed';
      write(prefix+'-applied.json',{output:result.output,findings:state.findings,propositions:state.propositions,relationships:state.relationships});
      console.log(JSON.stringify({event:'applied',prefix,status:kind==='review'?state.findings.find(f=>f.id===id)?.status:'completed'}));
    } catch(error) {
      task.status='failed';task.error=error.message;write(prefix+'-failure.json',{message:error.message,attempts:error.attempts});
      console.log(JSON.stringify({event:'failed',prefix,error:error.message}));
      if(controller.signal.aborted)throw error;
      if(/fetch failed|ECONN|unreachable|digest changed|token limit|stream|context.*exceed/i.test(error.message))throw error;
    } finally {write(prefix+'-state.json',state);}
  }
  for(const f of state.findings)if(!reverifyPath&&(controlledDocument||f.reviewAssessment?.policy!==CLAIM_REVIEW_POLICY||f.reviewExecution!=='complete'))await execute('review',f.id,findingText(f),f.spanIds);
  // Only independently supported, non-context claims enter this board pilot.
  for(const f of state.findings)if(!reverifyPath&&f.status==='supported'&&f.causalRole!=='context')await execute('causal',f.id,findingText(f),f.spanIds);
  for(const p of state.propositions)await execute('verify',p.id,`${p.label} ${p.detail}`,p.spanIds);
  for(const e of state.relationships) {
    if([e.from,e.to].some(id=>id!=='focal'&&!state.propositions.some(p=>p.id===id))){e.status='unknown';e.reviewReason='Endpoint outside this reviewed pilot; not an established connection.';continue;}
    await execute('verify',e.id,`${e.rationale} ${e.counterfactual} ${e.alternative}`,e.spanIds);
  }
  const after=sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);
  const unchanged=after.generation===saved.generation&&after.status===saved.status&&hash(await readState(db,after.state_json))===baseline.stateHash
    &&hash(await readJSON(db,after.input_json))===baseline.inputHash&&hash(after.snapshot_json)===baseline.snapshotHash;
  write('state.json',state);write('snapshot.json',project(state,input,'partial'));
  write('summary.json',{runId,finishedAt:new Date().toISOString(),applicationRunUnchanged:unchanged,selected,imported,
    findings:state.findings.map(f=>({id:f.id,statement:f.statement,status:f.status,role:f.causalRole,reason:f.reviewReason})),
    propositions:state.propositions,relationships:state.relationships,questions:state.questions.filter(q=>!original.questions.some(old=>old.id===q.id)),
    failed:state.tasks.filter(t=>t.status==='failed'),semanticAcceptance:'UNASSESSED — inspect every node and relationship against the originals. Not a completed RCA.'});
  if(!unchanged)throw Error('Original application changed during pilot.');
  console.log(JSON.stringify({event:'completed',output,nodes:state.propositions.length,edges:state.relationships.length,applicationRunUnchanged:unchanged}));
}finally{sqlite.close();}

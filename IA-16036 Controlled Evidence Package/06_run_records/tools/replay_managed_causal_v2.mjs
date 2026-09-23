// Causal-only comparison. Read frozen V2, preserve every upstream output, and
// never write an app database or commit a replacement investigation version.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {localHttpOnce} from './local_http_once.mjs';

const workspace=fileURLToPath(new URL('../../../',import.meta.url));
const source=path.join(workspace,'IA-16036 Controlled Evidence Package/06_run_records/qwen-focused-v2-no-text-caps-sgaA81');
const app=path.join(workspace,'Try 4');
const reuseDirectory=process.argv[2] ? path.resolve(process.argv[2]) : null;
if(reuseDirectory && (!reuseDirectory.startsWith(path.dirname(source)+path.sep+'qwen-v2-managed-causal-'))) throw Error('Only a prior isolated managed-causal replay may supply checkpoints');
const dir=await fs.mkdtemp(path.join(path.dirname(source),'qwen-v2-managed-causal-'));
const save=(name,value)=>fs.writeFile(path.join(dir,name),JSON.stringify(value,null,2),{flag:'wx'});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=async name=>JSON.parse(await fs.readFile(path.join(source,name),'utf8'));
const original=await read('manifest.json'), snapshot=await read('after-resume.json');
const oldVersion=await read('version-2.json'), previous=await read('version-1.json');
const sourceV2Sha256=sha(await fs.readFile(path.join(source,'version-2.json')));
const calls=snapshot.incident.tracks[0].checkpoints.filter(c=>c.targetVersion===2&&c.stage==='causal-analysis'&&c.payload?.kind==='model-call');
const nodePackets=calls.filter(c=>c.payload.requestIdentity.schema.properties.nodes).map(c=>c.payload.requestIdentity.packet);
assert.equal(nodePackets.length,7);
const saved=nodePackets[0];
const savedClaims=nodePackets.flatMap(p=>p.evidenceClaims);
assert.equal(new Set(savedClaims.map(c=>c.id)).size,96);
const current=oldVersion.analysis;
assert.equal(current.evidenceClaims.length,96);
assert.equal(current.answers.length,4);
assert.equal(saved.evidenceSegments.length,8);
const packet={originalIncident:saved.originalIncident,structuredIncident:saved.structuredIncident,
  evidenceClaims:current.evidenceClaims,evidenceSegments:saved.evidenceSegments,documentCoverage:saved.documentCoverage,
  specialistKnowledgeBases:current.specialistKnowledgeBases,questions:current.questions,
  conflicts:saved.conflicts,adjudicationConflicts:saved.adjudicationConflicts,
  previousBoard:previous.analysis.causalBoard,previousEvidenceClaims:previous.analysis.evidenceClaims,
  answers:current.answers};
await fs.mkdir(path.join(dir,'frozen-app/scripts'),{recursive:true});
for(const name of ['src','prompts']) await fs.cp(path.join(app,name),path.join(dir,'frozen-app',name),{recursive:true});
await fs.copyFile(path.join(app,'package.json'),path.join(dir,'frozen-app/package.json'));
await fs.copyFile(path.join(app,'scripts/register-test-loader.mjs'),path.join(dir,'frozen-app/scripts/register-test-loader.mjs'));
await fs.symlink(path.join(app,'node_modules'),path.join(dir,'frozen-app/node_modules'));
await fs.mkdir(path.join(dir,'model-capture')); await fs.mkdir(path.join(dir,'checkpoints'));
const codeHashes={};
async function hashTree(folder){for(const entry of await fs.readdir(folder,{withFileTypes:true})){
  const full=path.join(folder,entry.name);
  if(entry.isDirectory())await hashTree(full);else codeHashes[path.relative(path.join(dir,'frozen-app'),full)]=sha(await fs.readFile(full));
}}
await hashTree(path.join(dir,'frozen-app/src'));await hashTree(path.join(dir,'frozen-app/prompts'));
await import(pathToFileURL(path.join(dir,'frozen-app/scripts/register-test-loader.mjs')).href);
const {runCausalAnalysis}=await import(pathToFileURL(path.join(dir,'frozen-app/src/stages/causal-analysis/run.ts')).href);
const {runCausalVerification}=await import(pathToFileURL(path.join(dir,'frozen-app/src/stages/causal-verification/run.ts')).href);
const {causalEvidenceView}=await import(pathToFileURL(path.join(dir,'frozen-app/src/stages/causal-analysis/evidence-view.ts')).href);
const {withStageRecovery}=await import(pathToFileURL(path.join(dir,'frozen-app/src/orchestrator/stage-recovery.ts')).href);
const {PROMPT_VERSION}=await import(pathToFileURL(path.join(dir,'frozen-app/src/prompts/manifest.ts')).href);
// Ensure the causal claim view is identical to the saved input, before ordering.
assert.deepEqual(causalEvidenceView(packet).evidenceClaims,savedClaims);
const installed=JSON.parse((await localHttpOnce('http://127.0.0.1:11434/api/tags')).body);
assert.equal(installed.models.find(m=>m.name==='qwen3.5:latest')?.digest,original.expectedModelDigest);
const version=JSON.parse((await localHttpOnce('http://127.0.0.1:11434/api/version')).body).version;
assert.equal(version,'0.32.3','No-truncation behavior has been checked against this installed version; review any backend change.');
await save('manifest.json',{kind:'saved-V2-causal-and-verification-only-comparison',createdAt:new Date().toISOString(),
  sourceRun:source,sourceV2Sha256,
  model:original.model,digest:original.expectedModelDigest,ollamaVersion:version,promptVersion:PROMPT_VERSION,
  claims:96,documents:8,answers:4,upstreamRerun:false,storytellerRerun:false,newEvidence:false,appVersionCommitted:false,
  evidenceIdentity:'Exact saved causal claim view asserted equal to the seven original NODE partitions.',
  oldBoard:{nodes:current.causalBoard.nodes.length,edges:current.causalBoard.edges.length},
  previousBoardCharacters:JSON.stringify(saved.previousBoard).length,
  workingBoardCharacters:JSON.stringify(causalEvidenceView(packet).previousBoard).length,
  evaluatorExpectations:'operator-only; never included in any request',checkpointReuseSource:reuseDirectory,runnerPid:process.pid,codeHashes});
await save('causal-input.json',packet);await save('baseline-version-2.json',oldVersion);
console.log(JSON.stringify({event:'started',directory:dir,promptVersion:PROMPT_VERSION,appVersionCommitted:false}));
const logFile=path.join(workspace,'R3 Benchmark Package/06_run_records/qwen-story-autonomous-N9Y0lS/ollama.log');
const logStart=(await fs.stat(logFile)).size;
let requests=0,checkpoints=0;
globalThis.fetch=async(url,options)=>{
  if(String(url)!=='http://127.0.0.1:11434/api/chat'||options?.method!=='POST')throw Error('Replay prohibits other network requests');
  const body=JSON.parse(options.body);
  assert.equal(body.model,'qwen3.5:latest');assert.equal(body.think,false);assert.equal(body.options.temperature,0);
  assert.equal(body.options.num_ctx,32768);assert.equal(body.truncate,false);assert.equal(body.shift,false);
  const id=String(++requests).padStart(4,'0'),started=Date.now();
  await save(`model-capture/${id}-request.json`,body);
  console.log(JSON.stringify({event:'request',id,bytes:Buffer.byteLength(options.body),at:new Date().toISOString()}));
  const response=await localHttpOnce(String(url),{method:'POST',headers:{'content-type':'application/json'},body:options.body,
    timeoutMs:body.options.num_predict===4000?360000:480000});
  await fs.writeFile(path.join(dir,`model-capture/${id}-response.json`),response.body,{flag:'wx'});
  const result=JSON.parse(response.body);
  await save(`model-capture/${id}-metadata.json`,{status:response.status,durationMs:Date.now()-started,
    inputTokens:result.prompt_eval_count,outputTokens:result.eval_count,doneReason:result.done_reason});
  console.log(JSON.stringify({event:'response',id,status:response.status,inputTokens:result.prompt_eval_count,outputTokens:result.eval_count}));
  return new Response(response.body,{status:response.status,headers:{'content-type':'application/json'}});
};
const cache=new Map();
if(reuseDirectory) {
  const visited=new Set();
  async function loadCache(directory) {
    if(visited.has(directory))throw Error('Checkpoint lineage cycle');
    if(!directory.startsWith(path.dirname(source)+path.sep+'qwen-v2-managed-causal-'))throw Error('Invalid checkpoint lineage');
    visited.add(directory);
    const priorManifest=JSON.parse(await fs.readFile(path.join(directory,'manifest.json')));
    assert.equal(priorManifest.digest,original.expectedModelDigest);
    assert.equal(sha(await fs.readFile(path.join(directory,'causal-input.json'))),sha(await fs.readFile(path.join(dir,'causal-input.json'))));
    if(priorManifest.checkpointReuseSource)await loadCache(priorManifest.checkpointReuseSource);
    for(const name of (await fs.readdir(path.join(directory,'checkpoints'))).sort()) {
      const checkpoint=JSON.parse(await fs.readFile(path.join(directory,'checkpoints',name)));
      if(checkpoint.kind==='model-call')cache.set(checkpoint.key,checkpoint.response);
    }
  }
  await loadCache(reuseDirectory);
  console.log(JSON.stringify({event:'checkpoint-cache-loaded',count:cache.size,source:reuseDirectory}));
}
const recovery={cache,fingerprint:sha(JSON.stringify(packet)),persist:async(stage,payload)=>{
  const id=String(++checkpoints).padStart(4,'0');await save(`checkpoints/${id}.json`,{stage,createdAt:new Date().toISOString(),...payload});
  console.log(JSON.stringify({event:'checkpoint',id,stage,kind:payload.kind}));
}};
try {
  await withStageRecovery(recovery,async()=>{
    const model={id:'ollama:qwen3.5:latest',name:'qwen3.5:latest',provider:'ollama',available:true};
    const causal=await runCausalAnalysis(model,packet);
    await save('causal-result.json',{...causal,keyToId:[...causal.keyToId]});
    console.log(JSON.stringify({event:'causal-completed',nodes:causal.board.nodes.length,edges:causal.board.edges.length,branchRevisions:causal.board.branchRevisions?.length}));
    const verified=await runCausalVerification(model,packet,causal.board,causal.keyToId);
    await save('verification-result.json',verified);
    const b=verified.board;
    await save('result.json',{status:'completed',completedAt:new Date().toISOString(),requests,checkpoints,appVersionCommitted:false,
      nodes:b.nodes.length,edges:b.edges.length,verifiedNodes:b.nodes.filter(n=>n.verified).length,verifiedEdges:b.edges.filter(e=>e.verified).length,
      revisions:b.branchRevisions?.length,unresolvedRevisions:b.branchRevisions?.filter(r=>r.action==='unresolved').length,
      findings:b.verificationFindings.length,maturity:b.maturity});
    console.log(JSON.stringify({event:'completed',directory:dir,nodes:b.nodes.length,edges:b.edges.length,requests}));
  });
} catch(error) {
  await save('failure.json',{error:String(error),stack:error.stack,at:new Date().toISOString(),requests,checkpoints,appVersionCommitted:false});
  console.error(error);process.exitCode=1;
} finally {
  const log=await fs.readFile(logFile);await fs.writeFile(path.join(dir,'ollama-log-excerpt.txt'),log.subarray(logStart),{flag:'wx'});
  assert.equal(sha(await fs.readFile(path.join(source,'version-2.json'))),sourceV2Sha256);
}

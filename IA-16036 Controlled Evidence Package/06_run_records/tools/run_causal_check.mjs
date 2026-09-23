// Isolated diagnostic only. Reuses frozen upstream outputs; NEVER writes an app version.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {localHttpOnce} from './local_http_once.mjs';
import {reconstructCausalInput} from './reconstruct_causal_input.mjs';
import {compactCausalPacket,expandCausalPacket} from '../../../Try 4/src/knowledge/causal-packet.ts';
import {assertPacketFits} from '../../../Try 4/src/knowledge/packet-limits.ts';
import {runCausalAnalysis} from '../../../Try 4/src/stages/causal-analysis/run.ts';
import {runCausalVerification} from '../../../Try 4/src/stages/causal-verification/run.ts';
import {PROMPT_VERSION,promptFor} from '../../../Try 4/src/prompts/manifest.ts';

const source=path.resolve(process.argv[2]||'');
const original=JSON.parse(await fs.readFile(path.join(source,'manifest.json')));
const packet=reconstructCausalInput(source);
if(JSON.stringify(packet).length!==66798)throw Error('Unexpected saved pre-causal boundary');
const compact=compactCausalPacket(packet);
assert.deepEqual(expandCausalPacket(compact),packet);
assertPacketFits('causal-analysis',compact);
const installed=await(await fetch('http://127.0.0.1:11434/api/tags',{signal:AbortSignal.timeout(30000)})).json();
if(installed.models.find(m=>m.name==='qwen3.5:latest')?.digest!==original.expectedModelDigest)throw Error('Model digest changed');
const dir=await fs.mkdtemp(path.join(path.dirname(source),'qwen-b0-causal-check-'));
const save=(name,value)=>fs.writeFile(path.join(dir,name),JSON.stringify(value,null,2),{flag:'wx'});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const app=fileURLToPath(new URL('../../../Try 4/',import.meta.url));
await fs.mkdir(path.join(dir,'frozen-code'));
const codeHashes={};
async function walk(folder){for(const entry of await fs.readdir(folder,{withFileTypes:true})){
  const full=path.join(folder,entry.name);
  if(entry.isDirectory())await walk(full);else codeHashes[path.relative(app,full)]=sha(await fs.readFile(full));
}}
for(const name of ['src','prompts']){
  await walk(path.join(app,name));
  await fs.cp(path.join(app,name),path.join(dir,'frozen-code',name),{recursive:true,errorOnExist:true,force:false});
}
await fs.mkdir(path.join(dir,'model-capture'));
await save('manifest.json',{kind:'causal-and-verification-only-diagnostic',createdAt:new Date().toISOString(),
  sourceRun:source,sourceSnapshotSha256:sha(await fs.readFile(path.join(source,'failure-snapshot.json'))),
  model:original.model,digest:original.expectedModelDigest,promptVersion:PROMPT_VERSION,
  upstreamOutputs:'Reused unchanged from stopped B0; not regenerated',appVersionCommitted:false,
  storyteller:false,newEvidence:false,wholeCycleRetry:false,maximumModelCalls:4,
  preCausalCharacters:66798,wireCharacters:JSON.stringify(compact).length,exactRoundTrip:true,
  codeHashes,transport:'Node-local diagnostic capture using explicit 8-minute causal and 6-minute verification deadlines; no implicit 5-minute headers timeout.'});
await save('causal-input.json',packet);
await save('causal-wire-input.json',compact);
console.log(JSON.stringify({event:'diagnostic-started',directory:dir,appVersionCommitted:false}));
const roles=new Map(['causal-analysis','causal-verification'].map(stage=>[promptFor(stage),stage]));
const counts=new Map();let calls=0;
globalThis.fetch=async(url,options)=>{
  if(String(url)!=='http://127.0.0.1:11434/api/chat'||options?.method!=='POST')throw Error('Diagnostic prohibits other network mutations');
  const body=JSON.parse(options.body),stage=roles.get(body.messages[0].content);
  if(!stage||body.model!=='qwen3.5:latest'||body.stream!==false||body.think!==false||body.options.temperature!==0||body.options.num_ctx!==32768)throw Error('Unexpected stage/model/settings');
  if(body.messages.some(m=>/V-201|V-202|CH-218|IA-P0[1-9]|IA-C0[12]|BEGIN PRIVATE|evaluator-frozen/.test(m.content)))throw Error('B0 leakage tripwire');
  counts.set(stage,(counts.get(stage)||0)+1);
  if(counts.get(stage)>2||++calls>4)throw Error('Bounded stage attempts exhausted');
  const id=String(calls).padStart(4,'0'),started=Date.now();
  await save(`model-capture/${id}-request.json`,body);
  console.log(JSON.stringify({event:'request',id,stage}));
  const result=await localHttpOnce(String(url),{method:'POST',headers:{'content-type':'application/json'},body:options.body,timeoutMs:stage==='causal-analysis'?480000:360000});
  await fs.writeFile(path.join(dir,`model-capture/${id}-response.json`),result.body,{flag:'wx'});
  const raw=JSON.parse(result.body);
  await save(`model-capture/${id}-metadata.json`,{stage,status:result.status,durationMs:Date.now()-started,inputTokens:raw.prompt_eval_count,outputTokens:raw.eval_count,doneReason:raw.done_reason});
  return new Response(result.body,{status:result.status,headers:{'content-type':'application/json'}});
};
try{
  const model={id:'ollama:qwen3.5:latest',name:'qwen3.5:latest',provider:'ollama'};
  const causal=await runCausalAnalysis(model,packet);
  await save('causal-result.json',{...causal,keyToId:Object.fromEntries(causal.keyToId)});
  const verificationPacket={originalIncident:packet.originalIncident,answers:packet.answers,evidenceSegments:packet.evidenceSegments,
    evidenceClaims:packet.evidenceClaims,conflicts:packet.conflicts,sourceAssessments:packet.sourceAssessments,adjudicationConflicts:packet.adjudicationConflicts};
  const verified=await runCausalVerification(model,verificationPacket,causal.board,causal.keyToId);
  await save('verification-result.json',verified);
  await save('board.json',verified.board);
  for(const [name,hash] of Object.entries(codeHashes))if(sha(await fs.readFile(path.join(app,name)))!==hash)throw Error(`Source changed during diagnostic: ${name}`);
  const result={status:'diagnostic-completed',completedAt:new Date().toISOString(),calls,appVersionCommitted:false,
    nodes:verified.board.nodes.length,edges:verified.board.edges.length,findings:verified.board.verificationFindings.length,maturity:verified.board.maturity};
  await save('result.json',result);console.log(JSON.stringify(result));
}catch(error){await save('failure.json',{error:String(error),calls,appVersionCommitted:false});console.error(String(error));process.exitCode=1;}

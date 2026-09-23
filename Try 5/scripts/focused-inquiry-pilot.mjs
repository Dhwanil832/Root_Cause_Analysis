// One real, opt-in task on a saved diagnostic clone. No database writes, no
// storyteller, no automatic retries, no later evidence or answer-key access.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {executeTask} from '../src/engine/tasks/executor.ts';
import {applyBoardTask} from '../src/engine/board/changes.ts';
import {project} from '../src/engine/board/projection.ts';
import {findingText} from '../src/engine/records.ts';
import {QWEN_REVIEW_SAMPLING} from '../src/engine/review/inference-profile.ts';
import {ENGINE_VERSION} from '../src/engine/types.ts';

const [directory]=process.argv.slice(2);
if(!directory)throw Error('Usage: focused-inquiry-pilot.mjs COMPLETED_B1_PILOT_DIRECTORY');
const read=name=>JSON.parse(fs.readFileSync(path.join(directory,name),'utf8'));
const manifest=read('manifest.json'),input=read('input.json'),state=read('03-review-state.json');
const sourceRequest=read('04-causal-request.json');
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
if(input.model.provider!=='ollama'||!input.model.digest||!input.model.capabilities?.includes('thinking'))throw Error('Frozen thinking-capable Ollama model required.');
if(!read('summary.json').applicationRunUnchanged)throw Error('Parent diagnostic integrity not established.');
const installed=await fetch(`${process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434'}/api/tags`).then(r=>r.json());
if(!installed.models?.some(m=>m.name===input.model.id.replace(/^ollama:/,'')&&m.digest===input.model.digest))throw Error('Model digest changed.');
const before=structuredClone(state), controller=new AbortController();
process.once('SIGINT',()=>controller.abort(new Error('Explicit interruption; no retry.')));
process.once('SIGTERM',()=>controller.abort(new Error('Explicit interruption; no retry.')));
fs.mkdirSync('outputs',{recursive:true});
const output=fs.mkdtempSync(path.resolve('outputs/focused-inquiry-'));
const write=(name,value)=>fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
write('manifest.json',{createdAt:new Date().toISOString(),engine:ENGINE_VERSION,parent:path.resolve(directory),runId:manifest.runId,
  inputHash:hash(input),stateHash:hash(state),sourceSetHash:hash(state.sources),model:input.model,profile:{thinking:true,sampling:QWEN_REVIEW_SAMPLING},
  boundary:'Focused inquiry on a diagnostic clone. Same three findings and B0+P01 originals. Generic objective, no hidden answers. All output remains proposed. Not an app revision or full acceptance.'});
const task={id:'focused:'+crypto.randomUUID(),kind:'inquiry',owner:'causal-analysis',targetIds:state.findings.map(f=>f.id),
  query:state.findings.map(findingText).join('\n'),requiredSpanIds:sourceRequest.selectedEvidence,
  dependsOn:[],status:'running',attempts:1,cacheKey:'',error:'',reused:false,evidenceIds:[],omittedEvidenceIds:[],contextBytes:0,durationMs:0,inputTokens:0,outputTokens:0,createdAt:new Date().toISOString()};
state.tasks.push(task);
const stream=path.join(output,'answer.txt');fs.writeFileSync(stream,'',{flag:'wx'});
console.log(JSON.stringify({event:'started',output}));
try {
  const result=await executeTask(state,task,input.model,'diagnostic-only',{cached:async()=>null},undefined,undefined,{
    signal:controller.signal,thinking:true,sampling:QWEN_REVIEW_SAMPLING,
    trace:{request:async data=>{
      if(hash([...data.selectedEvidence].sort())!==hash([...sourceRequest.selectedEvidence].sort()))throw Error('Original evidence set changed.');
      write('request.json',data);
    },append:async text=>fs.appendFileSync(stream,text),complete:async(status,result,error)=>write('provider.json',{status,result,error})},
  });
  const proposal=applyBoardTask(state,task,result.output,result.refs);
  Object.assign(task,{status:'completed',output:result.output,evidenceIds:result.evidenceIds,omittedEvidenceIds:result.omittedEvidenceIds,
    contextBytes:result.contextBytes,durationMs:result.durationMs,inputTokens:result.inputTokens,outputTokens:result.outputTokens,cacheKey:result.cacheKey});
  const unchanged=hash(before.findings)===hash(state.findings)&&hash(before.propositions)===hash(state.propositions)
    &&hash(before.relationships)===hash(state.relationships)&&hash(before.sources)===hash(state.sources);
  write('result.json',{output:result.output,proposal,questions:state.questions.filter(q=>q.inquiryTargets?.includes(proposal.id)),
    durationMs:result.durationMs,unchangedFactsAndBoard:unchanged,applicationWrites:0,quarantine:state.quarantine,
    semanticAcceptance:'Requires source audit. API completion is not reasoning acceptance.'});
  write('state.json',state);write('snapshot.json',project(state,input,'partial'));
  if(!unchanged)throw Error('Inquiry modified facts or the board.');
  console.log(JSON.stringify({event:'completed',output,durationMs:result.durationMs,questions:proposal.questions.length,unchangedFactsAndBoard:unchanged}));
}catch(error){write('failure.json',{message:error.message,attempts:error.attempts,applicationWrites:0});throw error;}

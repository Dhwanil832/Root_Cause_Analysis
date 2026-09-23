// Opt-in diagnostic only. Uses the existing context planner and provider, with
// no database mutation or production scheduling changes.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {z} from 'zod';
import {runProviderStage} from '../src/providers/index.ts';
import {planContext,contextCapacity} from '../src/engine/context/planner.ts';
import {evidenceIndex} from '../src/knowledge/retrieval/index.ts';
import {QWEN_REVIEW_SAMPLING} from '../src/engine/review/inference-profile.ts';
import {ENGINE_VERSION} from '../src/engine/types.ts';

const [parentDirectory,observationIndex='0']=process.argv.slice(2);
if(!parentDirectory||!/^\d+$/.test(observationIndex))throw Error('Usage: next-evidence-pilot.mjs FOCUSED_PILOT_DIRECTORY [OBSERVATION_INDEX]');
const read=(directory,name)=>JSON.parse(fs.readFileSync(path.join(directory,name),'utf8'));
const parent=read(parentDirectory,'manifest.json'),prior=read(parentDirectory,'result.json');
const input=read(parent.parent,'input.json'),state=read(parent.parent,'03-review-state.json');
const observation=prior.proposal.observations[Number(observationIndex)];
if(!observation||!prior.unchangedFactsAndBoard||prior.applicationWrites!==0)throw Error('Invalid diagnostic parent or observation.');
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
if(hash(input)!==parent.inputHash||hash(state)!==parent.stateHash)throw Error('Frozen parent input/state changed.');
const model=input.model;
if(model.provider!=='ollama'||!model.digest||!model.capabilities?.includes('thinking'))throw Error('Frozen thinking-capable Ollama model required.');
const installed=await fetch(`${process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434'}/api/tags`).then(r=>r.json());
if(!installed.models?.some(m=>m.name===model.id.replace(/^ollama:/,'')&&m.digest===model.digest))throw Error('Model digest changed.');
const system=fs.readFileSync('prompts/engine/shared.md','utf8')+'\n\n'+fs.readFileSync('prompts/causal-analysis/next-evidence.md','utf8');
const text=z.string(), refs=z.array(z.string());
const generic=z.object({
  observationAssessment:z.object({established:text,notEstablished:text,references:refs}),
  nextRequest:z.object({question:text,evidenceNeeded:text,decisionToResolve:text,whyThisRequest:text,references:refs,
    outcomes:z.array(z.object({answerCondition:text,warrantedUpdate:text,doesNotEstablish:text}))}),
});
const originalRequest=read(parentDirectory,'request.json');
const base={task:'next-evidence-decision',incidentContext:{focalEvent:state.focalEvent,summary:state.summary},
  proposedObservation:{...observation,status:'proposed; not independently reviewed'},
  findings:originalRequest.packet.findings,existingQuestions:originalRequest.packet.existingQuestions};
const context=planContext({model,system,schema:generic,base,index:evidenceIndex('next-evidence-diagnostic',state.sources),
  query:observation.statement,required:originalRequest.selectedEvidence});
if(hash([...context.selected.map(s=>s.id)].sort())!==hash([...originalRequest.selectedEvidence].sort()))throw Error('Original evidence set changed.');
const citations=z.array(z.enum([...context.references.keys()]));
const schema=generic.extend({observationAssessment:generic.shape.observationAssessment.extend({references:citations}),
  nextRequest:generic.shape.nextRequest.extend({references:citations})});
const delta=Math.max(0,JSON.stringify(z.toJSONSchema(schema)).length-JSON.stringify(z.toJSONSchema(generic)).length);
const outputTokens=context.outputTokens-Math.ceil(delta/2);
if(outputTokens<1)throw Error('Request exceeds context; do not truncate.');
const controller=new AbortController();
for(const signal of ['SIGINT','SIGTERM'])process.once(signal,()=>controller.abort(new Error('Explicit interruption; no retry.')));
const output=fs.mkdtempSync(path.resolve('outputs/next-evidence-'));
const write=(name,value)=>fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const request={stage:'causal-analysis',model,systemPrompt:system,schema,schemaName:'try5_next_evidence_diagnostic',evidencePacket:context.packet,
  contextWindow:contextCapacity(model),outputTokens,thinking:true,sampling:QWEN_REVIEW_SAMPLING,noTruncation:true,maxAttempts:1};
write('manifest.json',{createdAt:new Date().toISOString(),engine:ENGINE_VERSION,parent:path.resolve(parentDirectory),observationIndex:Number(observationIndex),
  model,sourceSetHash:hash(state.sources),parentStateHash:hash(state),expectationsHash:hash(fs.readFileSync('evals/try5/next-evidence-expectations.md','utf8')),
  boundary:'One question-selection diagnostic, not a production revision. No database access, storyteller, later evidence, answer key, fallback or retry. Expectations are not in the model packet.'});
write('request.json',{...request,schema:z.toJSONSchema(schema),selectedEvidence:context.selected.map(s=>s.id),omittedEvidence:context.omitted});
const stream=path.join(output,'answer.txt');fs.writeFileSync(stream,'',{flag:'wx'});
console.log(JSON.stringify({event:'started',output,model:model.id,evidencePassages:context.selected.length}));
try{
  const result=await runProviderStage({...request,signal:controller.signal,onChunk:async text=>fs.appendFileSync(stream,text)});
  write('provider.json',result);
  const parsed=schema.parse(result.output);
  write('result.json',{output:parsed,durationMs:result.durationMs,usage:result.usage,
    referenceBindings:[...context.references],applicationWrites:0,semanticAcceptance:'Pending source audit against frozen criteria; schema success is not semantic acceptance.'});
  console.log(JSON.stringify({event:'completed',output,durationMs:result.durationMs}));
}catch(error){write('failure.json',{message:error.message,attempts:error.attempts,applicationWrites:0});throw error;}

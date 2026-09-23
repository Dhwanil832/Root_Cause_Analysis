import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {z} from 'zod';
import {runProviderStage} from '../src/providers/index.ts';

const [parentDirectory]=process.argv.slice(2);
if(!parentDirectory)throw Error('Usage: next-evidence-history-ablation.mjs NEXT_EVIDENCE_DIRECTORY');
const baseline=JSON.parse(fs.readFileSync(path.join(parentDirectory,'request.json'),'utf8'));
if(baseline.schemaName!=='try5_next_evidence_diagnostic'||!Array.isArray(baseline.evidencePacket.existingQuestions))throw Error('Expected saved next-evidence request with question history.');
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const request=structuredClone(baseline);
delete request.evidencePacket.existingQuestions;
const restored=structuredClone(request);restored.evidencePacket.existingQuestions=baseline.evidencePacket.existingQuestions;
if(!isDeepStrictEqual(restored,baseline))throw Error('Unexpected second request change.');
const schema=z.fromJSONSchema(request.schema);
if(!isDeepStrictEqual(z.toJSONSchema(schema,{target:'draft-7'}),{...request.schema,$schema:'http://json-schema.org/draft-07/schema#'}))throw Error('Wire schema differs from the saved request.');
const installed=await fetch(`${process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434'}/api/tags`).then(r=>r.json());
if(!installed.models?.some(m=>m.name===request.model.id.replace(/^ollama:/,'')&&m.digest===request.model.digest))throw Error('Model digest changed.');
const output=fs.mkdtempSync(path.resolve('outputs/next-evidence-no-history-'));
const write=(name,value)=>fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
write('manifest.json',{createdAt:new Date().toISOString(),parent:path.resolve(parentDirectory),parentRequestHash:hash(baseline),
  removedField:'evidencePacket.existingQuestions',removedQuestions:baseline.evidencePacket.existingQuestions.length,
  onlySpecifiedFieldChanged:true,wireSchemaEquivalent:true,
  expectationHash:hash(fs.readFileSync('evals/try5/next-evidence-history-ablation.md','utf8')),
  boundary:'One explicit context-ablation condition, not an automatic retry or production run. No database writes or other input changes.'});
write('request.json',request);
const stream=path.join(output,'answer.txt');fs.writeFileSync(stream,'',{flag:'wx'});
const controller=new AbortController();
for(const signal of ['SIGINT','SIGTERM'])process.once(signal,()=>controller.abort(new Error('Explicit interruption; no retry.')));
console.log(JSON.stringify({event:'started',output,removedQuestions:baseline.evidencePacket.existingQuestions.length}));
try{
  const result=await runProviderStage({...request,schema,maxAttempts:1,signal:controller.signal,onChunk:async text=>fs.appendFileSync(stream,text)});
  write('provider.json',result);
  write('result.json',{output:schema.parse(result.output),durationMs:result.durationMs,usage:result.usage,applicationWrites:0,semanticAcceptance:'Pending source audit against unchanged criteria.'});
  console.log(JSON.stringify({event:'completed',output,durationMs:result.durationMs}));
}catch(error){write('failure.json',{message:error.message,attempts:error.attempts,applicationWrites:0});throw error;}

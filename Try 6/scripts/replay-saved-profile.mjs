// Replay an immutable request, changing ONLY the explicit inference profile.
// No app DB access, previous answer in context, retry, or model substitution.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {z} from 'zod';
import {evidenceMessage,parseModelJson} from '../src/providers/json.ts';
import {StreamRepetitionGuard} from '../src/providers/stream-repetition.ts';
import {QWEN_REVIEW_SAMPLING} from '../src/engine/review/inference-profile.ts';

const source=process.argv[2];
if(!source)throw Error('Usage: replay-saved-profile.mjs SAVED_REQUEST_JSON');
const saved=JSON.parse(fs.readFileSync(source,'utf8'));
if(!['causal','verify'].includes(saved.kind)||!/^ollama:qwen3\.5(?::|$)/.test(saved.model.id)||!saved.model.digest)
  throw Error('Expected a frozen Qwen causal/verification request.');
const base=process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434',name=saved.model.id.slice(7);
const tags=await fetch(base+'/api/tags').then(r=>{if(!r.ok)throw Error('Ollama unavailable');return r.json();});
if(!tags.models?.some(m=>m.name===name&&m.digest===saved.model.digest))throw Error('Model digest mismatch.');
const schema=z.fromJSONSchema(saved.schema),format={...saved.schema,$schema:'http://json-schema.org/draft-07/schema#'};
// Production serializes Zod's draft-7 form on the wire; this preserves the saved
// contract, field ordering and descriptions rather than loading updated prompts.
const body={model:name,stream:true,think:true,truncate:false,shift:false,format,
  options:{...QWEN_REVIEW_SAMPLING,num_ctx:saved.context,num_predict:saved.outputTokens},
  messages:[{role:'system',content:saved.system},{role:'user',content:`${evidenceMessage(saved.packet)}\n\nRESPONSE CONTRACT (application instructions, not evidence):\n${JSON.stringify(format)}`}]};
fs.mkdirSync('outputs',{recursive:true});
const output=fs.mkdtempSync(path.resolve('outputs/profile-replay-'));
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const write=(file,value)=>fs.writeFileSync(path.join(output,file),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
write('request.json',{source:path.resolve(source),sourceHash:hash(saved),body,model:saved.model,
  unchanged:{system:hash(saved.system),packet:hash(saved.packet),schema:hash(saved.schema),context:saved.context,outputTokens:saved.outputTokens},
  change:'Thinking plus the documented general-task sampling profile. A profile comparison, not an isolated thinking-toggle ablation.'});
const controller=new AbortController(),guard=new StreamRepetitionGuard();
for(const signal of ['SIGINT','SIGTERM'])process.once(signal,()=>controller.abort(new Error('Replay cancelled.')));
let timer;const touch=()=>{clearTimeout(timer);timer=setTimeout(()=>controller.abort(new Error('No stream activity for 180 seconds')),180000);};
let raw='',buffer='',thinkingCharacters=0,done;const start=Date.now();
fs.writeFileSync(path.join(output,'answer.txt'),'',{flag:'wx'});
console.log(JSON.stringify({event:'started',output,kind:saved.kind}));
touch();
try {
  const response=await fetch(base+'/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body),signal:controller.signal});
  if(!response.ok||!response.body)throw Error(`Ollama HTTP ${response.status}`);
  const reader=response.body.getReader(),decoder=new TextDecoder();
  const consume=line=>{if(!line.trim())return;const c=JSON.parse(line);if(c.error)throw Error(c.error);
    thinkingCharacters+=(c.message?.thinking||'').length;
    const text=c.message?.content||'';raw+=text;fs.appendFileSync(path.join(output,'answer.txt'),text);guard.push(text);
    if(c.done)done={reason:c.done_reason,inputTokens:c.prompt_eval_count,outputTokens:c.eval_count};};
  try {for(;;){const c=await reader.read();if(c.done)break;touch();buffer+=decoder.decode(c.value,{stream:true});
    let n;while((n=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,n));buffer=buffer.slice(n+1);}}
    buffer+=decoder.decode();if(buffer.trim())consume(buffer);
  }finally{await reader.cancel().catch(()=>{});}
  if(!done)throw Error('Stream ended without completion');if(done.reason==='length')throw Error('Output capacity exhausted');
  const result=schema.parse(parseModelJson(raw));
  write('result.json',{output:result,done,durationMs:Date.now()-start,thinkingCharacters,attempts:1,applicationWrites:0,semanticAcceptance:'Requires source audit'});
  console.log(JSON.stringify({event:'completed',output,durationMs:Date.now()-start}));
}catch(error){controller.abort(error);write('failure.json',{message:error.message,durationMs:Date.now()-start,thinkingCharacters,attempts:1});throw error;}
finally{clearTimeout(timer);}

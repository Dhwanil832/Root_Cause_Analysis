import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {localHttpOnce} from './local_http_once.mjs';
const dir=path.resolve(process.argv[2] || '');
const manifest=JSON.parse(await fs.readFile(path.join(dir,'manifest.json')));
if(manifest.batch!=='B0'||manifest.targetVersion!==1) throw Error('B0-only capture proxy');
const capture=path.join(dir,'model-capture');
await fs.mkdir(capture,{recursive:false});
let number=0;
const log=async value=>fs.appendFile(path.join(dir,'capture-events.jsonl'),JSON.stringify({...value,at:new Date().toISOString()})+'\n');
const server=http.createServer(async(req,res)=>{
  let id;
  try{
    if(req.url==='/health'){res.end(JSON.stringify({ok:true,captured:number}));return;}
    if(req.method==='GET'&&req.url==='/api/tags'){
      const upstream=await fetch('http://127.0.0.1:11434/api/tags');
      res.writeHead(upstream.status,{'content-type':'application/json'});res.end(await upstream.text());
      await log({event:'model-list'});return;
    }
    if(req.method!=='POST'||req.url!=='/api/chat')throw Error('Capture proxy only permits tags and chat');
    const chunks=[];for await(const chunk of req)chunks.push(chunk);
    const raw=Buffer.concat(chunks),body=JSON.parse(raw);
    if(body.model!=='qwen3.5:latest'||body.stream!==false)throw Error('Unexpected model or streaming mode');
    if(body.think!==false||body.options?.temperature!==0||body.options?.num_ctx!==32768)throw Error('Generation settings differ from manifest');
    if(body.messages.some(m=>/V-201|V-202|CH-218|IA-P0[1-9]|IA-C0[12]|BEGIN PRIVATE|evaluator-frozen/.test(m.content||'')))throw Error('B0 leakage tripwire');
    id=String(++number).padStart(4,'0');
    await fs.writeFile(path.join(capture,`${id}-request.json`),raw,{flag:'wx'});
    await log({event:'request',id,systemSha256:createHash('sha256').update(body.messages[0]?.content||'').digest('hex'),maxOutputTokens:body.options.num_predict});
    const started=Date.now();
    const response=await localHttpOnce('http://127.0.0.1:11434/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:raw,timeoutMs:9*60*1000});
    const out=response.body;
    await fs.writeFile(path.join(capture,`${id}-response.json`),out,{flag:'wx'});
    res.writeHead(response.status,{'content-type':'application/json'});res.end(out);
    let summary={};try{const p=JSON.parse(out);summary={doneReason:p.done_reason,inputTokens:p.prompt_eval_count,outputTokens:p.eval_count};}catch{}
    await log({event:'response',id,status:response.status,durationMs:Date.now()-started,...summary});
  }catch(error){await log({event:'error',id,error:String(error)});if(!res.headersSent)res.writeHead(502,{'content-type':'application/json'});res.end(JSON.stringify({error:String(error)}));}
});
server.listen(11435,'127.0.0.1',()=>console.log(JSON.stringify({capture,port:11435})));

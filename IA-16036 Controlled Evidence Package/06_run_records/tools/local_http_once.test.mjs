import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {localHttpOnce} from './local_http_once.mjs';

async function serverFor(handler){
  const server=http.createServer(handler);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  return {url:`http://127.0.0.1:${server.address().port}`,close:()=>new Promise(resolve=>{server.close(resolve);server.closeAllConnections();})};
}
test('waits for delayed headers, sends exact bytes and performs one POST',async()=>{
  let calls=0,received='';
  const server=await serverFor(async(req,res)=>{calls++;for await(const data of req)received+=data;setTimeout(()=>res.end('{"ok":true}'),150);});
  try{const result=await localHttpOnce(server.url,{method:'POST',body:'unchanged payload',timeoutMs:2000});assert.equal(result.status,200);assert.equal(result.body,'{"ok":true}');assert.equal(received,'unchanged payload');assert.equal(calls,1);}finally{await server.close();}
});
test('explicit timeout rejects without retrying',async()=>{
  let calls=0;
  const server=await serverFor(()=>{calls++;});
  try{await assert.rejects(localHttpOnce(server.url,{timeoutMs:100}),/Explicit local HTTP deadline/);assert.equal(calls,1);}finally{await server.close();}
});
test('HTTP failure is returned intact, not retried',async()=>{
  let calls=0;
  const server=await serverFor((req,res)=>{calls++;res.writeHead(503);res.end('{"error":"unavailable"}');});
  try{const result=await localHttpOnce(server.url);assert.equal(result.status,503);assert.equal(result.body,'{"error":"unavailable"}');assert.equal(calls,1);}finally{await server.close();}
});
test('remote targets rejected before connection',()=>{
  assert.throws(()=>localHttpOnce('https://example.com'),/Local HTTP only/);
});
test('survives the former five-minute headers cutoff with exactly one POST', {skip:process.env.RCA_LONG_TRANSPORT_TEST!=='1'}, async()=>{
  let calls=0;
  const server=await serverFor((req,res)=>{calls++;req.resume();setTimeout(()=>res.end('{"completed":true}'),310000);});
  const started=Date.now();
  try{
    const result=await localHttpOnce(server.url,{method:'POST',timeoutMs:330000});
    assert.equal(result.status,200);
    assert.equal(result.body,'{"completed":true}');
    assert.equal(calls,1);
    assert.ok(Date.now()-started>=310000);
  }finally{await server.close();}
});

import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';

async function exercise(failGeneration=false,failInitialization=false){
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'rca-runner-contract-'));
  const versions=[],rounds=[];let initialized=false,scenario,applyCount=0,generateCount=0,initializeCount=0;
  const fixedWorld={title:'Test scenario',hiddenTruth:'Private test fact must not be uploaded as an RCA answer',sources:[{id:'s',available:true,text:'A fixed observation.'}]};
  function addVersion(){const number=versions.length+1;versions.push({id:`v${number}`,number,trigger:number===1?'Initial input':'Story batch',createdAt:'fixed',analysis:{stageErrors:[],trace:[{stage:'causal-analysis',engine:'ollama:qwen3.5:latest',validation:'valid'},{stage:'causal-verification',engine:'ollama:qwen3.5:latest',validation:'valid'}],causalBoard:{nodes:[{id:'f'}],focalNodeId:'f'}}});}
  const server=http.createServer(async(req,res)=>{
    let raw='';for await(const chunk of req)raw+=chunk;
    const body=req.headers['content-type']?.includes('application/json')?JSON.parse(raw):{};
    const send=(data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
    if(req.url==='/api/tags')return send({models:[{name:'qwen3.5:latest',digest:'mock-only'}]});
    if(req.url==='/api/references')return send({documents:[]});
    if(req.url==='/api/incidents'&&req.method==='GET')return send({incidents:[]});
    if(req.url==='/api/incidents'&&req.method==='POST'){
      assert.match(raw,/deferAnalysis/);assert.match(raw,/qwen3.5:latest/);return send({id:'incident'});
    }
    if(req.url==='/api/incidents/incident')return send({incident:{tracks:[{id:'track',modelId:'ollama:qwen3.5:latest',versions}]}});
    if(req.url==='/api/tracks/track/initialize'){initializeCount++;if(failInitialization)return send({error:'Stage-local repairs exhausted'},400);if(!initialized){addVersion();initialized=true;}return send({version:1});}
    if(req.url==='/api/story-template')return send(fixedWorld);
    if(req.url==='/api/tracks/track/story'){
      if(req.method==='GET')return send({questions:[{id:'q'+versions.length,text:'What does the record establish?'}],scenario:{definition:scenario},rounds});
      if(body.action==='create'){scenario={...body.scenario,sources:body.scenario.sources.map(s=>({text:s.text,available:s.available,id:s.id}))};return send({id:'scenario'});}
      if(body.action==='generate'){
        generateCount++;
        if(failGeneration){rounds.splice(0,rounds.length,{id:'failed',base_version:1,status:'failed'});return send({error:'Unsupported evidence reference'},400);}
        const round={id:'round'+versions.length,status:'ready',base_version:versions.length,output:{output:{answers:[{questionId:'q'+versions.length,status:'unknown',answer:'Not established.',citations:[]}]}}};
        rounds.push(round);return send({id:round.id});
      }
      if(body.action==='apply'){
        assert.equal(body.strictCausal,true);assert.ok(versions.length<4);applyCount++;
        const round=rounds.find(r=>r.id===body.roundId);round.status='applied';addVersion();round.result_version=versions.length;return send({version:versions.length});
      }
    }
    return send({error:'Unexpected route '+req.url},404);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  try{
    const child=spawn(process.execPath,['--experimental-strip-types','scripts/autonomous-qwen-story.mjs','--run-dir',dir,'--base-url',base,'--ollama-url',base]);
    let output='';child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>output+=data);
    const code=await new Promise((resolve,reject)=>{child.on('close',resolve);child.on('error',reject);});
    const state=JSON.parse(await fs.readFile(path.join(dir,'state.json'),'utf8'));
    return {code,state,applyCount,generateCount,initializeCount,versions,output,dir};
  }finally{await new Promise(resolve=>server.close(resolve));}
}
test('unattended orchestration commits exactly four versions and three story batches',async()=>{
  const result=await exercise();assert.equal(result.code,0,result.output);assert.equal(result.state.status,'complete');
  assert.equal(result.versions.length,4);assert.equal(result.applyCount,3);assert.equal(result.generateCount,3);
  assert.equal(JSON.parse(await fs.readFile(path.join(result.dir,'result.json'),'utf8')).analysisPending,true);
});
test('invalid story evidence never advances the causal version or triggers invented answers',async()=>{
  const result=await exercise(true);assert.equal(result.code,1,result.output);assert.equal(result.state.status,'failed');
  assert.equal(result.applyCount,0);assert.equal(result.versions.length,1);assert.equal(result.generateCount,2);
});
test('exhausted initial stage recovery does not replay the entire RCA request',async()=>{
  const result=await exercise(false,true);
  assert.equal(result.code,1);assert.equal(result.state.committedVersions,0);
  assert.equal(result.initializeCount,1);assert.equal(result.generateCount,0);assert.equal(result.applyCount,0);
});

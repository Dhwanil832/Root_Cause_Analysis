import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const dir=path.resolve(process.argv[2] || '');
const read=name=>JSON.parse(fs.readFileSync(path.join(dir,name)));
const manifest=read('manifest.json');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const events=fs.readFileSync(path.join(dir,'capture-events.jsonl'),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const requests=events.filter(e=>e.event==='request');
const responses=events.filter(e=>e.event==='response');
const changedCode=Object.entries(manifest.codeHashes).filter(([name,hash])=>sha(fs.readFileSync(path.join(manifest.appDirectory,name)))!==hash).map(([name])=>name);
const changedInputs=manifest.inputs.filter(item=>sha(fs.readFileSync(path.join(dir,item.path)))!==item.sha256).map(item=>item.id);
const result=fs.existsSync(path.join(dir,'result.json'))?read('result.json'):null;
const failure=fs.existsSync(path.join(dir,'failure.json'))?read('failure.json'):null;
const stats={run:path.basename(dir),promptVersion:manifest.promptVersion,result,failure,
  requests:requests.length,responses:responses.length,proxyErrors:events.filter(e=>e.event==='error'),
  lengthLimitedResponses:responses.filter(e=>e.doneReason==='length').map(e=>e.id),
  firstRequest:requests[0]?.at,lastResponse:responses.at(-1)?.at,
  modelInputTokens:responses.reduce((sum,e)=>sum+(e.inputTokens||0),0),
  modelOutputTokens:responses.reduce((sum,e)=>sum+(e.outputTokens||0),0),
  inferenceSeconds:responses.reduce((sum,e)=>sum+(e.durationMs||0),0)/1000,
  frozenCodeFiles:Object.keys(manifest.codeHashes).length,changedCode,changedInputs};
if(process.argv.includes('--save')) {
  if(!result&&!failure)throw Error('Do not freeze a report while the run is in progress');
  fs.writeFileSync(path.join(dir,'capture-summary.json'),JSON.stringify(stats,null,2),{flag:'wx'});
}
console.log(JSON.stringify(stats,null,2));

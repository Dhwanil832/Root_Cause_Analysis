// Read-only status; no model requests, restarts or database writes.
import fs from 'node:fs/promises';
import path from 'node:path';
const dir=path.resolve(process.argv[2] || 'IA-16036 Controlled Evidence Package/06_run_records/qwen-v2-consolidated-btG98n');
const read=async name=>{try{return JSON.parse(await fs.readFile(path.join(dir,name),'utf8'));}catch(error){if(error.code==='ENOENT')return null;throw error;}};
const manifest=await read('manifest.json');
if(!manifest)throw Error('No restart manifest at supplied directory');
const names=await fs.readdir(path.join(dir,'phases'));
const latest=prefix=>names.filter(n=>new RegExp(`^${prefix}-\\d+\\.json$`).test(n)).sort((a,b)=>Number(b.match(/(\d+)\.json$/)[1])-Number(a.match(/(\d+)\.json$/)[1]))[0];
const discovery=await read('phases/discovery.json');
const consolidation=await read(`phases/${latest('consolidation')||'consolidation-complete.json'}`);
const board=await read('phases/linked-board.json');
const review=latest('verification')?await read(`phases/${latest('verification')}`):null;
const result=await read('result.json'),failure=await read('failure.json');
const files=await fs.readdir(path.join(dir,'model-capture'));
const metrics=await Promise.all(files.filter(n=>n.endsWith('-metadata.json')).map(n=>read(`model-capture/${n}`)));
const counts=rows=>rows.reduce((out,row)=>({...out,[row]:1+(out[row]||0)}),{});
console.log(JSON.stringify({directory:dir,status:result?'completed':failure?'failed':'in-progress-or-paused (see process state)',
  model:manifest.model,appVersionCommitted:manifest.appVersionCommitted,
  preservedDiscovery:discovery&&{calls:discovery.calls,reused:discovery.reused,candidates:discovery.candidates.length},
  consolidation:consolidation&&{processed:consolidation.ledger.length,total:discovery?.candidates.length,nodes:consolidation.catalog.length,
    dispositions:counts(consolidation.ledger.map(r=>r.disposition))},
  linkedBoard:board&&{nodes:board.board.nodes.length,edges:board.board.edges.length,rejected:board.board.rejectedEdges?.length},
  verification:review&&{targets:Object.keys(review.reviews).length,verdicts:counts(Object.values(review.reviews).map(r=>r.verdict))},
  transport:{requests:files.filter(n=>n.endsWith('-request.json')).length,responses:metrics.length,
    inputTokens:metrics.map(m=>m.inputTokens),outputTokens:metrics.map(m=>m.outputTokens),
    responseStatuses:counts(metrics.map(m=>m.status)),lengthStops:metrics.filter(m=>m.doneReason==='length').length},
  result,failure},null,2));

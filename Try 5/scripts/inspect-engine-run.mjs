import fs from 'node:fs';
import path from 'node:path';
import {DatabaseSync} from 'node:sqlite';

const runId=process.argv[2];if(!runId)throw Error('Usage: node scripts/inspect-engine-run.mjs RUN_ID [--findings] [--calls]');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const files=fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite'));
const candidates=files.filter(file=>{
  const candidate=new DatabaseSync(path.join(folder,file),{readOnly:true});
  try{return !!candidate.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='engine_runs'").get()
    && !!candidate.prepare('SELECT id FROM engine_runs WHERE id=?').get(runId);}finally{candidate.close();}
});
if(candidates.length!==1)throw Error('Could not uniquely locate this run in local D1.');
const db=new DatabaseSync(path.join(folder,candidates[0]),{readOnly:true});
function json(encoded){const value=JSON.parse(encoded);return value?.$artifact?JSON.parse(db.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').all(value.$artifact).map(r=>r.content).join('')):value;}
const row=db.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);if(!row)throw Error('Run not found.');
const manifest=row.state_json?json(row.state_json):null;
const state=manifest?.$engineState?Object.fromEntries(Object.entries(manifest.fields).map(([k,v])=>[k,json(v)])):manifest;
const input=json(row.input_json);
const counts={};for(const t of state?.tasks||[])counts[`${t.kind}:${t.status}`]=(counts[`${t.kind}:${t.status}`]||0)+1;
const calls=db.prepare('SELECT id,task_id,status,error,request_json,result_json,updated_at FROM engine_calls WHERE run_id=? ORDER BY created_at').all(runId);
console.log(JSON.stringify({runId,trackId:row.track_id,version:row.number,status:row.status,pauseReason:row.pause_reason,generation:row.generation,phase:state?.phase,
  model:input.model.id,engine:state?.executionMigrations?.at(-1)?.to||input.engineVersion,originalInputEngine:input.engineVersion,
  executionMigrations:state?.executionMigrations,reviewAfterReading:state?.reviewAfterReading??input.reviewAfterReading,counts,
  findings:state?.findings.length,questions:state?.questions.length,nodes:state?.propositions.length,edges:state?.relationships.length,
  quarantine:state?.quarantine,maxDependencies:Math.max(0,...(state?.tasks||[]).map(t=>t.dependsOn.length)),
  checkpointRowBytes:Buffer.byteLength(row.input_json+(row.state_json||'')+row.snapshot_json),
  calls:calls.map(c=>{const request=c.request_json?json(c.request_json):null;
    const stream=db.prepare('SELECT SUM(length(content)) AS chars,MAX(ordinal)+1 AS chunks FROM engine_artifact_chunks WHERE artifact_id=?').get(`stream:${c.id}`);
    return {id:c.id,status:c.status,error:c.error,kind:request?.kind,outputAllowance:request?.outputTokens,stream,updatedAt:c.updated_at,
      ...(process.argv.includes('--calls')?{result:c.result_json?json(c.result_json):null}:{} )};}),
  ...(process.argv.includes('--findings')?{notebook:state?.findings.map(f=>({id:f.id,kind:f.kind,statement:f.statement,status:f.status,role:f.causalRole,
    review:f.reviewReason,sources:f.spanIds.map(id=>state.sources.find(s=>s.spans.some(p=>p.id===id))?.label)}))}:{})},null,2));
db.close();

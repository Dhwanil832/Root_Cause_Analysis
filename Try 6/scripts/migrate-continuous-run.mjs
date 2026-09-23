// Explicit operator action. No model calls; backs up the selected execution before
// its state-compatible migration, and never resumes another track.
import fs from 'node:fs';
import path from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {digest} from '../src/engine/identity.ts';
import {readJSON,readState} from '../src/engine/tasks/artifacts.ts';
import './legacy-disabled.mjs';
import {migrateContinuousExecution} from '../src/server/engine-migration.ts';

const runId=process.argv[2];
if(!runId)throw Error('Usage: node --import ./scripts/register-test-loader.mjs scripts/migrate-continuous-run.mjs RUN_ID');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const candidates=fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite')).filter(n=>{
  const r=new DatabaseSync(path.join(folder,n),{readOnly:true});
  try{return !!r.prepare("SELECT name FROM sqlite_master WHERE name='engine_runs'").get()&&!!r.prepare('SELECT id FROM engine_runs WHERE id=?').get(runId);}finally{r.close();}
});
if(candidates.length!==1)throw Error('Run must resolve to exactly one local database.');
const sqlite=new DatabaseSync(path.join(folder,candidates[0]));
sqlite.exec('PRAGMA busy_timeout=10000');
const db={prepare(sql){let bindings=[];return {
  bind(...v){bindings=v;return this;},
  async first(){return sqlite.prepare(sql).get(...bindings)||null;},
  async all(){return {results:sqlite.prepare(sql).all(...bindings),success:true,meta:{}};},
  async run(){const r=sqlite.prepare(sql).run(...bindings);return {success:true,meta:{changes:Number(r.changes)}};},
};},async batch(statements){sqlite.exec('BEGIN IMMEDIATE');try{const results=[];for(const s of statements)results.push(await s.run());sqlite.exec('COMMIT');return results;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
try {
  const row=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(runId).first();
  if(row.status!=='paused')throw Error('Only a paused run may be migrated.');
  const beforeRows=sqlite.prepare('SELECT id,input_json,state_json,snapshot_json,status,generation FROM engine_runs ORDER BY id').all();
  const input=await readJSON(db,row.input_json),state=await readState(db,row.state_json);
  const calls=(await db.prepare('SELECT * FROM engine_calls WHERE run_id=? ORDER BY created_at,rowid').bind(runId).all()).results;
  const traces=[];
  for(const call of calls)traces.push({...call,
    request:call.request_json?await readJSON(db,call.request_json):null,
    result:call.result_json?await readJSON(db,call.result_json):null,
    raw:sqlite.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').all(`stream:${call.id}`).map(r=>r.content).join('')});
  const checkpointHash=await digest([row.input_json,row.state_json,row.snapshot_json]);
  const output=fs.mkdtempSync(path.resolve('outputs/continuous-recovery-'));
  fs.writeFileSync(path.join(output,'before.json'),JSON.stringify({row,input,state,snapshot:await readJSON(db,row.snapshot_json),traces},null,2),{flag:'wx'});
  fs.writeFileSync(path.join(output,'backup-manifest.json'),JSON.stringify({runId,generation:row.generation,checkpointHash,
    backupSha256:await digest(fs.readFileSync(path.join(output,'before.json'),'utf8')),createdAt:new Date().toISOString()},null,2),{flag:'wx'});
  const receipt=await migrateContinuousExecution(db,runId,row.generation,checkpointHash,
    'User requested removal of artificial stopping limits and faster V1 results. Repetition is telemetry; no default idle/output/text/follow-up cap; response failures are task-local. Prioritize original-source findings through review, mapping and verification for a provisional board without discarding remaining work.');
  const after=sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);
  if(after.input_json!==row.input_json)throw Error('Immutable input changed unexpectedly.');
  const otherAfter=sqlite.prepare('SELECT id,input_json,state_json,snapshot_json,status,generation FROM engine_runs WHERE id<>? ORDER BY id').all(runId);
  if(JSON.stringify(otherAfter)!==JSON.stringify(beforeRows.filter(r=>r.id!==runId)))throw Error('Another run changed during migration.');
  fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify({...receipt,output,immutableInputUnchanged:true,otherRunsUnchanged:true},null,2),{flag:'wx'});
  console.log(JSON.stringify({...receipt,output,immutableInputUnchanged:true,otherRunsUnchanged:true},null,2));
} finally {sqlite.close();}

import type {EngineInput} from '@/src/engine/types';
import type {RunRow} from '@/src/engine/tasks/d1-store';
import {readJSON,readState} from '@/src/engine/tasks/artifacts';
import {validateReleasedInput} from './admission';

export function redactSecrets(value:unknown):unknown {
  if(Array.isArray(value))return value.map(redactSecrets);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,v])=>[key,
    /^(apiKey|api_key|authorization|token|secret|password|providerVaultKey)$/i.test(key)?'[REDACTED]':redactSecrets(v)]));
  return value;
}
/** Export only the explicit investigator tables, never private simulator tables. */
export async function exportExperiment(db:D1Database,trackId:string) {
  const rows=await db.prepare('SELECT * FROM engine_runs WHERE track_id=? ORDER BY number').bind(trackId).all<RunRow>();
  if(!rows.results.length)throw Error('No investigator runs for this model track.');
  const versions=[];
  for(const row of rows.results) {
    const input=await readJSON<EngineInput>(db,row.input_json);validateReleasedInput(input);
    const calls=await db.prepare('SELECT * FROM engine_calls WHERE run_id=? ORDER BY created_at,id').bind(row.id)
      .all<{id:string;request_json:string|null;result_json:string|null;[key:string]:unknown}>();
    const trace=[];
    for(const call of calls.results) {
      const chunks=await db.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').bind(`stream:${call.id}`).all<{content:string}>();
      const {request_json,result_json,...meta}=call;
      trace.push({...meta,request:request_json?await readJSON(db,request_json):null,result:result_json?await readJSON(db,result_json):null,
        rawOutput:chunks.results.map(c=>c.content).join('')});
    }
    const events=await db.prepare('SELECT * FROM engine_task_events WHERE run_id=? ORDER BY created_at,id').bind(row.id).all<{payload_json:string;[key:string]:unknown}>();
    versions.push({id:row.id,number:row.number,parentVersion:row.parent_number,status:row.status,trigger:row.trigger,
      createdAt:row.created_at,updatedAt:row.updated_at,input,state:await readState(db,row.state_json),
      snapshot:await readJSON(db,row.snapshot_json),calls:trace,
      events:await Promise.all(events.results.map(async({payload_json,...meta})=>({...meta,payload:await readJSON(db,payload_json)})))});
  }
  return redactSecrets({format:'rca-investigator-export-v1',trackId,exportedAt:new Date().toISOString(),
    evaluation:'Unscored. Internal reviews and scripted tests are not an external RCA quality judgment.',
    originalFiles:'Document text, hashes and original-file identifiers are included. Binary originals are not embedded in this JSON export.',versions});
}

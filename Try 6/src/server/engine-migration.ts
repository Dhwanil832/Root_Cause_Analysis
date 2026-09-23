import { ENGINE_VERSION, type EngineInput } from '@/src/engine/types';
import type { RunRow } from '@/src/engine/tasks/d1-store';
import { readJSON,readState,putJSON,putState } from '@/src/engine/tasks/artifacts';
import { checkpointVersion } from '@/src/engine/tasks/checkpoint-version';
import { digest } from '@/src/engine/identity';
import { project } from '@/src/engine/board/projection';

/** Explicit operator-only recovery of an unpublished, paused compatible run.
 * Input, record IDs, completed outputs and traces are never rewritten. */
export async function migrateContinuousExecution(db:D1Database,runId:string,expectedGeneration:number,checkpointHash:string,reason:string) {
  if (ENGINE_VERSION.startsWith('try6.')) throw Error('Try 6 requires a fresh model track. Import original evidence only; Try 5 checkpoints cannot be migrated into the new investigation engine.');
  const row=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(runId).first<RunRow>();
  if(!row || row.status!=='paused' || row.generation!==expectedGeneration)
    throw Error('Migration requires the exact paused checkpoint inspected by the operator.');
  if(await db.prepare('SELECT id FROM versions WHERE id=? OR (track_id=? AND number=?)').bind(runId,row.track_id,row.number).first())
    throw Error('Published versions are immutable; refusing migration.');
  if(checkpointHash!==await digest([row.input_json,row.state_json,row.snapshot_json]) || !reason.trim())
    throw Error('Checkpoint backup hash/reason missing or changed.');
  const input=await readJSON<EngineInput>(db,row.input_json),state=await readState(db,row.state_json);
  if(!state || checkpointVersion(input,state)!=='try5.2.2' || String(ENGINE_VERSION)!=='try5.2.3')
    throw Error('Only the reviewed try5.2.2 → try5.2.3 state-compatible migration is supported.');
  if(state.tasks.some(t=>t.status==='running'))throw Error('Wait for in-flight inference to release before migration.');
  // Preserve the executor identity of old work, including failed call attempts.
  for(const task of state.tasks)if(task.attempts&&!task.engineVersion)task.engineVersion='try5.2.2';
  state.executionMigrations=[...(state.executionMigrations||[]),{from:'try5.2.2',to:ENGINE_VERSION,
    at:new Date().toISOString(),reason,checkpointHash}];
  state.reviewAfterReading=false;state.readingApproved=true;state.progressiveBoard=true;delete state.pauseAfterTaskId;state.pauseReason='';
  state.changes.push({targetId:runId,kind:'rechecked',reason:`Execution migrated to ${ENGINE_VERSION}: ${reason} Original input/checkpoint and completed outputs retained. No new evidence revision.`});
  const snapshot=await putJSON(db,project(state,input,'queued'));
  const changed=await db.prepare(`UPDATE engine_runs SET state_json=?,snapshot_json=?,status='queued',pause_reason='',
    lease=NULL,lease_until=0,generation=generation+1,updated_at=? WHERE id=? AND status='paused' AND generation=?`)
    .bind(await putState(db,state),snapshot,new Date().toISOString(),runId,expectedGeneration).run();
  if(!changed.meta.changes)throw Error('Checkpoint changed during migration; no dispatch was authorized.');
  return {runId,version:row.number,engineVersion:ENGINE_VERSION,queued:true,checkpointHash,
    completedRetained:state.tasks.filter(t=>t.status==='completed').length,findingsRetained:state.findings.length};
}

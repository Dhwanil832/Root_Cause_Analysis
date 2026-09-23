import type { AnalysisSnapshot } from '@/src/domain/types';
import type { CachedTask, EngineInput, EngineRun, EngineStore, RunStatus, EngineTask, TaskTrace } from '../types';
import { putJSON, readJSON, putState, readState, textChunks } from './artifacts';

export interface RunRow {
  id: string; track_id: string; number: number; parent_number: number; status: RunStatus; trigger: string;
  input_json: string; state_json: string | null; snapshot_json: string;
  lease: string | null; lease_until: number; generation: number; created_at: string; updated_at: string;
  pause_reason?: string;
}
export async function runFromRow(db: D1Database, r: RunRow): Promise<EngineRun> {
  return { id: r.id, trackId: r.track_id, number: r.number, parentNumber: r.parent_number, status: r.status,
    trigger: r.trigger, input: await readJSON<EngineInput>(db,r.input_json), state: await readState(db,r.state_json),
    lease: r.lease, leaseUntil: r.lease_until, generation: r.generation, createdAt: r.created_at, updatedAt: r.updated_at, pauseReason:r.pause_reason };
}
export class D1EngineStore implements EngineStore {
  readonly db: D1Database;
  private readonly targetRunId?: string;
  constructor(db: D1Database, targetRunId?: string) { this.db = db; this.targetRunId = targetRunId; }
  async claim(now: number, leaseMs: number) {
    const lease = crypto.randomUUID();
    const row = await this.db.prepare(`UPDATE engine_runs SET lease=?, lease_until=?, status='running'
      WHERE id = (SELECT r.id FROM engine_runs r WHERE r.status IN ('queued','running') AND r.lease_until < ? AND (? IS NULL OR r.id=?)
        AND NOT EXISTS (SELECT 1 FROM engine_runs earlier WHERE earlier.track_id=r.track_id AND earlier.number<r.number
          AND earlier.status IN ('queued','running','paused')) ORDER BY r.created_at,r.number LIMIT 1)
      AND lease_until < ? RETURNING *`).bind(lease, now + leaseMs, now, this.targetRunId || null, this.targetRunId || null, now).first<RunRow>();
    if (!row) return null;
    try { return await runFromRow(this.db,row); }
    catch(error) { await this.pause(row.id,`Checkpoint hydration failed: ${String(error)}`,lease); throw error; }
  }
  async renew(id: string, lease: string, until: number) {
    const r = await this.db.prepare("UPDATE engine_runs SET lease_until=? WHERE id=? AND lease=? AND status='running'").bind(until, id, lease).run();
    return !!r.meta.changes;
  }
  async save(run: EngineRun, expected: number, snapshot: AnalysisSnapshot, cache?: CachedTask) {
    const now = new Date().toISOString();
    // All dependent writes are guarded by this lease + generation in one D1 batch.
    const guard = "EXISTS (SELECT 1 FROM engine_runs WHERE id=? AND lease=? AND generation=? AND status='running')";
    const bindings = [run.id, run.lease, expected];
    const statements: D1PreparedStatement[] = [];
    if (cache) statements.push(this.db.prepare(`INSERT OR REPLACE INTO engine_task_cache
      (track_id,cache_key,kind,output_json,evidence_json,created_at) SELECT ?,?,?,?,?,? WHERE ${guard}`)
      .bind(cache.trackId, cache.key, cache.kind, await putJSON(this.db,cache.output), await putJSON(this.db,cache.evidenceIds), cache.createdAt, ...bindings));
    const task = run.state?.tasks.find(t => t.status === 'running') || [...(run.state?.tasks || [])].reverse().find(t => t.completedAt);
    if (task) statements.push(this.db.prepare(`INSERT INTO engine_task_events (id,run_id,task_id,kind,status,attempt,payload_json,created_at)
      SELECT ?,?,?,?,?,?,?,? WHERE ${guard}`).bind(crypto.randomUUID(), run.id, task.id, task.kind, task.status, task.attempts, await putJSON(this.db,task), now, ...bindings));
    const snapshotJSON = await putJSON(this.db,snapshot);
    if (run.status === 'completed' || run.status === 'partial') {
      statements.push(this.db.prepare(`INSERT OR IGNORE INTO versions (id,track_id,number,trigger,analysis_json,created_at)
        SELECT ?,?,?,?,?,? WHERE ${guard}`).bind(run.id, run.trackId, run.number, run.trigger, snapshotJSON, now, ...bindings));
      if (run.input.storyRoundId) statements.push(this.db.prepare(`UPDATE story_rounds SET status='applied', result_version=?, updated_at=?
        WHERE id=? AND ${guard}`).bind(run.number, now, run.input.storyRoundId, ...bindings));
    }
    statements.push(this.db.prepare(`UPDATE engine_runs SET state_json=?,snapshot_json=?,status=?,lease_until=?,generation=generation+1,updated_at=?,pause_reason=?
      WHERE id=? AND lease=? AND generation=? AND status='running'`).bind(await putState(this.db,run.state), snapshotJSON, run.status, run.leaseUntil, now, run.state?.pauseReason || '', ...bindings));
    const results = await this.db.batch(statements);
    return !!results.at(-1)?.meta.changes;
  }
  async previous(trackId: string, before: number) {
    const r = await this.db.prepare("SELECT state_json FROM engine_runs WHERE track_id=? AND number<? AND status IN ('completed','partial') ORDER BY number DESC LIMIT 1")
      .bind(trackId, before).first<{ state_json: string | null }>();
    return r?.state_json ? readState(this.db,r.state_json) : null;
  }
  async cached(trackId: string, key: string): Promise<CachedTask | null> {
    const r = await this.db.prepare('SELECT * FROM engine_task_cache WHERE track_id=? AND cache_key=?').bind(trackId, key)
      .first<{ kind: CachedTask['kind']; output_json: string; evidence_json: string; created_at: string }>();
    return r ? { key, trackId, kind: r.kind, output: await readJSON(this.db,r.output_json), evidenceIds: await readJSON(this.db,r.evidence_json), createdAt: r.created_at } : null;
  }
  async pause(id: string, reason: string, lease?: string | null) {
    const result = await this.db.prepare(`UPDATE engine_runs SET status='paused',pause_reason=?,lease=NULL,lease_until=0,generation=generation+1,updated_at=?
      WHERE id=? AND status IN ('queued','running')${lease ? ' AND lease=?' : ''}`)
      .bind(reason.slice(0,4000),new Date().toISOString(),id,...(lease?[lease]:[])).run();
    return !!result.meta.changes;
  }
  async trace(run: EngineRun, task: EngineTask): Promise<TaskTrace> {
    const id = task.traceId!, now = new Date().toISOString();
    await this.db.prepare('INSERT INTO engine_calls (id,run_id,task_id,attempt,created_at,updated_at) VALUES (?,?,?,?,?,?)')
      .bind(id,run.id,task.id,task.attempts,now,now).run();
    let ordinal=0;
    return {
      request: async value => { await this.db.prepare('UPDATE engine_calls SET request_json=?,updated_at=? WHERE id=?')
        .bind(await putJSON(this.db,value),new Date().toISOString(),id).run(); },
      append: async text => {
        for(const chunk of textChunks(text)) await this.db.prepare('INSERT INTO engine_artifact_chunks (artifact_id,ordinal,content) VALUES (?,?,?)')
          .bind(`stream:${id}`,ordinal++,chunk).run();
      },
      complete: async (status,result,error='') => { await this.db.prepare('UPDATE engine_calls SET status=?,result_json=?,error=?,updated_at=? WHERE id=?')
        .bind(status,await putJSON(this.db,result),error.slice(0,4000),new Date().toISOString(),id).run(); },
    };
  }
}

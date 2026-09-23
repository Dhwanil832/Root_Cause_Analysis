import type { RunRow } from '@/src/engine/tasks/d1-store';
import { ENGINE_VERSION, type EngineInput } from '@/src/engine/types';
import { readJSON, readState, putJSON, putState } from '@/src/engine/tasks/artifacts';
import { checkpointVersion } from '@/src/engine/tasks/checkpoint-version';
import { digest } from '@/src/engine/identity';
import { frameSchema } from '@/src/engine/investigation/contracts';
import { activeBoardFindings, hasUsablePosition } from '@/src/engine/investigation/usability';
import { project } from '@/src/engine/board/projection';

/** Explicit recovery of the old, overly strict edge-endpoint frame gate.
 * Original inputs, reads, findings, quarantines and failed traces are immutable.
 * This changes execution eligibility, NEVER an evidence or causal verdict. */
export async function recoverPartialFrame(db: D1Database, runId: string, expectedGeneration: number,
  checkpointHash: string, reason: string) {
  const row = await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(runId).first<RunRow>();
  if (!row || row.status !== 'paused' || row.generation !== expectedGeneration || row.lease_until !== 0)
    throw Error('Recovery requires the exact idle, paused checkpoint.');
  if (await db.prepare('SELECT id FROM versions WHERE id=? OR (track_id=? AND number=?)').bind(runId, row.track_id, row.number).first())
    throw Error('Published versions are immutable.');
  if (!reason.trim() || checkpointHash !== await digest([row.input_json, row.state_json, row.snapshot_json]))
    throw Error('Checkpoint hash or authorization reason changed.');
  const state = await readState(db, row.state_json), input = await readJSON<EngineInput>(db, row.input_json);
  if (!state || checkpointVersion(input, state) !== 'try6.0.0' || String(ENGINE_VERSION) !== 'try6.1.0'
    || state.phase !== 2 || state.tasks.some(t => t.status === 'running'))
    throw Error('Only an idle try6.0.0 frame checkpoint is compatible with this recovery.');
  const task = state.tasks.find(t => t.kind === 'frame' && t.status === 'failed');
  if (!task?.traceId || !hasUsablePosition(state)) throw Error('No usable saved frame to recover.');
  const rejected = state.quarantine.filter(q => q.taskId === task.id);
  if (!rejected.length || rejected.some(q => q.reason !== 'Relationship endpoints must be distinct selected observations or EVENT.'))
    throw Error('Unrelated frame failure requires separate diagnosis.');
  const call = await db.prepare('SELECT * FROM engine_calls WHERE id=? AND run_id=? AND task_id=?')
    .bind(task.traceId, runId, task.id).first<{status: string; request_json: string; result_json: string}>();
  if (!call || call.status !== 'failed') throw Error('Finished original failed frame trace is required.');
  const request = await readJSON<{kind: string; packet: {notebook: Array<{ref: string; statement: string}>}}>(db, call.request_json);
  const result = await readJSON<{output: unknown}>(db, call.result_json);
  const output = frameSchema.parse(result.output);
  if (request.kind !== 'frame' || request.packet.notebook.length !== state.findings.length
    || request.packet.notebook.some((f, i) => f.ref !== `F${i + 1}` || f.statement !== state.findings[i].statement))
    throw Error('Original notebook binding changed; no implicit remapping permitted.');
  const refs = new Map(request.packet.notebook.map((f, i) => [f.ref, state.findings[i].id]));
  const nodes = new Set(activeBoardFindings(state).map(f => f.id));
  if (output.nodes.some(n => !nodes.has(refs.get(n.finding) || '')))
    throw Error('A submitted frame node was not retained; explicit review required.');
  for (const q of rejected) {
    const edge = output.edges.find(e => JSON.stringify(e) === JSON.stringify(q.item));
    if (!edge || ![edge.from, edge.to].every(id => id === 'EVENT' || refs.has(id)))
      throw Error('Rejected edge is not an unchanged saved proposal with known references.');
    (state.investigation!.rejectedConnections ||= []).push({ taskId: task.id,
      fromFindingId: refs.get(edge.from) || edge.from, toFindingId: refs.get(edge.to) || edge.to,
      rationale: edge.rationale, reason: q.reason });
  }
  const backup = await putJSON(db, row), at = new Date().toISOString();
  state.executionMigrations = [...(state.executionMigrations || []), {from: 'try6.0.0', to: ENGINE_VERSION,
    at, reason, checkpointHash, backup, recoveredTaskIds: [task.id]}];
  task.status = 'completed'; task.partial = true;
  task.error = `${rejected.length} invalid connections remain quarantined. Usable frame recovered; separate connection task will re-evaluate proposals.`;
  state.pauseReason = ''; delete state.pauseAfterTaskId;
  state.changes.push({targetId: task.id, kind: 'rechecked', reason: 'Operator-approved partial-frame execution recovery. No observations, verdicts, source inputs, or failed traces changed.'});
  const changed = await db.prepare(`UPDATE engine_runs SET state_json=?,snapshot_json=?,status='queued',pause_reason='',
    lease=NULL,lease_until=0,generation=generation+1,updated_at=? WHERE id=? AND status='paused' AND generation=? AND lease_until=0`)
    .bind(await putState(db, state), await putJSON(db, project(state, input, 'queued')), at, runId, expectedGeneration).run();
  if (!changed.meta.changes) throw Error('Checkpoint changed during recovery; dispatch not authorized.');
  return {runId, version: row.number, queued: true, engineVersion: ENGINE_VERSION, backup,
    completedReadsRetained: state.tasks.filter(t => t.kind === 'read' && t.status === 'completed').length,
    findingsRetained: state.findings.length, quarantinedEdgesRetained: rejected.length};
}

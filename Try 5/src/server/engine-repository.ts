import type { AnalysisSnapshot, DocumentRecord, HumanDecision, InvestigationAnswer, ModelDescriptor, VersionRecord } from '@/src/domain/types';
import { D1EngineStore, type RunRow } from '@/src/engine/tasks/d1-store';
import { initializeState } from '@/src/engine/tasks/planner';
import { project } from '@/src/engine/board/projection';
import { ENGINE_VERSION, type EngineInput } from '@/src/engine/types';
import { contextCapacity } from '@/src/engine/context/planner';
import { putJSON,readJSON,readState,putState } from '@/src/engine/tasks/artifacts';
import { onlyQuestionRejections } from '@/src/engine/records';
import { checkpointVersion } from '@/src/engine/tasks/checkpoint-version';
import { REVIEW_FORMATTING_POLICY } from '@/src/engine/review/formatting';

export async function latestInput(db: D1Database, trackId: string) {
  const row = await db.prepare('SELECT * FROM engine_runs WHERE track_id=? ORDER BY number DESC LIMIT 1').bind(trackId).first<RunRow>();
  return row ? { row, input: await readJSON<EngineInput>(db,row.input_json) } : null;
}
export async function enqueueRevision(db: D1Database, trackId: string, incident: string, model: ModelDescriptor,
  documents: DocumentRecord[], incoming: InvestigationAnswer[] = [], options: { expectedVersion?: number; storyRoundId?: string; humanDecision?: HumanDecision; initial?: boolean; reviewAfterReading?:boolean } = {}) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const previous = await latestInput(db, trackId);
    if(previous?.input.model.digest&&model.digest&&previous.input.model.digest!==model.digest)throw new Error('Model digest changed. Start a new model track instead of mixing versions.');
    if (options.initial && previous) return { version: previous.row.number, queued: previous.row.status === 'queued' || previous.row.status === 'running' };
    if (options.expectedVersion !== undefined && (previous?.row.number || 0) !== options.expectedVersion) throw new Error('This answer batch refers to a stale input revision.');
    const ids = new Set(incoming.map(a => a.questionId));
    const { apiKey: _credential, ...publicModel } = model;
    void _credential;
    const previousState=await readState(db,previous?.row.state_json||null);
    const input: EngineInput = { incident,
      reviewFormattingPolicy:REVIEW_FORMATTING_POLICY,
      engineVersion:ENGINE_VERSION,reviewAfterReading:options.reviewAfterReading??previousState?.reviewAfterReading??previous?.input.reviewAfterReading??process.env.RCA_REVIEW_AFTER_READING==='true',
      model: previous?.input.model || {...publicModel,contextWindow:contextCapacity(model)}, // Freeze identity/config; resolve credentials only per call.
      documents, answers: [...(previous?.input.answers || []).filter(a => !ids.has(a.questionId)), ...incoming],
      storyRoundId: options.storyRoundId, humanDecision: options.humanDecision,
      answerQuestions: {...previous?.input.answerQuestions,...Object.fromEntries((previousState?.questions||[]).map(q=>[q.id,q.text]))} };
    const number = (previous?.row.number || 0) + 1, now = new Date().toISOString();
    const state = await initializeState(input, number, null);
    const snapshot = project(state, input, 'queued');
    const trigger = options.humanDecision ? `Human review: ${options.humanDecision.action}` : options.storyRoundId ? `Story release ${options.storyRoundId}`
      : number === 1 ? 'Initial incident and evidence' : `Evidence update: ${incoming.map(a => a.questionId).join(', ') || 'document upload'}`;
    const id = crypto.randomUUID();
    try {
      await db.prepare(`INSERT INTO engine_runs (id,track_id,number,parent_number,status,trigger,input_json,state_json,snapshot_json,created_at,updated_at)
        VALUES (?,?,?,?,'queued',?,?,NULL,?,?,?)`).bind(id, trackId, number, number - 1, trigger, await putJSON(db,input), await putJSON(db,snapshot), now, now).run();
      return { version: number, queued: true,engineVersion:ENGINE_VERSION,reviewAfterReading:input.reviewAfterReading };
    } catch (error) {
      if (!/unique|constraint/i.test(String(error)) || attempt === 3) throw error;
      // A concurrent submission wins this number; retry against its immutable inputs.
    }
  }
  throw new Error('Could not reserve an input revision.');
}
export async function engineVersions(db: D1Database, trackId: string): Promise<VersionRecord[]> {
  const rows = await db.prepare('SELECT * FROM engine_runs WHERE track_id=? ORDER BY number').bind(trackId).all<RunRow>();
  return Promise.all(rows.results.map(async r => {
    const analysis=await readJSON<AnalysisSnapshot>(db,r.snapshot_json);
    if(analysis.engineProgress){analysis.engineProgress.status=r.status;analysis.engineProgress.pauseReason=r.pause_reason||undefined;}
    if(r.pause_reason)analysis.stageErrors=[...analysis.stageErrors,{stage:'incident-understanding',message:r.pause_reason,recoverable:true}];
    return {id:r.id,number:r.number,trigger:r.trigger,createdAt:r.created_at,executionStatus:r.status,analysis};
  }));
}
export interface ResumeOptions { taskId?: string; pauseAfterTask?: boolean }
export async function retryFailedTasks(db: D1Database, trackId: string, options: ResumeOptions = {}) {
  if (options.pauseAfterTask && !options.taskId) throw new Error('Select a task for single-task recovery.');
  const paused=await db.prepare("SELECT * FROM engine_runs WHERE track_id=? AND status='paused' ORDER BY number LIMIT 1").bind(trackId).first<RunRow>();
  if(paused) {
    const input=await readJSON<EngineInput>(db,paused.input_json);
    const state=await readState(db,paused.state_json);
    if(checkpointVersion(input,state)!==ENGINE_VERSION)throw new Error('This saved run used a different engine. Explicitly migrate a compatible paused checkpoint before resuming.');
    if (options.taskId && !state) throw new Error('No saved task state for this recovery.');
    if(state) {
      if (options.taskId) {
        const target = state.tasks.find(t => t.id === options.taskId);
        if (!target || !['queued','failed','blocked','running'].includes(target.status)) throw new Error('Selected task is missing or already completed. Completed work cannot be retried in place.');
        if (!target.dependsOn.every(id => state.tasks.some(t => t.id === id && t.status === 'completed'))) throw new Error('Selected task has unfinished prerequisites; recover those first.');
        target.status = 'queued'; target.error = '';
        state.pauseAfterTaskId = options.pauseAfterTask ? target.id : undefined;
        state.changes.push({ targetId: target.id, kind: 'rechecked', reason: 'Operator requested scoped task recovery. Completed tasks, prior call traces and evidence are retained.' });
      }
      if(state.pauseReason?.startsWith('Evidence-reading checkpoint:'))state.readingApproved=true;
      state.pauseReason='';
      for(const task of state.tasks)if(!options.taskId && (task.status==='failed'||task.status==='blocked')) {
        const rejected=state.quarantine.filter(q=>q.taskId===task.id);
        // Unpublished checkpoints from the old all-or-nothing policy already
        // contain the valid facts. Do not resample those merely to omit a bad question.
        if(task.status==='failed'&&task.output&&onlyQuestionRejections(rejected)) {
          task.status='completed';task.error=`${rejected.length} optional question(s) quarantined; primary result retained without rerunning inference.`;
          state.changes.push({targetId:task.id,kind:'retained',reason:task.error});
        } else {task.status='queued';task.error='';}
      }
    }
    const result = await db.prepare("UPDATE engine_runs SET status='queued',state_json=?,pause_reason='',lease=NULL,lease_until=0,generation=generation+1,updated_at=? WHERE id=? AND status='paused' AND generation=?")
      .bind(await putState(db,state),new Date().toISOString(),paused.id,paused.generation).run();
    if (!result.meta.changes) throw new Error('Run changed during recovery; inspect its current state before retrying.');
    return {version:paused.number,queued:true};
  }
  if (options.taskId) throw new Error('Pause the run before selecting a recovery task.');
  const latest = await latestInput(db, trackId);
  if (!latest) return null;
  if (['queued','running'].includes(latest.row.status)) return { version: latest.row.number, queued: true };
  if (latest.row.status==='paused') {
    await db.prepare("UPDATE engine_runs SET status='queued',lease=NULL,lease_until=0,updated_at=? WHERE id=? AND status='paused'")
      .bind(new Date().toISOString(),latest.row.id).run();
    return {version:latest.row.number,queued:true};
  }
  const state = await readState(db,latest.row.state_json);
  if (!state) throw new Error('No saved task state to resume.');
  const failed = state.tasks.filter((t: { status: string }) => ['failed','blocked'].includes(t.status));
  if (!failed.length) throw new Error('No failed tasks remain. Add evidence to continue the investigation.');
  // Never mutate a published snapshot: retry produces another input revision,
  // whose successful calls are reused by content/dependency key.
  const result = await enqueueRevision(db, trackId, latest.input.incident, latest.input.model, latest.input.documents, [], {});
  return result;
}
export { D1EngineStore };

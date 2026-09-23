import type { ModelDescriptor } from '@/src/domain/types';
import { applyEvidenceTask } from '@/src/stages/evidence-reading/task';
import { applyQuestionTask, reconcileAnswers } from '@/src/stages/question-broker/task';
import { applyBoardTask } from '../board/changes';
import { project } from '../board/projection';
import { quarantine,onlyQuestionRejections } from '../records';
import { ENGINE_VERSION, type EngineStore, type TaskTrace } from '../types';
import { initializeState, planNext } from './planner';
import { executeTask, type ProviderRunner, type MediaLoader } from './executor';
import type { EngineInput } from '../types';
import { invalidateReview } from '../review/interpretation';
import { checkpointVersion } from './checkpoint-version';
import { isInvestigationKind } from '../investigation/contracts';
import { applyInvestigationTask, syncBoardEvidence } from '../investigation/apply';
import { hasUsablePosition } from '../investigation/usability';

export async function workerStep(store: EngineStore, resolveModel: (id: string) => Promise<ModelDescriptor>, runner?: ProviderRunner,
  mediaFactory?:(input:EngineInput)=>MediaLoader) {
  const leaseMs = 90_000;
  const run = await store.claim(Date.now(), leaseMs);
  if (!run) return { idle: true };
  let leaseLost = false;
  const controller=new AbortController();
  const loseLease=()=>{leaseLost=true;controller.abort(new Error('Run paused or worker lease lost.'));};
  const timer = setInterval(() => { void store.renew(run.id, run.lease!, Date.now() + leaseMs).then(ok => { if (!ok) loseLease(); }).catch(loseLease); }, 5_000);
  try {
    if(checkpointVersion(run.input,run.state)!==ENGINE_VERSION)throw new Error('This checkpoint belongs to a different engine version. Explicitly migrate a compatible paused checkpoint.');
    if (!run.state) run.state = await initializeState(run.input, run.number, await store.previous(run.trackId, run.number));
    const state = run.state;
    // A lost worker may have submitted a provider request but not committed its
    // result. Only that uncertain task is retried; completed tasks remain intact.
    for (const t of state.tasks.filter(t => t.status === 'running')) { t.status = 'queued'; t.error = 'Recovered expired worker lease; previous uncommitted request outcome is unknown.'; }
    const task = await planNext(state);
    if (!task) {
      reconcileAnswers(state);
      run.status = state.pauseReason ? 'paused' : state.tasks.some(t => t.status === 'failed' || t.status === 'blocked') || state.quarantine.length ? 'partial' : 'completed';
      run.leaseUntil=0;
      const saved = await store.save(run, run.generation, project(state, run.input, run.status));
      return { idle: false, runId: run.id, status: run.status, saved };
    }
    task.status = 'running'; task.attempts++; task.traceId=crypto.randomUUID(); task.engineVersion=ENGINE_VERSION; run.status = 'running';
    if(task.kind==='review'||task.kind==='interpret') {
      const finding=state.findings.find(f=>f.id===task.targetIds[0]);
      if(finding)invalidateReview(finding,'unreviewed',`${task.kind} pending; no current evidence verdict.`,state);
    }
    // Persist the intent before inference so a process crash leaves a recoverable unit.
    if (!await store.save(run, run.generation, project(state, run.input, 'running'))) return { leaseLost: true };
    run.generation++;
    let cached, trace:TaskTrace|undefined, rawResult:unknown;
    try {
      trace=await store.trace?.(run,task);
      if (run.input.model.provider === 'builtin') throw new Error('The deterministic preview is not a scientific RCA model. Select an installed Ollama or configured API model.');
      const resolved = await resolveModel(run.input.model.id);
      if (run.input.model.digest && resolved.digest !== run.input.model.digest) throw new Error('Installed model digest changed or is unavailable. Create a new track; do not mix model identities.');
      const model = {...resolved,...run.input.model,apiKey:resolved.apiKey};
      const result = await executeTask(state, task, model, run.trackId, store, runner,mediaFactory?.(run.input),{signal:controller.signal,trace});
      rawResult={output:result.output,providerAttempts:result.providerAttempts,usage:{inputTokens:result.inputTokens,outputTokens:result.outputTokens}};
      const previousIds=new Set([...state.findings,...state.questions,...state.propositions,...state.relationships].map(r=>r.id));
      const rejectedBefore=state.quarantine.length;
      Object.assign(task, { cacheKey: result.cacheKey, reused: result.reused, evidenceIds: result.evidenceIds,
        omittedEvidenceIds: result.omittedEvidenceIds, contextBytes: result.contextBytes, durationMs: result.durationMs,
        inputTokens: result.inputTokens, outputTokens: result.outputTokens });
      if (isInvestigationKind(task.kind)) await applyInvestigationTask(state, task, result.output, result.refs);
      else if (['read','understand','tag','specialist','interpret','review'].includes(task.kind)) applyEvidenceTask(state, task, result.output, result.refs);
      else if (task.kind === 'broker' || task.kind === 'answer') applyQuestionTask(state, task, result.output, result.refs);
      else applyBoardTask(state, task, result.output, result.refs);
      syncBoardEvidence(state);
      task.producedIds=[...state.findings,...state.questions,...state.propositions,...state.relationships].filter(r=>!previousIds.has(r.id)).map(r=>r.id);
      task.output = { decision: (result.output as { decision?: unknown }).decision };
      // The raw model judgment remains in the call trace; dashboard summaries
      // must use the applied gate result, not a contradictory approval sentence.
      if(task.kind==='review') task.output={decision:{summary:state.findings.find(f=>f.id===task.targetIds[0])?.reviewReason || 'Review target missing.'}};
      task.status = 'completed'; task.error = ''; task.completedAt = new Date().toISOString();
      if(state.quarantine.length>rejectedBefore) {
        const rejected=state.quarantine.slice(rejectedBefore);
        const usable = task.kind === 'connect' || (['frame', 'refine'].includes(task.kind) && hasUsablePosition(state));
        task.status=onlyQuestionRejections(rejected) || usable ? 'completed':'failed';
        task.partial = task.status === 'completed';
        task.error=`${rejected.length} invalid item(s) quarantined; valid sibling records were retained${usable ? ' and the usable position can continue' : ''}.`;
      } else cached = { key: result.cacheKey, trackId: run.trackId, kind: task.kind, output: result.output, evidenceIds: result.evidenceIds, createdAt: task.completedAt };
      if (task.kind === 'read' && task.status === 'completed' && state.investigation)
        state.investigation.readSpanIds = [...new Set([...state.investigation.readSpanIds, ...task.targetIds])];
      await trace?.complete(task.status==='failed'?'failed':'completed',rawResult,task.error);
    } catch (error) {
      task.error = error instanceof Error ? error.message : String(error);
      if(task.kind==='review'||task.kind==='interpret') {
        const finding=state.findings.find(f=>f.id===task.targetIds[0]);
        if(finding)invalidateReview(finding,'incomplete',`${task.kind} incomplete: ${task.error}`,state);
      }
      const attempts=(error as { attempts?:unknown })?.attempts;
      await trace?.complete('failed',{output:rawResult,providerAttempts:attempts},task.error);
      // Service/identity failures are global; unusable individual responses are
      // task-local. Never admit partial JSON or pause independent specialists.
      if (/fetch failed|ECONNREFUSED|ECONNRESET|ENOTFOUND|network|unreachable|(?:HTTP|returned) (401|403|429|50[0234])|digest changed|API key.*(missing|configured)|API provider.*not configured|PROVIDER_VAULT_KEY/i.test(task.error)) {
        task.status='queued'; run.status='paused'; run.leaseUntil=0;state.pauseReason=task.error;
        const saved=leaseLost?false:await store.save(run,run.generation,project(state,run.input,'paused'));
        return {idle:false,runId:run.id,status:'paused',error:task.error,saved};
      }
      task.status = 'failed';
      task.completedAt = new Date().toISOString();
      quarantine(state, task, { traceId:task.traceId }, error);
    }
    if (leaseLost) return { leaseLost: true, runId: run.id };
    if(task.status==='failed'&&['read','frame'].includes(task.kind)) {
      state.pauseReason=`Prerequisite ${task.kind} failed: ${task.error}`;run.status='paused';
    }
    if (state.pauseAfterTaskId === task.id) {
      delete state.pauseAfterTaskId;
      state.pauseReason = `Task recovery checkpoint: ${task.kind} ${task.id} ${task.status}. Inspect the retained result before resuming other work.${task.error ? ` ${task.error}` : ''}`;
      run.status = 'paused';
    }
    // Release after each atomic task. The next revision waits until this run is terminal.
    const lease = run.lease; run.leaseUntil = 0;
    const saved = await store.save({ ...run, lease }, run.generation, project(state, run.input, run.status), cached);
    return { idle: false, runId: run.id, taskId: task.id, status:run.status==='paused'?'paused':task.status, saved };
  } catch(error) {
    controller.abort();
    const reason=`Worker stopped before further inference: ${error instanceof Error?error.message:String(error)}`;
    // This emergency write is tiny and independent of the failed checkpoint.
    const paused=await store.pause?.(run.id,reason,run.lease);
    if(!paused)throw error;
    return {idle:false,runId:run.id,status:'paused',error:reason};
  } finally { clearInterval(timer); }
}

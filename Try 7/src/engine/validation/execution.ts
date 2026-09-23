import type {EngineState,EngineTask,RunStatus} from '../types';
import {TaskContextError} from '../context/planner';

export function failureCategory(error:unknown):EngineTask['failureCategory'] {
  const message=error instanceof Error?error.message:String(error);
  if(error instanceof TaskContextError)return 'harness';
  if(/ECONNREFUSED|ECONNRESET|ENOTFOUND|fetch failed|HTTP (401|403|429|50[0234])|digest changed|API key|PROVIDER_VAULT_KEY/.test(message))return 'environment';
  // Generic exceptions and parser/provider wrappers do not prove a model error.
  return 'unattributed';
}
export function assessmentGate(state:EngineState,status:RunStatus) {
  const issues=state.tasks.filter(t=>['failed','blocked'].includes(t.status)).map(t=>`${t.kind}: ${t.failureCategory||'unattributed'} — ${t.error}`);
  if(state.quarantine.length)issues.push(`${state.quarantine.length} rejected output items require attribution against raw traces.`);
  if(state.pauseReason)issues.push(state.pauseReason);
  const pending=state.questions.flatMap(q=>(q.deliveries||[]).filter(d=>!q.coveredBy&&d.answerRevision===q.answerRevision&&d.status==='pending'));
  if(pending.length)issues.push(`${pending.length} answer delivery receipts are still pending.`);
  if(state.investigation?.pendingImpacts?.length)issues.push(`${state.investigation.pendingImpacts.length} evidence impacts are still pending.`);
  return {status:!['partial','completed'].includes(status)?'pending' as const:issues.length?'execution-inconclusive' as const:'ready-for-output-review' as const,issues};
}

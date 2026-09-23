import type { EngineState, EngineQuestion, EngineTask } from '../types';
import { normalize } from '../identity';

export function activeQuestion(state:EngineState,q:EngineQuestion) {
  if(!state.investigation)return true;
  return !!(state.investigation.directions.some(d=>d.questionId===q.id)
    || q.reviewTargets?.some(id=>state.investigation!.selectedFindingIds.includes(id))
    || q.targetIds?.some(id=>state.investigation!.selectedFindingIds.includes(id)
      || state.relationships.some(e=>e.id===id&&e.proposedBy?.length)
      || state.investigation!.branches.some(b=>b.id===id)));
}
export function bindQuestion(q:EngineQuestion,task:EngineTask,options:{branchId?:string;decision?:string;evidenceNeeded?:string;ifPresent?:string;ifAbsent?:string;parts?:string[]}={}) {
  q.targetIds=[...new Set([...(q.targetIds||[]),...(task.targetIds||[]),...(options.branchId?[options.branchId]:[])])];
  q.parts ||= [{id:`${q.id}:p1`,text:q.intent||q.text}];
  const oldPartIds=new Set(q.parts.map(p=>p.id));
  // Explicit subparts replace the unsolved placeholder, not add another
  // catch-all requirement that can never receive an exact coverage receipt.
  if(options.parts?.length&&!q.answerRevision&&q.parts.length===1&&q.parts[0].text===(q.intent||q.text)) {
    const old=q.parts[0].id;
    q.parts=options.parts.map((text,i)=>({id:`${q.id}:p${i+1}`,text}));
    for(const s of q.subscriptions||[])if(s.partIds.includes(old))s.partIds=q.parts.map(p=>p.id);
  }
  if(options.parts?.length) for(const text of options.parts)if(!q.parts.some(p=>normalize(p.text)===normalize(text)))
    q.parts.push({id:`${q.id}:p${q.parts.length+1}`,text});
  if(q.answerRevision&&q.parts.some(p=>!oldPartIds.has(p.id))) {
    q.inventory='';
    if(q.status==='answered'){q.status='partial';q.answerCompleteness='partial';}
  }
  const decision=options.decision||q.decision;
  const id=JSON.stringify([task.owner,options.branchId||'',decision,options.evidenceNeeded||q.intent,options.ifPresent||'',options.ifAbsent||'']);
  if(!q.subscriptions?.some(s=>s.id===id))(q.subscriptions ||= []).push({id,owner:task.owner,branchId:options.branchId,
    targetIds:[...(task.targetIds||[])],decision,evidenceNeeded:options.evidenceNeeded||q.intent,
    ifPresent:options.ifPresent||'',ifAbsent:options.ifAbsent||'',partIds:q.parts.map(p=>p.id)});
}
export function mergeQuestions(state:EngineState,q:EngineQuestion,canonical:EngineQuestion,reason:string) {
  if(q.id===canonical.id||canonical.coveredBy||state.questions.indexOf(canonical)>=state.questions.indexOf(q))
    throw Error('Question coverage must use an earlier canonical request; no self references or cycles.');
  for(const field of ['subject','location','time'] as const) if(normalize(q[field])!==normalize(canonical[field]))
    throw Error(`Cannot merge questions with different ${field} scopes.`);
  // The semantic decision remains attributable to the resolver. The reducer
  // retains all needs and subscriptions; none may disappear on a merge.
  if(!reason.trim())throw Error('A semantic merge needs a scope/coverage justification.');
  const partMap=new Map<string,string>();canonical.parts ||= [{id:`${canonical.id}:p1`,text:canonical.intent||canonical.text}];
  for(const part of q.parts||[{id:`q:${q.id}`,text:q.intent||q.text}]) {
    let existing=canonical.parts.find(p=>normalize(p.text)===normalize(part.text));
    if(!existing){existing={id:`${canonical.id}:p${canonical.parts.length+1}`,text:part.text};canonical.parts.push(existing);}
    partMap.set(part.id,existing.id);
  }
  canonical.subscriptions ||= [];
  for(const s of q.subscriptions||[])if(!canonical.subscriptions.some(c=>c.id===s.id))canonical.subscriptions.push({...s,partIds:s.partIds.map(id=>partMap.get(id)||id)});
  for(const field of ['owners','spanIds','targetIds','reviewTargets','inquiryTargets'] as const)
    canonical[field]=[...new Set([...(canonical[field]||[]),...(q[field]||[])])];
  const direction=state.investigation?.directions.find(d=>d.questionId===canonical.id),own=state.investigation?.directions.find(d=>d.questionId===q.id);
  if(direction&&own)direction.branchIds=[...new Set([...direction.branchIds,...own.branchIds])];
  q.coveredBy=canonical.id;q.status='covered';q.reason=reason;
  if(canonical.answer&&canonical.parts.some(p=>!canonical.coverage?.some(c=>c.partId===p.id&&c.status==='answered')))canonical.status='partial';
  queueDeliveries(canonical);
}
export function queueDeliveries(q:EngineQuestion) {
  if(!q.answerRevision)return;
  for(const owner of q.owners)if(!q.deliveries?.some(d=>d.owner===owner&&d.answerRevision===q.answerRevision))
    (q.deliveries ||= []).push({owner,answerRevision:q.answerRevision,status:'pending'});
}
export function receiveDelivery(q:EngineQuestion,owner:string,taskId:string,implication:string) {
  const delivery=q.deliveries?.find(d=>d.owner===owner&&d.answerRevision===q.answerRevision);
  if(!delivery)throw Error('Answer delivery is not assigned to this owner/revision.');
  Object.assign(delivery,{status:'received',taskId,implication});
}

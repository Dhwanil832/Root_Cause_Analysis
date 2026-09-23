import { inquirySchema } from '../contracts';
import { bindCommentary } from '../citations';
import { ingestQuestion, quarantine, resolve, type References } from '../records';
import type { EngineState, EngineTask, InquiryResult } from '../types';

/** A research proposal, not a factual board update. All observations and
 * explanations remain proposed; questions enter the existing broker route. */
export function applyInquiry(state:EngineState,task:EngineTask,raw:unknown,refs:References) {
  const out=inquirySchema.parse(raw), ids=new Set(out.explanations.map(e=>e.id));
  if(ids.size!==out.explanations.length)throw new Error('Explanation IDs must be unique within this inquiry.');
  const bind=(text:string)=>bindCommentary(text,refs);
  const result:InquiryResult={id:`inquiry:${task.id}`,taskId:task.id,findingIds:[...task.targetIds],status:'proposed',summary:bind(out.decision.summary),
    observations:out.observations.map(o=>({statement:o.statement,spanIds:resolve(o.references,refs.sources),limitation:bind(o.limitation)})),
    explanations:out.explanations.map(e=>({id:e.id,title:e.title,mechanism:bind(e.mechanism),supportingSpanIds:resolve(e.supporting,refs.sources),
      opposingSpanIds:resolve(e.opposing,refs.sources),unresolved:bind(e.unresolved)})),questions:[]};
  for(const q of out.questions)try {
    if(!q.evidenceNeeded.trim()||!q.contrasts.length||q.contrasts.some(c=>!ids.has(c.explanationId)||!c.expectedObservation.trim()||!c.implication.trim()))
      throw new Error('A focused question needs an evidence request and a testable implication for a named explanation.');
    const questionId=ingestQuestion(state,task,q,refs), question=state.questions.find(q=>q.id===questionId)!;
    question.inquiryTargets=[...new Set([...(question.inquiryTargets||[]),result.id])];
    result.questions.push({questionId,evidenceNeeded:bind(q.evidenceNeeded),contrasts:q.contrasts.map(c=>({...c,expectedObservation:bind(c.expectedObservation),implication:bind(c.implication)}))});
  }catch(error){quarantine(state,task,q,error);}
  state.inquiries ||= [];
  const previous=state.inquiries.findIndex(i=>i.id===result.id);
  if(previous>=0)state.inquiries[previous]=result;else state.inquiries.push(result);
  task.producedIds=result.questions.map(q=>q.questionId);
  return result;
}

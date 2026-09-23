import type {EngineState} from '../types';
import {normalize} from '../identity';
import {mergeQuestions} from './ledger';

/** Narrow, auditable repair for an unpublished checkpoint produced by the
 * old text/identity ambiguity. No question meaning, evidence, or verdict is
 * inferred. Already-answered or externally referenced records require review. */
export function recoverReferenceQuestions(state:EngineState) {
  for(const q of state.questions.filter(q=>!q.coveredBy)) {
    const id=q.text.match(/^⟦question:([^⟧]+)⟧$/)?.[1];
    if(!id)continue;
    const canonical=state.questions.find(c=>c.id===id&&!c.coveredBy);
    if(!canonical||state.questions.indexOf(canonical)>=state.questions.indexOf(q)
      ||(['subject','location','time'] as const).some(key=>normalize(q[key])!==normalize(canonical[key]))
      ||q.answerRevision||state.sources.some(s=>s.questionId===q.id)
      ||state.tasks.some(t=>['queued','running'].includes(t.status)&&t.targetIds.includes(q.id)))
      throw Error('Reference-only question cannot be safely rebound in place; preserve this checkpoint for explicit review.');
    const parts=q.parts?.map(p=>{
      const known=canonical.parts?.find(c=>c.id===p.text||normalize(c.text)===normalize(p.text));
      if(!known)throw Error('Reference-only question contains an unrecognized subpart; no automatic recovery was applied.');
      return {...p,text:known.text};
    });
    const before=JSON.stringify({question:q,canonical});
    q.text=canonical.text;q.parts=parts;
    mergeQuestions(state,q,canonical,'Question identity recovery: the prior response referenced this exact existing question; no new question wording or evidence was supplied.');
    state.changes.push({targetId:q.id,kind:'revised',reason:'question-identity-v1: repaired a reference-only duplicate on explicit resume; original provider response and before-state retained.',
      before,after:JSON.stringify({question:q,canonical})});
  }
}

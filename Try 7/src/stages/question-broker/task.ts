import { answerSchema, brokerSchema } from '@/src/engine/contracts';
import { ingestRows, resolve, type References } from '@/src/engine/records';
import type { EngineState, EngineTask } from '@/src/engine/types';
import { bindCommentary } from '@/src/engine/citations';
import {mergeQuestions} from '@/src/engine/questions/ledger';

export function applyQuestionTask(state: EngineState, task: EngineTask, raw: unknown, refs: References) {
  const question = state.questions.find(q => q.id === task.targetIds[0]);
  if (!question) throw new Error('Question target does not exist.');
  if (task.kind === 'broker') {
    const out = brokerSchema.parse(raw);
    if (!out.equivalentTo) return;
    const id = refs.questions.get(out.equivalentTo);
    const target = state.questions.find(q => q.id === id && q.id !== question.id && !q.coveredBy);
    if (!target) throw new Error('Broker selected an invalid, self, or chained coverage owner.');
    mergeQuestions(state,question,target,bindCommentary(out.reason,refs));
  } else {
    const out = answerSchema.parse(raw), cited = resolve(out.references, refs.sources);
    question.answerCompleteness = out.status;
    question.answer = bindCommentary(out.answer,refs); question.answerSpanIds = cited;
    question.findingIds = ingestRows(state, task, out, refs);
    question.status = out.status === 'answered' && cited.length ? 'partial'
      : out.status === 'not-found' ? 'awaiting-user' : out.status === 'answered' ? 'awaiting-user' : out.status;
    question.reason = bindCommentary(out.evidenceRequest,refs) || 'Answer findings require separate evidence review.';
    question.searchedSpanIds = task.evidenceIds;
    question.inventory = state.sources.map(s => `${s.id}:${s.textHash}`).sort().join('|');
  }
}

/** Route reviewed answers to every specialist owner without manufacturing new evidence. */
export function reconcileAnswers(state: EngineState) {
  for (const q of state.questions.filter(q => !q.coveredBy)) {
    const claims = q.findingIds.map(id => state.findings.find(f => f.id === id)).filter(f => !!f);
    if (claims.some(f => ['contradicted','conflicting'].includes(f.status))) q.status = 'conflicting';
    // Answer coverage is not conditional on selecting its facts as board nodes.
    // A later contradicted finding still reopens the answer above.
    else if(q.answerSpanIds.length&&q.coverage?.length)
      q.status=q.coverage.some(c=>c.status==='conflicting')?'conflicting'
        :q.parts?.every(p=>q.coverage?.some(c=>c.partId===p.id&&c.status==='answered'))?'answered':'partial';
    else if(q.answerSpanIds.length&&q.answerCompleteness)
      q.status=q.answerCompleteness==='answered'&&claims.length&&claims.every(f=>f.status==='supported')?'answered'
        :q.answerCompleteness==='unavailable'?'unavailable':q.answerCompleteness==='conflicting'?'conflicting':'partial';
    for (const claim of claims) claim.owners = [...new Set([...claim.owners, ...q.owners])];
  }
  for (const q of state.questions.filter(q => q.coveredBy)) {
    const canonical = state.questions.find(c => c.id === q.coveredBy);
    if (!canonical) continue;
    q.answer = canonical.answer; q.answerSpanIds = [...canonical.answerSpanIds]; q.findingIds = [...canonical.findingIds];
  }
}

import type {EngineState,EngineTask} from '@/src/engine/types';

/** Deterministic original-source dependencies; lexical retrieval supplements,
 * but cannot replace these sources with a summary or an unrelated match. */
export function bundleSpans(state:EngineState,task:EngineTask) {
  if(!['frame','refine','connect','consult','respond','revise','role'].includes(task.kind))return task.requiredSpanIds;
  const all=state.sources.flatMap(s=>s.spans);
  if(task.kind==='frame'||task.kind==='refine')return all.map(s=>s.id);
  const branch=state.investigation?.branches.find(b=>task.targetIds.includes(b.id));
  const mission=state.investigation?.consultations.find(c=>task.targetIds.includes(c.id));
  const ids=new Set([...task.targetIds,...(branch?[...branch.supporting,...branch.opposing]:[]),...(mission?.findingIds||[]),
    ...(['connect','revise'].includes(task.kind)?state.investigation?.selectedFindingIds||[]:[])]);
  const dependencies=state.findings.filter(f=>ids.has(f.id)).flatMap(f=>f.spanIds);
  const answerSpans=state.questions.filter(q=>task.targetIds.includes(q.id)).flatMap(q=>[...q.spanIds,...q.answerSpanIds]);
  const changed=['revise','connect'].includes(task.kind)?state.sources.filter(s=>state.changedSourceIds.includes(s.id)).flatMap(s=>s.spans.map(p=>p.id)):[];
  return [...new Set([...task.requiredSpanIds,...dependencies,...answerSpans,...changed])].filter(id=>all.some(s=>s.id===id));
}

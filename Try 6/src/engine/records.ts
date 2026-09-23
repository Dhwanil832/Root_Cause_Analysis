import type { z } from 'zod';
import type { findingSchema, questionSchema } from './contracts';
import type { EngineQuestion, EngineState, EngineTask, Finding } from './types';
import { normalize, overlap } from './identity';
import { invalidateReview } from './review/interpretation';
import { bindCommentary } from './citations';

export type References = { sources: Map<string, string>; findings: Map<string, string>; questions: Map<string, string> };
export function resolve(refs: string[], map: Map<string, string>) {
  const invalid = refs.filter(r => !map.has(r));
  if (invalid.length) throw new Error(`Unknown task-local references: ${invalid.join(', ')}`);
  return [...new Set(refs.map(r => map.get(r)!))];
}
export function quarantine(state: EngineState, task: EngineTask, item: unknown, error: unknown) {
  state.quarantine.push({ taskId: task.id, reason: error instanceof Error ? error.message : String(error), item });
}
/** Optional question rejection must not invalidate successfully extracted facts.
 * Keep the rejection visible; it never becomes an executable question. */
export function onlyQuestionRejections(items:EngineState['quarantine']) {
  return items.length>0&&items.every(({item})=>!!item&&typeof item==='object'&&'text' in item&&'intent' in item&&'decision' in item&&!('statement' in item));
}
export function findingText(f: Pick<Finding, 'statement' | 'subject' | 'predicate' | 'location' | 'time' | 'qualifiers'>) {
  return `${f.statement} ${f.subject} ${f.predicate} ${f.location} ${f.time} ${f.qualifiers}`;
}
export function relatedFindings(state: EngineState, query: string, omit: string[] = []) {
  return state.findings.filter(f => !omit.includes(f.id)).map(f => ({ f, score: overlap(query, findingText(f)) }))
    .filter(x => x.score > 0).sort((a, b) => b.score - a.score || a.f.id.localeCompare(b.f.id)).map(x => x.f);
}
export function ingestFinding(state: EngineState, task: EngineTask, row: z.infer<typeof findingSchema>, refs: References) {
  const spanIds = resolve(row.references, refs.sources);
  if (!row.statement.trim()) throw new Error('A finding needs a nonblank proposition.');
  if (!spanIds.length && !['hypothesis', 'context'].includes(row.kind)) throw new Error('An evidence finding requires original source references.');
  const replaceId = row.replaces ? refs.findings.get(row.replaces) : null;
  if (row.replaces && !replaceId) throw new Error('Replacement finding is outside the task context.');
  const sameOriginal = state.investigation && task.kind === 'read' ? state.findings.find(f => normalize(f.statement) === normalize(row.statement)
    && f.spanIds.length === spanIds.length && f.spanIds.every(id => spanIds.includes(id)) && f.kind === row.kind) : undefined;
  if (sameOriginal && !replaceId) return sameOriginal.id;
  const prior = state.findings.find(f => f.id === replaceId) || state.findings.find(f =>
    normalize(f.statement) === normalize(row.statement) && normalize(f.subject) === normalize(row.subject)
    && normalize(f.location) === normalize(row.location) && normalize(f.time) === normalize(row.time) && f.kind === row.kind);
  if (prior) {
    prior.owners = [...new Set([...prior.owners, task.owner])];
    prior.tags = [...new Set([...prior.tags, ...row.tags])];
    const newEvidence = spanIds.some(id => !prior.spanIds.includes(id));
    if (prior.statement !== row.statement || newEvidence) {
      if(prior.statement!==row.statement)delete prior.interpretation;
      prior.history.push({ revision: prior.revision, statement: prior.statement, reason: `Updated by ${task.kind} with source references; review invalidated.` });
      prior.revision++; prior.updatedVersion = state.version;
      if(prior.humanStatus==='accepted')prior.humanStatus='reopened';
      Object.assign(prior, { statement: row.statement, subject: row.subject, predicate: row.predicate, location: row.location,
        time: row.time, unit: row.unit, qualifiers: bindCommentary(row.qualifiers,refs), spanIds: [...new Set([...prior.spanIds, ...spanIds])],
        status: 'proposed', reviewExecution:'unreviewed', reviewReason: '', opposedBy: [], reviewAssessment: undefined, causalRole: undefined, causalRelevance: undefined });
      invalidateReview(prior,'unreviewed','Claim or cited evidence changed; review pending.',state);
      state.changes.push({ targetId: prior.id, kind: 'revised', reason: 'Proposition or cited evidence changed.' });
    }
    return prior.id;
  }
  const finding: Finding = { id: crypto.randomUUID(), revision: 1, statement: row.statement, kind: row.kind,
    subject: row.subject, predicate: row.predicate, location: row.location, time: row.time, unit: row.unit,
    qualifiers: bindCommentary(row.qualifiers,refs), spanIds, tags: row.tags, owners: [task.owner], status: 'proposed', reviewReason: '',
    opposedBy: [], history: [], introducedVersion: state.version, updatedVersion: state.version };
  state.findings.push(finding);
  state.changes.push({ targetId: finding.id, kind: 'added', reason: `${task.kind}: new proposition pending review.` });
  return finding.id;
}
export function ingestQuestion(state: EngineState, task: EngineTask, row: z.infer<typeof questionSchema>, refs: References) {
  const spanIds = resolve(row.references, refs.sources);
  row = { ...row, text: bindCommentary(row.text, refs), intent: bindCommentary(row.intent, refs), decision: bindCommentary(row.decision, refs) };
  if (!row.text.trim() || !row.decision.trim()) throw new Error('A question must identify a concrete decision it can inform.');
  const prior = state.questions.find(q => normalize(q.text) === normalize(row.text) && normalize(q.subject) === normalize(row.subject)
    && normalize(q.location) === normalize(row.location) && normalize(q.time) === normalize(row.time));
  if (prior) { prior.owners = [...new Set([...prior.owners, task.owner])]; prior.spanIds = [...new Set([...prior.spanIds, ...spanIds])]; return prior.id; }
  const question: EngineQuestion = { id: crypto.randomUUID(), text: row.text, intent: row.intent, decision: row.decision,
    subject: row.subject, location: row.location, time: row.time, owners: [task.owner], spanIds, status: 'open', answer: '',
    answerSpanIds: [], findingIds: [], coveredBy: null, reason: '', searchedSpanIds: [], inventory: '' };
  state.questions.push(question); return question.id;
}
export function ingestRows(state: EngineState, task: EngineTask, output: { findings?: z.infer<typeof findingSchema>[]; questions?: z.infer<typeof questionSchema>[] }, refs: References) {
  const ids: string[] = [];
  for (const row of output.findings || []) try { ids.push(ingestFinding(state, task, row, refs)); } catch (error) { quarantine(state, task, row, error); }
  for (const row of output.questions || []) try { ingestQuestion(state, task, row, refs); } catch (error) { quarantine(state, task, row, error); }
  return ids;
}

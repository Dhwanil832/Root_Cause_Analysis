import type { EngineState, EngineTask } from '../types';
import type { References } from '../records';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import { activeBoardFindings } from './usability';

export function investigationBase(state: EngineState, task: EngineTask) {
  const refs: References = { sources: new Map(), findings: new Map(), questions: new Map() };
  // One compact notebook, no raw traces, repeated generated prose, or prior boards.
  // Context planner fails explicitly rather than silently truncating this notebook.
  // Retain IDs of observations whose sources were removed: the map must be able
  // to explicitly retire them, without treating their old wording as evidence.
  const findings = state.findings;
  findings.forEach((f, i) => refs.findings.set(`F${i + 1}`, f.id));
  const fact = (id: string) => [...refs.findings].find(([, value]) => value === id)?.[0];
  const questions = state.questions.filter(q => state.investigation?.directions.some(d => d.questionId === q.id));
  questions.forEach((q, i) => refs.questions.set(`Q${i + 1}`, q.id));
  const base: Record<string, unknown> = {
    task: task.kind, owner: task.owner, taxonomy: TAG_LABELS,
    incidentContext: { focalEvent: state.focalEvent, summary: state.summary },
    boardNodes: activeBoardFindings(state).map(f => ({ ref: fact(f.id), statement: f.statement,
      type: state.propositions.find(p => p.findingId === f.id)?.type, evidenceStatus: f.status })),
    notebook: findings.map((f, i) => ({ ref: `F${i + 1}`, statement: f.statement, kind: f.kind,
      scope: [...new Set([f.subject, f.location, f.time].filter(v => v && !f.statement.toLowerCase().includes(v.toLowerCase())))].join(' · '), evidenceStatus: f.status,
      changedThisVersion: state.investigation?.changedFindingIds.includes(f.id),
      sourceAvailable: f.spanIds.length > 0,
      sourceLabels: [...new Set(state.sources.filter(s => s.spans.some(p => f.spanIds.includes(p.id))).map(s => s.label))] })),
    sourceInventory: state.sources.map(s => ({ label: s.label, scope: s.scope, changed: state.changedSourceIds.includes(s.id), limitations: s.limitations })),
    priorPosition: state.investigation ? {
      summary: state.investigation.summary,
      branches: state.investigation.branches.map(b => ({ ...b, supporting: b.supporting.map(fact).filter(Boolean), opposing: b.opposing.map(fact).filter(Boolean) })),
      selectedFindings: state.investigation.selectedFindingIds.map(fact).filter(Boolean),
      nodeRequests: state.investigation.nodeRequests?.map(r => ({ finding: fact(r.findingId), reason: r.reason })),
      rejectedConnections: state.investigation.rejectedConnections?.map(r => ({ from: fact(r.fromFindingId) || r.fromFindingId,
        to: fact(r.toFindingId) || r.toFindingId, rationale: r.rationale, rejection: r.reason })),
      connections: state.relationships.filter(e => e.proposedBy?.length).map(e => ({ id: e.id,
        from: e.from === 'focal' ? 'EVENT' : fact(state.propositions.find(p => p.id === e.from)?.findingId || ''),
        to: e.to === 'focal' ? 'EVENT' : fact(state.propositions.find(p => p.id === e.to)?.findingId || ''),
        type: e.type, rationale: e.rationale, gap: e.gap, status: e.status })),
      consultations: state.investigation.consultations.map(c => ({ ...c, findingIds: c.findingIds.map(fact).filter(Boolean) })),
      directions: state.investigation.directions.map(d => ({ ...d, questionId: [...refs.questions].find(([, id]) => id === d.questionId)?.[0] })),
    } : null,
    questions: questions.map((q, i) => ({ ref: `Q${i + 1}`, text: q.text, decision: q.decision,
      status: q.status, answer: q.answer, owners: q.owners, evidenceNeeded: q.reason,
      findingIds: q.findingIds.map(fact).filter(Boolean) })),
  };
  if (task.kind === 'consult') base.consultation = state.investigation?.consultations.find(c => c.id === task.targetIds[0]);
  if (task.kind === 'resolve') base.assignedQuestions = [...refs.questions].filter(([, id]) => task.targetIds.includes(id)).map(([ref]) => ref);
  return { base, refs };
}

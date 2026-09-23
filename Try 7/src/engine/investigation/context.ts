import type { EngineState, EngineTask } from '../types';
import type { References } from '../records';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import { activeBoardFindings } from './usability';
import {activeQuestion} from '../questions/ledger';

export function investigationBase(state: EngineState, task: EngineTask) {
  const refs: References = { sources: new Map(), findings: new Map(), questions: new Map() };
  // One compact notebook, no raw traces, repeated generated prose, or prior boards.
  // Context planner fails explicitly rather than silently truncating this notebook.
  // Retain IDs of observations whose sources were removed: the map must be able
  // to explicitly retire them, without treating their old wording as evidence.
  const findings = state.findings;
  findings.forEach((f, i) => refs.findings.set(`F${i + 1}`, f.id));
  const fact = (id: string) => [...refs.findings].find(([, value]) => value === id)?.[0];
  const questions = state.questions.filter(q => !q.coveredBy && activeQuestion(state,q));
  questions.forEach((q, i) => refs.questions.set(`Q${i + 1}`, q.id));
  const base: Record<string, unknown> = {
    task: task.kind, owner: task.owner, taxonomy: TAG_LABELS,
    incidentContext: { focalEvent: state.focalEvent, summary: state.summary },
    boardNodes: activeBoardFindings(state).map(f => ({ ref: fact(f.id), statement: f.statement,
      type: state.propositions.find(p => p.findingId === f.id)?.type, evidenceStatus: f.status,
      roleAssessment:state.propositions.find(p=>p.findingId===f.id)?.roleAssessment })),
    notebook: findings.map((f, i) => ({ ref: `F${i + 1}`, statement: f.statement, kind: f.kind,revision:f.revision,
      subject:f.subject,predicate:f.predicate,location:f.location,time:f.time,unit:f.unit,qualifiers:f.qualifiers,
      reviewExecution:f.reviewExecution,reviewReason:f.reviewReason,causalRole:f.causalRole,
      scope: [...new Set([f.subject, f.location, f.time].filter(v => v && !f.statement.toLowerCase().includes(v.toLowerCase())))].join(' · '), evidenceStatus: f.status,
      changedThisVersion: state.investigation?.changedFindingIds.includes(f.id),
      sourceAvailable: f.spanIds.length > 0,
      sourceLabels: [...new Set(state.sources.filter(s => s.spans.some(p => f.spanIds.includes(p.id))).map(s => s.label))] })),
    sourceInventory: state.sources.map(s => ({ label: s.label, scope: s.scope, changed: state.changedSourceIds.includes(s.id), limitations: s.limitations })),
    priorPosition: state.investigation ? {
      summary: state.investigation.summary,
      branches: state.investigation.branches.map(b => ({ ...b,conditions:b.conditions?.map(c=>({...c,findings:c.findings.map(fact).filter(Boolean)})), supporting: b.supporting.map(fact).filter(Boolean), opposing: b.opposing.map(fact).filter(Boolean) })),
      selectedFindings: state.investigation.selectedFindingIds.map(fact).filter(Boolean),
      nodeRequests: state.investigation.nodeRequests?.map(r => ({ finding: fact(r.findingId), reason: r.reason })),
      rejectedConnections: state.investigation.rejectedConnections?.map(r => ({ from: fact(r.fromFindingId) || r.fromFindingId,
        to: fact(r.toFindingId) || r.toFindingId, rationale: r.rationale, rejection: r.reason })),
      connections: state.relationships.filter(e => e.proposedBy?.length).map(e => ({ id: e.id,
        from: e.from === 'focal' ? 'EVENT' : fact(state.propositions.find(p => p.id === e.from)?.findingId || ''),
        to: e.to === 'focal' ? 'EVENT' : fact(state.propositions.find(p => p.id === e.to)?.findingId || ''),
        type: e.type, rationale: e.rationale, gap: e.gap, status: e.status,jointConditions:e.jointConditions?.map(fact),reviewReason:e.reviewReason,integrityIssues:e.integrityIssues })),
      consultations: state.investigation.consultations.map(c => ({ ...c, findingIds: c.findingIds.map(fact).filter(Boolean) })),
      directions: state.investigation.directions.map(d => ({ ...d, questionId: [...refs.questions].find(([, id]) => id === d.questionId)?.[0] })),
    } : null,
    questions: questions.map((q, i) => ({ ref: `Q${i + 1}`, text: q.text, decision: q.decision,
      status: q.status, answer: q.answer, owners: q.owners, evidenceNeeded: q.reason,
      subject:q.subject,location:q.location,time:q.time,parts:q.parts,coverage:q.coverage,subscriptions:q.subscriptions,
      answerRevision:q.answerRevision,answerSourceIds:q.answerSpanIds,deliveries:q.deliveries,
      findingIds: q.findingIds.map(fact).filter(Boolean) })),
  };
  if (task.kind === 'consult') base.consultation = state.investigation?.consultations.find(c => c.id === task.targetIds[0]);
  if (task.kind === 'resolve'||task.kind==='respond') base.assignedQuestions = [...refs.questions].filter(([, id]) => task.targetIds.includes(id)).map(([ref]) => ref);
  if(task.kind==='revise')base.impactTargets=task.targetIds.map(id=>({target:fact(id)||id,
    review:state.findings.find(f=>f.id===id)?.reviewAssessment,
    branch:state.investigation?.branches.find(b=>b.id===id)?.title}));
  return { base, refs };
}

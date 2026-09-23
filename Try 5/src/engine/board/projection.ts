import type { AgentId, AnalysisSnapshot, EvidenceStatus, InvestigationQuestion, TagId } from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import type { EngineInput, EngineState, EpistemicStatus, RunStatus } from '../types';
import { ENGINE_VERSION } from '../types';
import { exactCitation, spanMap } from '@/src/knowledge/sources/registry';
import { checkpointVersion } from '../tasks/checkpoint-version';

function status(s: EpistemicStatus): EvidenceStatus { return s === 'partial' ? 'partially-supported' : s === 'conflicting' ? 'unknown' : s; }
function stage(owner: string): AgentId { return owner === 'baseline' ? 'incident-understanding' : owner as AgentId; }
function ownerTag(owners: string[]): InvestigationQuestion['tagId'] {
  return owners.find(o => o in TAG_LABELS) as TagId || (owners.includes('causal-analysis') ? 'causal-analysis' : owners.includes('causal-verification') ? 'causal-verification' : 'baseline');
}
export function project(state: EngineState, input: EngineInput, execution: RunStatus): AnalysisSnapshot {
  const spans = spanMap(state.sources);
  const citations = (ids: string[]) => ids.flatMap(id => spans.has(id) ? [exactCitation(spans.get(id)!)] : []);
  const sourceIds = (ids: string[]) => [...new Set(ids.flatMap(id => spans.has(id) ? [spans.get(id)!.sourceId] : []))];
  const questions: InvestigationQuestion[] = state.questions.filter(q => !q.coveredBy).map(q => ({
    id: q.id, tagId: ownerTag(q.owners), proposedBy: stage(q.owners[0]), routedTo: q.owners.filter(o => o in TAG_LABELS) as TagId[],
    text: q.text, intent: q.intent, rationale: q.reason || q.decision, evidenceNeeded: [q.decision], decisionUnlocked: q.decision,
    citations: citations(q.spanIds), priority: 'medium', status: q.status === 'partial' ? 'partially-answered' : q.status === 'conflicting' ? 'contradicted' : q.status,
  }));
  const nodes = state.propositions.map(p => ({ id: p.id, type: p.type, label: p.label, detail: p.detail, status: status(p.status),
    sourceIds: sourceIds(p.spanIds), specialistIds: state.findings.find(f => f.id === p.findingId)?.tags || [],
    verified: p.status === 'supported', claimIds: [p.findingId], assessmentKind: state.findings.find(f => f.id === p.findingId)?.kind === 'hypothesis' ? 'hypothesis' as const : 'observation' as const,
    humanStatus: p.humanStatus }));
  const ids = new Set(['focal', ...nodes.map(n => n.id)]);
  const edges = state.relationships.filter(e => ids.has(e.from) && ids.has(e.to)).map(e => ({ id: e.id, from: e.from, to: e.to, type: e.type,
    rationale: e.rationale, status: status(e.status), sourceIds: sourceIds(e.spanIds), claimIds: e.findingIds,
    counterfactual: e.counterfactual, competingExplanation: e.alternative, evidenceGap: e.gap, verified: e.status === 'supported' }));
  const findings = [...state.propositions, ...state.relationships].filter(p => p.status !== 'supported').map(p => ({
    id: `review:${p.id}`, targetId: p.id, severity: 'important' as const,
    issue: p.reviewReason || 'Proposed; semantic review is pending or unresolved.', evidenceNeeded: 'Evidence for the stated proposition and mechanism.' }));
  const failed = state.tasks.filter(t => t.status === 'failed' || t.status === 'blocked');
  const open = questions.filter(q => q.status !== 'answered');
  const conflicts = state.findings.flatMap<AnalysisSnapshot['conflicts'][number]>(f=>f.reviewAssessment?.evidenceConflicts
    ? f.reviewAssessment.evidenceConflicts.map((c,i)=>({id:`conflict:${f.id}:${i}`,summary:c.reason,claimIds:[f.id],status:c.status,
      scope:c.scope,resolutionNeeded:c.resolutionNeeded,sides:[c.sideA,c.sideB].map(side=>({assertion:side.assertion,citations:citations(side.spanIds),originalQuotes:side.quotes}))}))
    : f.status==='conflicting'?[{id:`conflict:${f.id}`,summary:f.reviewReason,claimIds:[f.id],status:'open' as const,resolutionNeeded:'Resolve the cited source disagreement.'}]:[]);
  return {
    status: conflicts.length ? 'contradictions-unresolved' : open.length ? 'awaiting-evidence' : 'causal-board-developing',
    structuredIncident: { summary: state.summary, focalEvent: state.focalEvent, normalState: state.normalState, eventState: state.eventState,
      actualImpact: '', potentialImpact: '', entities: state.entities.map((e, i) => ({ id: `entity:${i}`, name: e.name, description: e.description,
        type: 'other', status: 'proposed', sourceIds: sourceIds(e.spanIds) })), timeline: [], conditions: [], unknowns: open.map(q => q.text) },
    facts: state.findings.filter(f => f.status === 'supported').map(f => f.statement), unknowns: open.map(q => q.text),
    baselineQuestions: questions.filter(q => q.tagId === 'baseline'), questions: questions.filter(q => q.tagId !== 'baseline'),
    tags: state.tags.map(t => ({ id: t.id, label: TAG_LABELS[t.id], rationale: t.reason, evidence: sourceIds(t.spanIds), citations: citations(t.spanIds), confidence: 0 })),
    specialistKnowledgeBases: state.tags.map(t => ({ tagId: t.id, label: TAG_LABELS[t.id], summary: t.reason,
      findings: state.findings.filter(f => f.owners.includes(t.id)).map(f => ({ id: f.id, statement: f.statement,
        type: f.kind === 'hypothesis' ? 'hypothesis' : 'finding', status: status(f.status), sourceIds: sourceIds(f.spanIds) })),
      questionIds: state.questions.filter(q => q.owners.includes(t.id)).map(q => q.id), handoffs: [], updatedAt: new Date().toISOString() })),
    skippedQuestions: state.questions.filter(q => q.coveredBy).map(q => ({ id: q.id, text: q.text, intent: q.intent, proposedBy: ownerTag(q.owners),
      coveredByQuestionId: q.coveredBy!, coveredByTagId: ownerTag(state.questions.find(c => c.id === q.coveredBy)?.owners || []), reason: q.reason })),
    answers: input.answers,
    documentIntelligence: input.documents.map(d => {
      const source=state.sources.find(s=>s.id===d.id), visual=source?.spans.find(s=>s.modality);
      const read=visual&&state.tasks.some(t=>t.kind==='read'&&t.status==='completed'&&t.evidenceIds.includes(visual.id));
      return { documentId:d.id,title:d.title,fileName:d.fileName,contentType:d.contentType,
        mode:read?(visual!.modality==='image'?'vision':'file-vision'):d.extractedText?'embedded-text':'unavailable',documentType:d.contentType,summary:'',
        observations:visual?state.findings.filter(f=>f.spanIds.includes(visual.id)).map(f=>({id:f.id,documentId:d.id,text:f.statement,kind:'visual-feature' as const,
          location:f.location,confidence:0,status:f.humanStatus==='accepted'?'verified' as const:f.humanStatus==='rejected'?'rejected' as const:'proposed' as const,
          requiresVerification:f.humanStatus!=='accepted',routedTo:f.tags})):[],
        limitations:[...(source?.limitations||[]),...(visual?['Model visual interpretations are not verbatim source text. Human review is separate.']:[])],
        processedAt:d.createdAt,engine:read?input.model.id:'exact-source-registry',validation:read||d.extractionStatus==='ready'?'valid':'failed'};
    }),
    sourceAssessments: [], adjudicationConflicts: [],
    evidenceClaims: state.findings.map(f => ({ id: f.id, text: f.statement, kind: f.kind === 'hypothesis' ? 'inference' : f.kind === 'requirement' ? 'documented-requirement'
      : f.kind === 'measurement' ? 'measurement' : f.kind === 'testimony' ? 'testimony' : 'record', status: status(f.status), sourceIds: sourceIds(f.spanIds), routedTo: f.tags,
      interpretation:f.interpretation,reviewExecution:f.reviewExecution,scopeHistory:f.scopeHistory,
      review: f.reviewReason ? { verdict: f.status === 'supported' ? 'supported' : f.status === 'contradicted' ? 'contradicted' : f.status === 'partial' ? 'partial' : 'unsupported',
        reason: f.reviewReason, citations: citations(f.spanIds),
        claimParts: f.reviewAssessment ? { policy:f.reviewAssessment.policy,status:f.reviewAssessment.status,
          uncoveredText:f.reviewAssessment.uncoveredText,issues:f.reviewAssessment.issues,
          parts:f.reviewAssessment.parts.map(p=>({claimText:p.claimText,claimType:p.claimType,assertion:p.assertion,truthConditions:p.truthConditions,establishes:p.establishes,relation:p.relation,
            status:p.status,reason:p.reason,missingPremises:p.missingPremises,issues:p.issues,citations:citations(p.spanIds),
            counterexample:p.counterexample,originalQuotes:p.quotes})) } : undefined } : undefined })),
    conflicts,
    answerFetches: state.questions.filter(q => !q.coveredBy && (q.answer || q.reason)).map(q => ({ id: `answer:${q.id}`, questionId: q.id,
      status: q.status === 'answered' ? 'answered' : q.status === 'conflicting' ? 'conflicting' : q.status === 'partial' ? 'partial' : 'not-found',
      answer: q.answer, sourceIds: sourceIds(q.answerSpanIds), claimIds: q.findingIds, userRequest: q.reason,
      searched: [`${q.searchedSpanIds.length} original passages; selected retrieval is not an exhaustive absence check.`] })),
    causalBoard: { maturity: edges.length ? 'developing' : 'initial', focalNodeId: 'focal',
      nodes: [{ id: 'focal', type: 'focal-event', label: state.focalEvent || 'Incident account — understanding pending', detail: state.summary,
        status: 'proposed', sourceIds: ['incident-description'], specialistIds: [], verified: false }, ...nodes], edges, verificationFindings: findings,
      branchRevisions: state.changes.filter(c => c.kind !== 'added').map(c => ({ previousTargetId: c.targetId, previousLabel: c.targetId,
        action: c.kind === 'retained' ? 'keep' : c.kind === 'rejected' ? 'reject' : 'revise', reason: c.reason, replacementIds: [c.targetId], evidenceIds: [] })) },
    correctiveActions: state.actions, humanDecisions: state.decisions,
    trace: state.tasks.map(t => ({ id: t.id, stage: stage(t.owner), summary: t.error || (t.output as {decision?:{summary?:string}})?.decision?.summary || `${t.kind}: ${t.status}${t.reused ? ' (reused)' : ''}`,
      evidence: sourceIds(t.evidenceIds), unknowns: t.omittedEvidenceIds.length ? [`${t.omittedEvidenceIds.length} matching passages outside this working set.`] : [],
      alternatives: [], confidence: 0, promptVersion: t.engineVersion || input.engineVersion || ENGINE_VERSION, engine: input.model.id, durationMs: t.durationMs,
      validation: t.status === 'failed' || t.status === 'blocked' ? 'failed' : 'valid', reused: t.reused })),
    stageErrors: failed.map(t => ({ stage: stage(t.owner), message: t.error, recoverable: true })),
    revision: { added: state.changes.filter(c => c.kind === 'added').map(c => c.targetId), changed: state.changes.filter(c => c.kind === 'revised').map(c => c.targetId),
      resolved: [], reopened: state.propositions.filter(p => p.humanStatus === 'reopened').map(p => p.id) },
    documentIds: input.documents.map(d => d.id),
    engineProgress: { scopeNote: input.controlledUpdate?.reason, status: execution, phase: state.phase,pauseReason:state.pauseReason,model:{id:input.model.id,digest:input.model.digest,contextWindow:input.model.contextWindow,engineVersion:checkpointVersion(input,state)||'try5.1'},tasks: state.tasks.map(t => ({ id: t.id, kind: t.kind, owner: t.owner, status: t.status,traceId:t.traceId,
      target:t.targetIds.map(id=>state.questions.find(q=>q.id===id)?.text||state.findings.find(f=>f.id===id)?.statement||state.propositions.find(p=>p.id===id)?.label||spans.get(id)?.label||id).join(' · '),
      decision:(t.output as {decision?:{summary?:string}})?.decision?.summary||'',dependencies:t.dependsOn.length,
      attempts: t.attempts, error: t.error, reused: t.reused, inputTokens: t.inputTokens, outputTokens: t.outputTokens, durationMs: t.durationMs,
      contextBytes: t.contextBytes, evidenceCount: t.evidenceIds.length, omittedEvidenceCount: t.omittedEvidenceIds.length })),
      quarantineCount: state.quarantine.length, quarantine:state.quarantine.map(q=>({taskId:q.taskId,reason:q.reason})),changes: state.changes,
      sourceCoverage: state.sources.map(s => ({ id: s.id, label: s.label, spans: s.spans.length, limitations: s.limitations,
        readSpans:s.spans.filter(p=>state.tasks.some(t=>t.kind==='read'&&t.status==='completed'&&t.targetIds.includes(p.id))).length })) },
  };
}

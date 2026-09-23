import { readSchema, understandSchema, tagSchema } from '@/src/engine/contracts';
import { assessLiteralClaim, preserveReviewGaps } from '@/src/engine/review/literal-decision';
import { interpretClaim, invalidateReview } from '@/src/engine/review/interpretation';
import { ingestRows, resolve, quarantine, type References } from '@/src/engine/records';
import type { EngineState, EngineTask } from '@/src/engine/types';
import { bindCommentary } from '@/src/engine/citations';

export function applyEvidenceTask(state: EngineState, task: EngineTask, raw: unknown, refs: References) {
  if(task.kind==='interpret') {
    const finding=state.findings.find(f=>f.id===task.targetIds[0]);
    if(!finding)throw new Error('Interpretation target no longer exists.');
    finding.interpretation=interpretClaim(finding.statement,raw);
    return;
  }
  if (task.kind === 'read' || task.kind === 'specialist') {
    const out = readSchema.parse(raw);
    if (task.kind === 'read' && state.investigation) {
      // Preserve unsolicited reader questions as notes, not executable work.
      state.investigation.readingNotes.push(...out.questions.map(q => ({ text: q.text, taskId: task.id })));
      return ingestRows(state, task, { findings: out.findings }, refs);
    }
    return ingestRows(state, task, out, refs);
  }
  if (task.kind === 'understand') {
    const out = understandSchema.parse(raw);
    state.summary = out.summary; state.focalEvent = out.focalEvent || state.focalEvent;
    state.normalState = out.normalState; state.eventState = out.eventState;
    for (const entity of out.entities) try {
      const spanIds = resolve(entity.references, refs.sources);
      const old = state.entities.find(e => e.name.toLowerCase() === entity.name.toLowerCase());
      if (old) Object.assign(old, { description: entity.description, spanIds });
      else state.entities.push({ name: entity.name, description: entity.description, spanIds });
    } catch(error) {quarantine(state,task,entity,error);}
    ingestRows(state, task, out, refs);
  }
  if (task.kind === 'tag') {
    const out = tagSchema.parse(raw);
    for (const row of out.tags) try {
      const spanIds = resolve(row.references, refs.sources);
      const prior = state.tags.find(t => t.id === row.id);
      if (prior) { prior.reason = row.reason; prior.spanIds = [...new Set([...prior.spanIds, ...spanIds])]; }
      else state.tags.push({ ...row, spanIds });
      for(const f of state.findings.filter(f=>task.targetIds.includes(f.id)&&f.spanIds.some(id=>spanIds.includes(id))))
        f.tags=[...new Set([...f.tags,row.id])];
    } catch(error) {quarantine(state,task,row,error);}
  }
  if (task.kind === 'review') {
    const finding = state.findings.find(f => f.id === task.targetIds[0]);
    if (!finding) throw new Error('Review target no longer exists.');
    let result;
    try { result=assessLiteralClaim(state,finding,raw,refs); }
    catch(error) {
      invalidateReview(finding,'incomplete',`Review incomplete: ${error instanceof Error?error.message:String(error)}`,state);
      task.producedIds=preserveReviewGaps(state,task,finding,raw,refs,true);
      throw error;
    }
    const {out,assessment,reason,causalRole,causalRelevance,supporting,opposing}=result;
    finding.status=assessment.status; finding.reviewAssessment=assessment;
    delete finding.interpretation;
    finding.reviewExecution='complete';
    finding.reviewReason=bindCommentary(reason,refs); finding.opposedBy=opposing;
    finding.scopeHistory ||= [];
    if (!finding.scopeHistory.some(s=>s.taskId===task.id&&s.revision===finding.revision))
      finding.scopeHistory.push({ revision:finding.revision, taskId:task.id, claimType:out.claimType });
    finding.causalRole=causalRole; finding.causalRelevance=causalRelevance;
    finding.spanIds = [...new Set([...finding.spanIds, ...supporting, ...opposing])];
    ingestRows(state, task, out, refs);
    preserveReviewGaps(state,task,finding,raw,refs,false);
    if (!task.reused) state.changes.push({ targetId: finding.id, kind: 'rechecked', reason:finding.reviewReason });
  }
}

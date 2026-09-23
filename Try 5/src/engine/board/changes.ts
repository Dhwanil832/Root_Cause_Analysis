import { actionsSchema, causalSchema, reviewSchema } from '../contracts';
import { ingestRows, quarantine, resolve, type References } from '../records';
import type { EngineState, EngineTask } from '../types';
import { bindCommentary } from '../citations';
import { applyInquiry } from '../inquiry/apply';

export const focalId = 'focal';
export const propositionId = (findingId: string) => `proposition:${findingId}`;
export function applyBoardTask(state: EngineState, task: EngineTask, raw: unknown, refs: References) {
  if (task.kind === 'inquiry') return applyInquiry(state,task,raw,refs);
  if (task.kind === 'causal') {
    const out = causalSchema.parse(raw), finding = state.findings.find(f => f.id === task.targetIds[0]);
    if (!finding) throw new Error('Causal task target does not exist.');
    const spans = [...new Set([...finding.spanIds,...resolve(out.references, refs.sources)])], id = propositionId(finding.id);
    const prior = state.propositions.find(p => p.id === id);
    for (const edge of state.relationships.filter(e => e.proposedBy?.includes(finding.id))) {
      edge.proposedBy = edge.proposedBy!.filter(owner => owner !== finding.id);
      if (!edge.proposedBy.length) { edge.status = 'unknown'; edge.reviewReason = 'Previous proposal withdrawn pending this revision’s evidence review.'; }
    }
    if (out.disposition === 'node') {
      const next = { id, findingId: finding.id, type: out.type, label: finding.statement,
        detail: '', spanIds: spans, status: 'proposed' as const, reviewReason: '',
        proposedWording: { label: bindCommentary(out.label,refs), detail: bindCommentary(out.detail,refs), taskId:task.id },
        humanStatus: prior?.humanStatus === 'accepted' && (prior.detail !== '' || prior.label !== finding.statement
          || spans.some(s=>!prior.spanIds.includes(s))) ? 'reopened' as const : prior?.humanStatus || 'unreviewed' as const };
      state.changes.push({targetId:id,kind:prior?'revised':'added',reason:bindCommentary(out.reason,refs)||'Causal proposition submitted for independent task review.'});
      if (prior) Object.assign(prior, next); else state.propositions.push(next);
      // Relationships are superseded only for this proposal's own outgoing/incoming suggestions.
      for (const edge of out.edges) try {
        const fromFinding = edge.from === 'EVENT' ? 'EVENT' : refs.findings.get(edge.from);
        const toFinding = edge.to === 'EVENT' ? 'EVENT' : refs.findings.get(edge.to);
        if (!fromFinding || !toFinding || fromFinding === toFinding) throw new Error('Invalid or self-referential relationship.');
        if (![fromFinding, toFinding].includes(finding.id)) throw new Error('Relationship must involve this task target.');
        if (edge.type !== 'preceded' && (!edge.counterfactual.trim() || !edge.alternative.trim())) throw new Error('Causal relationship needs a counterfactual and competing explanation.');
        const from = fromFinding === 'EVENT' ? focalId : propositionId(fromFinding), to = toFinding === 'EVENT' ? focalId : propositionId(toFinding);
        const edgeId = `${from}>${edge.type}>${to}`;
        const record = { id: edgeId, from, to, type: edge.type, rationale: bindCommentary(edge.rationale,refs), counterfactual: bindCommentary(edge.counterfactual,refs),
          alternative: bindCommentary(edge.alternative,refs), gap: bindCommentary(edge.gap,refs), spanIds: resolve(edge.references, refs.sources),
          findingIds: [fromFinding, toFinding].filter(f => f !== 'EVENT'), proposedBy: [finding.id], status: 'proposed' as const, reviewReason: '' };
        const old = state.relationships.find(e => e.id === edgeId);
        state.changes.push({targetId:edgeId,kind:old?'revised':'added',reason:record.rationale});
        if (old) Object.assign(old, record, { proposedBy: [...new Set([...(old.proposedBy || []), finding.id])] }); else state.relationships.push(record);
      } catch (error) { quarantine(state, task, edge, error); }
    } else if (prior) {
      prior.status = 'unknown'; prior.reviewReason = bindCommentary(out.reason,refs);
      state.changes.push({targetId:prior.id,kind:'rejected',reason:prior.reviewReason||'Not retained as a causal proposition; history is preserved.'});
      if (prior.humanStatus === 'accepted') prior.humanStatus = 'reopened';
    }
    ingestRows(state, task, out, refs);
  } else if (task.kind === 'verify') {
    const out = reviewSchema.parse(raw);
    const target = state.propositions.find(p => p.id === task.targetIds[0]) || state.relationships.find(e => e.id === task.targetIds[0]);
    if (!target) throw new Error('Verification target is missing.');
    const supporting = resolve(out.supporting, refs.sources), opposing = resolve(out.opposing, refs.sources);
    target.status = supporting.length && opposing.length ? 'conflicting' : out.status === 'supported' && !supporting.length ? 'unknown' : out.status;
    target.reviewReason = bindCommentary(out.reason,refs);
    const premises = 'findingId' in target ? [target.findingId] : target.findingIds;
    if (target.status === 'supported' && premises.some(id => state.findings.find(f => f.id === id)?.status !== 'supported')) {
      target.status = 'unknown'; target.reviewReason += ' Underlying findings are not all independently supported.';
    }
    if ('proposedBy' in target && !target.proposedBy?.length) {
      target.status = 'unknown'; target.reviewReason += ' No current proposal owns this relationship.';
    }
    if ('from' in target && target.status==='supported' && [target.from,target.to].some(id=>id!==focalId
      && state.propositions.find(p=>p.id===id)?.status!=='supported')) {
      target.status='unknown';target.reviewReason+=' One or more endpoint propositions lack support.';
    }
    target.spanIds = [...new Set([...target.spanIds, ...supporting, ...opposing])];
    if ('humanStatus' in target && target.humanStatus === 'accepted' && target.status !== 'supported') target.humanStatus = 'reopened';
    ingestRows(state, task, out, refs);
  } else {
    const out = actionsSchema.parse(raw);
    state.actions = state.actions.filter(a => !a.causalTargetIds.includes(task.targetIds[0]));
    state.actions.push(...out.actions.map(a => ({ ...a, id: crypto.randomUUID(), causalTargetIds: [task.targetIds[0]], status: 'proposed' as const })));
  }
}

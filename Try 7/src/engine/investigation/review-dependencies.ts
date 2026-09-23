import type { EngineState } from '../types';

/** Active map dependencies, not the union of every premise ever proposed.
 * Keep sourceless nodes addressable until explicit retirement; this is not an
 * evidence verdict and does not turn missing evidence into a supported claim. */
export function currentBoardPremiseIds(state: EngineState) {
  const selected = new Set(state.investigation?.selectedFindingIds || []);
  return [...new Set([
    ...state.propositions.filter(p => selected.has(p.findingId)).map(p => p.findingId),
    ...state.relationships.filter(e => e.proposedBy?.length).flatMap(e => e.findingIds),
  ])];
}

export function retireObsoleteQueuedReviews(state: EngineState) {
  if (!state.investigation) return;
  const required = new Set(currentBoardPremiseIds(state));
  for (const task of state.tasks.filter(t => t.kind === 'review' && t.status === 'queued'
    && t.targetIds.every(id => !required.has(id)))) {
    task.status = 'superseded';
    task.error = 'Not executed: no active board node or connection uses this premise. Original observation and previous results retained.';
    task.completedAt = new Date().toISOString();
    state.changes.push({targetId: task.id, kind: 'revised', reason: task.error});
  }
  // The active selection mirrors the current graph. The full source notebook,
  // prior calls, completed reviews and findings are never pruned or rewritten.
  state.investigation.selectedFindingIds = [...required];
}

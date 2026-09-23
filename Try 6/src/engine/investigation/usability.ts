import type { EngineState } from '../types';

/** Publication dependencies need a usable position, not universal acceptance of
 * every proposal. Structural usefulness is NOT factual or causal verification. */
export function activeBoardFindings(state: EngineState) {
  const selected = new Set(state.investigation?.selectedFindingIds || []);
  return state.propositions.filter(p => selected.has(p.findingId)).flatMap(p => {
    const f = state.findings.find(f => f.id === p.findingId);
    return f && f.kind !== 'hypothesis' && f.spanIds.length ? [f] : [];
  });
}
export function hasUsablePosition(state: EngineState) {
  if (!state.summary.trim() || !state.focalEvent.trim()) return false;
  if (activeBoardFindings(state).length) return true;
  // A concrete foundation question is legitimate when the mechanism is unknown.
  return !!state.investigation?.directions.some(d => d.branchIds.some(id => state.investigation!.branches.some(b => b.id === id))
    && state.questions.some(q => q.id === d.questionId && q.text.trim() && q.decision.trim()));
}

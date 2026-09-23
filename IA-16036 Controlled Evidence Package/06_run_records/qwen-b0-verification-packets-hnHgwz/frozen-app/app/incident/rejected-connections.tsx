import type { RejectedCausalEdge } from '@/src/domain/types';

/** Read-only audit view. These proposals are never drawn as active links. */
export function RejectedConnections({ edges = [] }: { edges?: RejectedCausalEdge[] }) {
  if (!edges.length) return null;
  return <section className="edge-review-list">
    <h3>Rejected connection proposals ({edges.length})</h3>
    <p>Excluded from the active board. These rejections do not invalidate the endpoint facts or unrelated branches. Original proposals are preserved for review; they are not established causes.</p>
    {edges.map(edge => <article key={edge.id}>
      <strong>{edge.fromLabel} → {edge.toLabel}</strong>
      <p><b>Rejected:</b> {edge.reasons.join(' ')}</p>
      <details><summary>Original model proposal</summary>
        <p>Proposed relationship: {edge.proposal.type} · Proposed status: {edge.proposal.status}</p>
        <p>{edge.proposal.rationale}</p>
        <p><b>Counterfactual:</b> {edge.proposal.counterfactual || 'Not supplied'}</p>
        <p><b>Competing explanation:</b> {edge.proposal.competingExplanation || 'Not supplied'}</p>
        <p><b>Evidence gap:</b> {edge.proposal.evidenceGap || 'Not supplied'}</p>
        <p><b>Source references:</b> {edge.proposal.sourceIds.join(', ') || 'Not supplied'}</p>
        <p><b>Claim references:</b> {edge.proposal.claimIds.join(', ') || 'Not supplied'}</p>
        <small>{edge.id} · {edge.proposal.fromKey} → {edge.proposal.toKey}</small>
      </details>
    </article>)}
  </section>;
}

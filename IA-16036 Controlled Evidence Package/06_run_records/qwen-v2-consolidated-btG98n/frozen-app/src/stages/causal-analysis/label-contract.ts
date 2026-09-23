import type { CausalBoard } from '../../domain/types';

// Formatting only. Never rewrite the factual proposition or its evidence status.
const categoryPrefix = /^(?:focal[ -]event|event|condition|barrier|impact|change|human[ -]decision[ -]action|direct[ -]cause|contributing[ -]cause|root[ -]cause[ -]candidate|corrective[ -]action|evidence|unknown)\s*:\s*/i;

export function cleanCausalLabel(label: string) {
  let clean = label.trim();
  while (categoryPrefix.test(clean)) clean = clean.replace(categoryPrefix, '').trim();
  if (!clean) throw new Error('A causal node needs a proposition, not just a category.');
  return clean;
}

export function previousBoardContext(board?: CausalBoard | null) {
  if (!board) return null;
  return {
    authority: 'Previous model interpretation, not a source or a formatting example. Reassess against current evidence.',
    focalNodeId: board.focalNodeId,
    nodes: board.nodes.map(node => ({ id: node.id, type: node.type,
      label: cleanCausalLabel(node.label), status: node.status, sourceIds: node.sourceIds })),
    edges: board.edges.map(edge => ({ id: edge.id, from: edge.from, to: edge.to,
      type: edge.type, status: edge.status, claimIds: edge.claimIds, sourceIds: edge.sourceIds })),
    archive: { verificationFindingCount: board.verificationFindings?.length || 0,
      rejectedProposalCount: board.rejectedEdges?.length || 0,
      instruction: 'Full records remain stored. Retrieve a prior target by ID for its detail and unresolved review issues. Rejected proposals are audit history, not active causes.' },
  };
}

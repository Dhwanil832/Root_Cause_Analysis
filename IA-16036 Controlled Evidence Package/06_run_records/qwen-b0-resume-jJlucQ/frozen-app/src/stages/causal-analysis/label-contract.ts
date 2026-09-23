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
    ...board,
    nodes: board.nodes.map(node => ({ ...node, label: cleanCausalLabel(node.label) })),
  };
}

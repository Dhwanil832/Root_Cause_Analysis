import type { CausalBoard } from '../../domain/types';

interface VerificationOutput {
  verifiedNodeKeys: string[];
  verifiedEdgeIndexes: number[];
  findings: Array<{ targetKey: string; severity: string }>;
}

export function verificationTargets(board: CausalBoard, keyToId: Map<string, string>) {
  // The verifier sees board IDs. Accept legacy model-local keys as aliases only
  // when they resolve to an actual node, never to an arbitrary invented target.
  const targets = new Map([...board.nodes, ...board.edges].map(item => [item.id, item.id]));
  for (const [key, id] of keyToId) if (board.nodes.some(node => node.id === id)) targets.set(key, id);
  return targets;
}

export function verificationReferenceProblems(output: VerificationOutput, board: CausalBoard, keyToId: Map<string, string>) {
  const targets = verificationTargets(board, keyToId);
  const nodes = new Set(board.nodes.map(node => node.id));
  const problems: string[] = [];
  for (const key of output.verifiedNodeKeys) {
    if (!nodes.has(targets.get(key) || '')) problems.push(`Unknown verified node ${key}. Use a node.id from the supplied board.`);
  }
  for (const index of output.verifiedEdgeIndexes) {
    if (!Number.isInteger(index) || index < 0 || index >= board.edges.length) problems.push(`Invalid edge index ${index}. Use zero-based indexes into the supplied board.edges.`);
  }
  for (const finding of output.findings) {
    if (!targets.has(finding.targetKey)) problems.push(`Unknown finding target ${finding.targetKey}. Use an existing board node.id or edge.id.`);
  }
  return problems;
}

export function verifiedTargetSets(output: VerificationOutput, board: CausalBoard, keyToId: Map<string, string>) {
  const problems = verificationReferenceProblems(output, board, keyToId);
  if (problems.length) throw new Error(problems.join('; '));
  const targets = verificationTargets(board, keyToId);
  const blocked = new Set(output.findings.filter(f => f.severity === 'blocking').map(f => targets.get(f.targetKey)!));
  return {
    targets,
    nodes: new Set(output.verifiedNodeKeys.map(key => targets.get(key)!).filter(id => !blocked.has(id))),
    // A blocking finding wins over a conflicting verification flag. Preserve
    // both raw model statements for review, but never mark that target verified.
    edges: new Set(output.verifiedEdgeIndexes.filter(index => {
      const edge = board.edges[index];
      return !blocked.has(edge.id) && !blocked.has(edge.from) && !blocked.has(edge.to);
    })),
  };
}

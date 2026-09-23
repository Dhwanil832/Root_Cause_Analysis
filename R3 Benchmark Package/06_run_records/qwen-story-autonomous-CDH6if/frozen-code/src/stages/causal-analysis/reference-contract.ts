interface GraphOutput {
  focalKey: string;
  nodes: Array<{ key: string; type: string; label: string }>;
  edges: Array<{ fromKey: string; toKey: string }>;
}

/** Never guess which event the model meant, or silently discard broken edges. */
export function causalReferenceProblems(output: GraphOutput): string[] {
  const keys = new Set<string>();
  const problems: string[] = [];
  for (const node of output.nodes) {
    if (!node.key.trim() || keys.has(node.key)) problems.push(`Node key ${JSON.stringify(node.key)} is empty or duplicated. Use unique nonempty keys.`);
    if (!node.label.trim()) problems.push(`Node ${node.key} has an empty proposition.`);
    keys.add(node.key);
  }
  const focal = output.nodes.find(node => node.key === output.focalKey);
  if (!focal) {
    problems.push(`focalKey ${JSON.stringify(output.focalKey)} does not match any nodes[].key. Select the existing incident node key. Available keys: ${[...keys].join(', ')}. Do not copy a timeline/entity ID.`);
  } else if (!['focal-event', 'event'].includes(focal.type)) {
    problems.push('The focal node must be the incident event, not a condition or barrier.');
  }
  for (const edge of output.edges) {
    if (!keys.has(edge.fromKey) || !keys.has(edge.toKey)) {
      problems.push(`Edge ${edge.fromKey} -> ${edge.toKey} refers to a nonexistent node. Both keys must match nodes[].key exactly.`);
    }
  }
  return problems;
}

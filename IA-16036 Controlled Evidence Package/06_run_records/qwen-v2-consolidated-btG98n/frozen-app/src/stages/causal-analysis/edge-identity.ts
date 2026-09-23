import type { CausalAnalysisOutput } from '@/src/domain/schemas';
type Edge = CausalAnalysisOutput['edges'][number];
/** One active relationship per ordered endpoints/type. Preserve variants in
 * the returned audit instead of counting repeated wording as new support. */
export function coalesceEdges(proposals: Edge[]) {
  const groups = new Map<string, Edge[]>();
  for (const edge of proposals) {
    const key = `${edge.fromKey}:${edge.toKey}:${edge.type}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(edge);
  }
  const active: Edge[] = [], rejected: Edge[] = [], variants = [];
  for (const [key, rows] of groups) {
    const retained = rows.filter(e => !['rejected', 'contradicted'].includes(e.status));
    rejected.push(...rows.filter(e => ['rejected', 'contradicted'].includes(e.status)));
    if (rows.length > 1) variants.push({ key, proposals: rows });
    if (!retained.length) continue;
    const first = retained[0];
    active.push({ ...first, sourceIds: [...new Set(retained.flatMap(e => e.sourceIds))],
      claimIds: [...new Set(retained.flatMap(e => e.claimIds))],
      // A disagreement cannot be made supported by deduplication.
      status: rows.some(e => e.status !== first.status) ? 'unknown' : first.status });
  }
  return { active, rejected, variants };
}

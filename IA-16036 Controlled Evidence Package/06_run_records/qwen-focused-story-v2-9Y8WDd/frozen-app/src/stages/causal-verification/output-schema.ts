import { z } from 'zod';
import { verificationSchema } from '../../domain/schemas';
import type { CausalBoard } from '../../domain/types';

/** Select only references that exist in the exact board being reviewed. */
export function verificationSchemaFor(board: CausalBoard) {
  const nodeIds = [...new Set(board.nodes.map(node => node.id))];
  if (!nodeIds.length) throw new Error('Causal verification requires a nonempty board.');
  const targetIds = [...new Set([...nodeIds, ...board.edges.map(edge => edge.id)])];
  return verificationSchema.extend({
    verifiedNodeKeys: z.array(z.enum(nodeIds as [string, ...string[]])),
    verifiedEdgeIndexes: board.edges.length
      ? z.array(z.number().int().min(0).max(board.edges.length - 1))
      : z.array(z.number().int()).max(0),
    findings: z.array(verificationSchema.shape.findings.element.extend({
      targetKey: z.enum(targetIds as [string, ...string[]]),
    })).max(16),
  });
}

import { z } from 'zod';
import { causalAnalysisSchema, decisionSchema } from '@/src/domain/schemas';

// Node identities are deliberately absent from the model's first operation.
export const causalNodesSchema = causalAnalysisSchema.omit({ edges: true }).extend({
  nodes: z.array(causalAnalysisSchema.shape.nodes.element.omit({ key: true })).max(17),
});

export function causalLinksSchema(keys: string[], targetKeys: string[], claimIds: string[]) {
  return z.object({
    edges: z.array(causalAnalysisSchema.shape.edges.element.extend({
      fromKey: z.enum(keys as [string, ...string[]]),
      toKey: z.enum(targetKeys as [string, ...string[]]),
      claimIds: claimIds.length ? z.array(z.enum(claimIds as [string, ...string[]])).max(12) : z.array(z.string()).max(0),
    })).max(12),
    decision: decisionSchema,
  });
}

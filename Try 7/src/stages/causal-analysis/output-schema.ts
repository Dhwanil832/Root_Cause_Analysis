import { z } from 'zod';
import { causalAnalysisSchema, decisionSchema } from '@/src/domain/schemas';

// Node identities are deliberately absent from the model's first operation.
export const causalNodesSchema = causalAnalysisSchema.omit({ edges: true }).extend({
  nodes: z.array(causalAnalysisSchema.shape.nodes.element.omit({ key: true })).max(17),
  evidenceRequests: z.array(z.string()),
});

export function causalLinksSchema(keys: string[], targetKeys: string[], claimIds: string[]) {
  return z.object({
    edges: z.array(causalAnalysisSchema.shape.edges.element.extend({
      fromKey: z.enum(keys as [string, ...string[]]),
      toKey: z.enum(targetKeys as [string, ...string[]]),
      claimIds: claimIds.length ? z.array(z.enum(claimIds as [string, ...string[]])).max(12) : z.array(z.string()).max(0),
    })).max(12),
    decision: decisionSchema,
    evidenceRequests: z.array(z.string()),
  });
}

export function branchRevisionSchema(ids: string[]) {
  return z.object({ updates: z.object(Object.fromEntries(ids.map(id => [id, z.object({
    action: z.enum(['keep', 'strengthen', 'weaken', 'revise', 'reject', 'unresolved']),
    reason: z.string().min(1), replacementIds: z.array(z.string()), evidenceIds: z.array(z.string()),
  }).strict()]))).strict(), decision: decisionSchema, evidenceRequests: z.array(z.string()) });
}

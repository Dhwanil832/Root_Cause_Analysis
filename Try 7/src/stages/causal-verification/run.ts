import { stableId } from '@/src/domain/ids';
import type { CausalBoard, InvestigationQuestion, ModelDescriptor, VerificationFinding } from '@/src/domain/types';
import { z } from 'zod';
import { decisionSchema } from '@/src/domain/schemas';
import { batchesBySize } from '@/src/knowledge/batches';
import { promptFor, PROMPT_VERSION } from '@/src/prompts/manifest';
import { createEvidenceIndex } from '../causal-analysis/evidence-index';
import { runFocusedOperation } from '../causal-analysis/focused-operation';
import type { PhaseSink } from '../causal-analysis/consolidate';
import { groundReview, type TargetReview } from './review-contract';

export async function runCausalVerification(model: ModelDescriptor, packet: unknown, board: CausalBoard,
  keyToId: Map<string, string>, sink?: PhaseSink) {
  void keyToId;
  const index = createEvidenceIndex(packet);
  const reviews: Record<string, TargetReview> = {};
  const results = [], coverageAudit = [];
  for (const targets of batchesBySize([...board.nodes, ...board.edges], 6_000, 3)) {
    const endpoints = board.nodes.filter(n => targets.some(t => 'from' in t && (t.from === n.id || t.to === n.id)));
    const refs = [...targets, ...endpoints].flatMap(t => [...t.sourceIds, ...t.claimIds || []]);
    const focused = index.workingSet(refs, [...targets, ...endpoints]);
    const row = z.object({ verdict: z.enum(['supported', 'contradicted', 'insufficient', 'viable-hypothesis']),
      issue: z.string(), evidenceNeeded: z.string(), question: z.string(),
      citations: z.array(z.object({ sourceId: z.enum(index.sourceIds as [string, ...string[]]), quote: z.string() }).strict()),
    }).strict();
    try {
      const calls = await runFocusedOperation({ model, stage: 'causal-verification', schemaName: 'grounded_target_verification',
        systemPrompt: promptFor('causal-verification'), targets, records: focused.records,
        schemaFor: owned => z.object({ reviews: z.object(Object.fromEntries(owned.map(t => [t.id, row]))).strict(), decision: decisionSchema }),
        packetFor: owned => ({ targets: owned, endpointNodes: endpoints,
          sourceCatalog: index.sourceCatalog, evidenceCoverage: focused.coverage,
          referenceResolution: { sourceIds: focused.resolution.sourceIds, claimIds: focused.resolution.claimIds,
            unresolved: focused.resolution.unresolved },
          citedClaims: focused.resolution.claimIds.map(id => index.claims.get(id)).filter(Boolean)
            .map(c => ({ id: c!.id, text: c!.text, sourceIds: c!.sourceIds, status: c!.status,
              note: 'Claim to test, not independent evidence.' })),
        }),
      });
      results.push(...calls);
      for (const call of calls) for (const [id, review] of Object.entries(call.output.reviews)) {
        if (reviews[id]) throw new Error('A verification target was reviewed more than once by separate evidence pages.');
        reviews[id] = groundReview(review, focused.records);
      }
    } catch (error) {
      // Preserve unrelated completed reviews. Failed calls remain checkpointed.
      for (const target of targets) if (!reviews[target.id]) reviews[target.id] = {
        verdict: 'insufficient', issue: `Review operation incomplete: ${String(error)}`,
        evidenceNeeded: 'Resume independent review of this target using the saved evidence.', question: '', citations: [],
      };
    }
    coverageAudit.push({ targets: targets.map(t => t.id), coverage: focused.coverage,
      normalizations: focused.resolution.normalizations, unresolved: focused.resolution.unresolved });
    await sink?.(`verification-${Object.keys(reviews).length}`, { reviews, coverageAudit });
  }
  const findings: VerificationFinding[] = [...board.verificationFindings];
  for (const [id, review] of Object.entries(reviews)) if (review.verdict !== 'supported') findings.push({
    id: stableId('verify', `${id}:${review.issue}`), targetId: id,
    severity: review.verdict === 'viable-hypothesis' ? 'important' : 'blocking',
    issue: review.issue || 'The evidence does not establish this proposition.',
    evidenceNeeded: review.evidenceNeeded || 'Evidence establishing the complete proposition.',
    question: review.question || undefined,
  });
  const blocked = new Set(findings.filter(f => f.severity === 'blocking').map(f => f.targetId));
  const approved = (id: string) => reviews[id]?.verdict === 'supported' && !blocked.has(id);
  const verifiedBoard: CausalBoard = { ...board,
    maturity: 'developing', // A batch of supported targets is not human RCA closure.
    nodes: board.nodes.map(n => ({ ...n, verified: approved(n.id),
      status: approved(n.id) ? 'supported' : reviews[n.id]?.verdict === 'contradicted' ? 'contradicted' : 'unknown' })),
    edges: board.edges.map(e => {
      const verified = approved(e.id) && approved(e.from) && approved(e.to);
      return { ...e, verified, status: verified ? 'supported' : reviews[e.id]?.verdict === 'contradicted' ? 'contradicted' : 'unknown' };
    }),
    verificationFindings: findings,
  };
  const questions: InvestigationQuestion[] = findings.filter(f => f.question).map(f => ({
    id: stableId('vq', `${f.targetId}:${f.question}`), tagId: 'causal-verification', proposedBy: 'causal-verification',
    routedTo: [], text: f.question!, intent: `verify-${f.targetId}`, rationale: f.issue,
    evidenceNeeded: [f.evidenceNeeded], priority: f.severity === 'blocking' ? 'high' : 'medium', status: 'proposed',
  }));
  return { output: { reviews }, board: verifiedBoard, questions, coverageAudit,
    providerAttempts: results.map(r => r.providerAttempts),
    trace: { id: stableId('verification', JSON.stringify(reviews)), stage: 'causal-verification' as const,
      summary: `${Object.keys(reviews).length} targets reviewed against jointly supplied evidence; ${Object.values(reviews).filter(r => r.verdict === 'supported').length} supported; ${blocked.size} blocked targets.`,
      evidence: [...new Set(Object.values(reviews).flatMap(r => r.citations.map(c => c.sourceId)))],
      unknowns: Object.values(reviews).filter(r => r.verdict !== 'supported').map(r => r.evidenceNeeded),
      alternatives: [], confidence: 0, promptVersion: PROMPT_VERSION, engine: model.provider,
      durationMs: results.reduce((n, r) => n + r.trace.durationMs, 0),
      validation: (Object.values(reviews).some(r => r.issue.startsWith('Review operation incomplete:')) ? 'failed' : 'valid') as 'failed' | 'valid',
      reused: results.length > 0 && results.every(r => r.trace.reused) },
  };
}

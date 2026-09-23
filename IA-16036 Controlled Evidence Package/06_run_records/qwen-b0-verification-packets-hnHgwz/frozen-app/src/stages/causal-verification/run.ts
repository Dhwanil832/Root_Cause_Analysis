import { stableId } from '@/src/domain/ids';
import type { CausalBoard, InvestigationQuestion, ModelDescriptor } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';
import { z } from 'zod';
import { decisionSchema } from '@/src/domain/schemas';
import { batchesBySize } from '@/src/knowledge/batches';
import type { EvidenceClaim, VerificationFinding } from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { verificationPacketPartitions } from './packet-partitions';

export async function runCausalVerification(model: ModelDescriptor, packet: unknown, board: CausalBoard, keyToId: Map<string, string>) {
  void keyToId; // Legacy caller argument: model-local aliases no longer participate.
  const evidence = packet as { evidenceSegments: EvidenceSegment[]; evidenceClaims: EvidenceClaim[]; originalIncident: unknown; answers: unknown; conflicts: unknown };
  const reviews: Record<string, { supported: boolean; issue: string; evidenceNeeded: string; question: string }> = {};
  const results = [];
  for (const targets of batchesBySize([...board.nodes, ...board.edges], 9_000, 3)) {
    const sourceIds = new Set(targets.flatMap(t => t.sourceIds));
    const claimIds = new Set(targets.flatMap(t => 'claimIds' in t ? t.claimIds : []));
    const claims = evidence.evidenceClaims.filter(c => claimIds.has(c.id) || c.sourceIds.some(id => sourceIds.has(id)));
    for (const claim of claims) for (const id of claim.sourceIds) sourceIds.add(id);
    const segments = evidence.evidenceSegments.filter(s => sourceIds.has(s.sourceId) || sourceIds.has(s.documentId));
    const schema = z.object({ reviews: z.object(Object.fromEntries(targets.map(t => [t.id, z.object({
      supported: z.boolean(), issue: z.string(), evidenceNeeded: z.string(), question: z.string(),
    }).strict()]))).strict(), decision: decisionSchema });
    const pages = batchesBySize(segments, 18_000, 8);
    for (const page of pages.length ? pages : [[]]) {
      const packets = verificationPacketPartitions({
        originalIncident: evidence.originalIncident, answers: evidence.answers,
        sources: page, claims, conflicts: evidence.conflicts, targets,
        nodes: board.nodes.filter(n => targets.some(t => t.id === n.id || ('from' in t && (t.from === n.id || t.to === n.id)))),
        sourcePages: Math.max(1, pages.length),
      });
      for (const verificationPacket of packets) {
        const result = await runAgentStage({ stage: 'causal-verification', model, schema, schemaName: 'target_verification',
          packet: verificationPacket,
          instruction: 'Review each fixed target property. You do not generate IDs or edge indexes. supported=true requires direct evidence for the complete proposition or relationship, not merely a plausible mechanism. A claim review or prior board label is not independent corroboration. For any unsupported target supply the specific gap and smallest useful question. This page is not the whole evidence collection; never infer absence from missing records.',
        });
        results.push(result);
        for (const target of targets) {
          const row = result.output.reviews[target.id];
          const prior = reviews[target.id];
          // With multiple context/source pages, no one-page approval overrides a gap or
          // contradiction seen elsewhere. Leave joint support for human review.
          reviews[target.id] = prior ? { supported: prior.supported && row.supported,
            issue: [prior.issue, row.issue].filter(Boolean).join(' '),
            evidenceNeeded: [prior.evidenceNeeded, row.evidenceNeeded].filter(Boolean).join(' '),
            question: prior.question || row.question,
          } : row;
        }
      }
    }
  }
  const findings: VerificationFinding[] = [...board.verificationFindings];
  const establishedClaims = new Set(evidence.evidenceClaims.filter(c => c.review?.verdict === 'supported').map(c => c.id));
  for (const edge of board.edges) if (edge.claimIds.some(id => !establishedClaims.has(id))) findings.push({
    id: stableId('verify', `unreviewed-claim:${edge.id}`), targetId: edge.id, severity: 'blocking',
    issue: 'This relationship cites at least one claim that did not pass evidence review.',
    evidenceNeeded: 'Resolve or replace the unsupported/contradicted cited claim before accepting this relationship.',
  });
  for (const [id, review] of Object.entries(reviews)) if (!review.supported) findings.push({
    id: stableId('verify', `${id}:${review.issue}`), targetId: id, severity: 'blocking',
    issue: review.issue || 'The source evidence does not establish this proposition.',
    evidenceNeeded: review.evidenceNeeded || 'Evidence directly establishing the complete proposition.', question: review.question || undefined,
  });
  const blocked = new Set(findings.filter(f => f.severity === 'blocking').map(f => f.targetId));
  const approved = (id: string) => Boolean(reviews[id]?.supported) && !blocked.has(id);
  const result = { output: { reviews }, providerAttempts: results.map(r => r.providerAttempts),
    trace: { ...results[0].trace, durationMs: results.reduce((n, r) => n + r.trace.durationMs, 0),
      summary: `${Object.keys(reviews).length} application-owned targets reviewed in ${results.length} durable operations; ${blocked.size} unresolved targets.`,
      reused: results.every(r => r.trace.reused),
    } };
  const verifiedBoard: CausalBoard = {
    ...board,
    maturity: blocked.size ? 'developing' : board.edges.length ? 'ready-for-review' : 'initial',
    nodes: board.nodes.map(node => ({ ...node, verified: approved(node.id),
      status: approved(node.id) ? 'supported' : blocked.has(node.id) ? 'unknown' : node.status })),
    edges: board.edges.map(edge => {
      const verified = approved(edge.id) && approved(edge.from) && approved(edge.to);
      return { ...edge, verified, status: verified ? 'supported' : 'unknown' };
    }),
    verificationFindings: findings,
  };
  const questions: InvestigationQuestion[] = findings.filter(finding => finding.question).map((finding) => ({
    id: stableId('vq', `${finding.targetId}:${finding.question}`), tagId: 'causal-verification',
    proposedBy: 'causal-verification', routedTo: [], text: finding.question!,
    intent: `verify-${finding.targetId}`, rationale: finding.issue,
    evidenceNeeded: [finding.evidenceNeeded], priority: finding.severity === 'blocking' ? 'high' : 'medium', status: 'proposed',
  }));
  return { ...result, board: verifiedBoard, questions };
}

import { verificationSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CausalBoard, InvestigationQuestion, ModelDescriptor } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export async function runCausalVerification(model: ModelDescriptor, packet: unknown, board: CausalBoard, keyToId: Map<string, string>) {
  const result = await runAgentStage({ stage: 'causal-verification', model, schema: verificationSchema, schemaName: 'causal_verification', packet: { packet, board } });
  const verifiedNodeIds = new Set(result.output.verifiedNodeKeys.map((key) => keyToId.get(key)).filter(Boolean));
  const verifiedEdgeIndexes = new Set(result.output.verifiedEdgeIndexes);
  const verifiedBoard: CausalBoard = {
    ...board,
    maturity: result.output.maturity,
    nodes: board.nodes.map((node) => ({ ...node, verified: verifiedNodeIds.has(node.id) })),
    edges: board.edges.map((edge, index) => ({ ...edge, verified: verifiedEdgeIndexes.has(index) })),
    verificationFindings: result.output.findings.map((finding) => ({
      id: stableId('verify', `${finding.targetKey}:${finding.issue}`),
      targetId: keyToId.get(finding.targetKey) || finding.targetKey,
      severity: finding.severity, issue: finding.issue, evidenceNeeded: finding.evidenceNeeded,
      question: finding.question || undefined,
    })),
  };
  const questions: InvestigationQuestion[] = result.output.findings.filter((finding) => finding.question).map((finding) => ({
    id: stableId('vq', `${finding.targetKey}:${finding.question}`), tagId: 'causal-verification',
    proposedBy: 'causal-verification', routedTo: [], text: finding.question,
    intent: `verify-${finding.targetKey}`, rationale: finding.issue,
    evidenceNeeded: [finding.evidenceNeeded], priority: finding.severity === 'blocking' ? 'high' : 'medium', status: 'proposed',
  }));
  return { ...result, board: verifiedBoard, questions };
}

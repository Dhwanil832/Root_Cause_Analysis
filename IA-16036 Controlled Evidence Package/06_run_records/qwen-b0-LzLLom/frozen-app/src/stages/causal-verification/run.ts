import { stableId } from '@/src/domain/ids';
import type { CausalBoard, InvestigationQuestion, ModelDescriptor } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';
import { verificationReferenceProblems, verifiedTargetSets } from './reference-contract';
import { verificationSchemaFor } from './output-schema';

export async function runCausalVerification(model: ModelDescriptor, packet: unknown, board: CausalBoard, keyToId: Map<string, string>) {
  const result = await runAgentStage({
    stage: 'causal-verification', model, schema: verificationSchemaFor(board), schemaName: 'causal_verification', packet: { packet, board },
    validateOutput: output => verificationReferenceProblems(output, board, keyToId),
  });
  const verified = verifiedTargetSets(result.output, board, keyToId);
  const verifiedBoard: CausalBoard = {
    ...board,
    maturity: result.output.maturity,
    nodes: board.nodes.map((node) => ({ ...node, verified: verified.nodes.has(node.id) })),
    edges: board.edges.map((edge, index) => ({ ...edge, verified: verified.edges.has(index) })),
    verificationFindings: [...board.verificationFindings, ...result.output.findings.map((finding) => ({
      id: stableId('verify', `${finding.targetKey}:${finding.issue}`),
      targetId: verified.targets.get(finding.targetKey)!,
      severity: finding.severity, issue: finding.issue, evidenceNeeded: finding.evidenceNeeded,
      question: finding.question || undefined,
    }))],
  };
  const questions: InvestigationQuestion[] = result.output.findings.filter((finding) => finding.question).map((finding) => ({
    id: stableId('vq', `${finding.targetKey}:${finding.question}`), tagId: 'causal-verification',
    proposedBy: 'causal-verification', routedTo: [], text: finding.question,
    intent: `verify-${finding.targetKey}`, rationale: finding.issue,
    evidenceNeeded: [finding.evidenceNeeded], priority: finding.severity === 'blocking' ? 'high' : 'medium', status: 'proposed',
  }));
  return { ...result, board: verifiedBoard, questions };
}

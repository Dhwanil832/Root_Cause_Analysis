import { causalAnalysisSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CausalBoard, InvestigationQuestion, ModelDescriptor } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export async function runCausalAnalysis(model: ModelDescriptor, packet: unknown) {
  const result = await runAgentStage({ stage: 'causal-analysis', model, schema: causalAnalysisSchema, schemaName: 'causal_analysis', packet });
  const keyToId = new Map(result.output.nodes.map((node) => [node.key, stableId('node', `${node.type}:${node.key}`)]));
  const nodes = result.output.nodes.map((node) => ({
    id: keyToId.get(node.key)!, type: node.type, label: node.label, detail: node.detail,
    status: node.status, sourceIds: node.sourceIds, specialistIds: node.specialistIds, verified: false,
  }));
  const edges = result.output.edges.flatMap((edge, index) => {
    const from = keyToId.get(edge.fromKey);
    const to = keyToId.get(edge.toKey);
    if (!from || !to) return [];
    return [{
      id: stableId('edge', `${from}:${to}:${edge.type}:${index}`), from, to, type: edge.type,
      rationale: edge.rationale, status: edge.status, sourceIds: edge.sourceIds, verified: false,
    }];
  });
  const board: CausalBoard = {
    maturity: result.output.maturity,
    focalNodeId: keyToId.get(result.output.focalKey) || nodes.find((node) => node.type === 'focal-event')?.id || '',
    nodes, edges, verificationFindings: [],
  };
  const questions: InvestigationQuestion[] = result.output.questions.map((candidate) => ({
    id: stableId('cq', candidate.intent || candidate.text), tagId: 'causal-analysis',
    proposedBy: 'causal-analysis', routedTo: candidate.routedTo, text: candidate.text,
    intent: candidate.intent, rationale: candidate.rationale, evidenceNeeded: candidate.evidenceNeeded,
    priority: candidate.priority, status: 'proposed',
  }));
  return { ...result, board, questions, keyToId };
}

import { causalAnalysisSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CausalBoard, CausalNode, InvestigationQuestion, ModelDescriptor, VerificationFinding } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';
import { cleanCausalLabel } from './label-contract';

export async function runCausalAnalysis(model: ModelDescriptor, packet: unknown) {
  const result = await runAgentStage({ stage: 'causal-analysis', model, schema: causalAnalysisSchema, schemaName: 'causal_analysis', packet });
  const labelCorrections = result.output.nodes.flatMap(node => {
    const label = cleanCausalLabel(node.label);
    return label === node.label ? [] : [{ key: node.key, original: node.label, normalized: label }];
  });
  const keyToId = new Map(result.output.nodes.map((node) => [node.key, stableId('node', `${node.type}:${node.key}`)]));
  const nodes: CausalNode[] = result.output.nodes.map((node) => ({
    id: keyToId.get(node.key)!, type: node.type, label: cleanCausalLabel(node.label), detail: node.detail,
    status: ['supported', 'verified'].includes(node.status) && !node.sourceIds.length ? 'proposed' : node.status,
    sourceIds: node.sourceIds, specialistIds: node.specialistIds, verified: false,
  }));
  const findings: VerificationFinding[] = [];
  const focalKey = result.output.focalKey;
  const byKey = new Map(result.output.nodes.map((node) => [node.key, node]));
  const edges = result.output.edges.flatMap((edge, index) => {
    const from = keyToId.get(edge.fromKey);
    const to = keyToId.get(edge.toKey);
    if (!from || !to) return [];
    const target = byKey.get(edge.toKey);
    const pointsBackwardFromEvent = edge.fromKey === focalKey && target && [
      'condition', 'change', 'barrier', 'human-decision-action', 'direct-cause',
      'contributing-cause', 'root-cause-candidate',
    ].includes(target.type);
    const missingSupport = ['supported', 'verified'].includes(edge.status)
      && !edge.sourceIds.length && !edge.claimIds.length;
    const missingTest = ['caused', 'enabled', 'failed-to-prevent'].includes(edge.type)
      && (!edge.counterfactual.trim() || !edge.competingExplanation.trim());
    if (edge.fromKey === edge.toKey || pointsBackwardFromEvent || missingTest) {
      findings.push({
        id: stableId('verify', `rejected-edge:${edge.fromKey}:${edge.toKey}:${index}`),
        targetId: to,
        severity: 'blocking',
        issue: edge.fromKey === edge.toKey
          ? 'The model proposed a self-referential causal edge.'
          : pointsBackwardFromEvent
            ? 'The model pointed from the focal event toward a pre-event causal condition.'
            : 'The causal edge did not include a usable counterfactual and competing explanation.',
        evidenceNeeded: edge.evidenceGap || 'Evidence that discriminates this causal relationship from its strongest alternative.',
      });
      return [];
    }
    return [{
      id: stableId('edge', `${from}:${to}:${edge.type}:${index}`), from, to, type: edge.type,
      rationale: edge.rationale, status: missingSupport ? 'proposed' as const : edge.status,
      sourceIds: edge.sourceIds, claimIds: edge.claimIds, counterfactual: edge.counterfactual,
      competingExplanation: edge.competingExplanation, evidenceGap: edge.evidenceGap,
      verified: false,
    }];
  });
  const focalId = keyToId.get(focalKey) || nodes.find((node) => node.type === 'focal-event')?.id || '';
  const hasInboundCausalEdge = edges.some((edge) => edge.to === focalId && ['caused', 'enabled', 'failed-to-prevent', 'combined-with'].includes(edge.type));
  const board: CausalBoard = {
    maturity: hasInboundCausalEdge ? result.output.maturity : 'initial',
    focalNodeId: focalId,
    nodes, edges, verificationFindings: findings,
  };
  const questions: InvestigationQuestion[] = result.output.questions.map((candidate) => ({
    id: stableId('cq', candidate.intent || candidate.text), tagId: 'causal-analysis',
    proposedBy: 'causal-analysis', routedTo: candidate.routedTo, text: candidate.text,
    intent: candidate.intent, rationale: candidate.rationale, evidenceNeeded: candidate.evidenceNeeded,
    priority: candidate.priority, status: 'proposed',
  }));
  return { ...result, board, questions, keyToId, labelCorrections };
}

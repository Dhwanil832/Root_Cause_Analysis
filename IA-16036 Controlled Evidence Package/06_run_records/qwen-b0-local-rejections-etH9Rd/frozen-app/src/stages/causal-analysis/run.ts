import type { CausalAnalysisOutput } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CausalBoard, CausalNode, InvestigationQuestion, ModelDescriptor, RejectedCausalEdge, VerificationFinding } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';
import { cleanCausalLabel } from './label-contract';
import { causalOutputProblems, materializeCausalGraph } from './reference-contract';
import { causalEvidenceView } from './evidence-view';
import { causalNodesSchema, causalLinksSchema } from './output-schema';
import { batchesBySize } from '@/src/knowledge/batches';

export async function runCausalAnalysis(model: ModelDescriptor, packet: unknown) {
  const input = causalEvidenceView(packet);
  const claimPages = JSON.stringify(input).length > 40_000 ? batchesBySize(input.evidenceClaims, 12_000, 20) : [input.evidenceClaims];
  const nodeResults = [];
  for (const claims of claimPages.length ? claimPages : [[]]) nodeResults.push(await runAgentStage({
    stage: 'causal-analysis', model, schema: causalNodesSchema, schemaName: 'causal_nodes',
    instruction: `NODE PASS: propose propositions and investigation questions only. Do not emit node keys, IDs, or edges. The application assigns identities after this pass. A verified label cannot be self-awarded; every proposition remains subject to independent evidence review. This is one of ${claimPages.length} claim partitions; absence here is not absence in the investigation.`,
    packet: { ...input, evidenceClaims: claims },
  }));
  const nodeResult = nodeResults[0];
  const assigned = nodeResults.flatMap(r => r.output.nodes).map(node => ({ ...node,
    key: stableId('n', JSON.stringify(node)) }));
  // Only byte-identical propositions coalesce; qualifiers and citations are part
  // of identity. Every raw proposal remains in its model-call checkpoint.
  const unique = [...new Map(assigned.map(n => [n.key, n])).values()];
  const catalog = [{ ...nodeResult.output.focalEvent, key: 'focal', type: 'focal-event' as const }, ...unique];
  const linkResults = [];
  // Each call owns an explicit target partition, so no relationship is silently
  // dropped when output grows. All source-node identities remain available.
  for (const targets of batchesBySize(catalog, 12_000, 3)) {
    linkResults.push(await runAgentStage({
      stage: 'causal-analysis', model, schema: causalLinksSchema(catalog.map(n => n.key), targets.map(n => n.key), input.evidenceClaims.map(c => c.id)),
      schemaName: 'causal_links', packet: { evidence: { ...input,
        evidenceClaims: input.evidenceClaims.map(c => ({ id: c.id, text: c.text, status: c.status, sourceIds: c.sourceIds })),
      }, nodes: catalog.map(n => ({ key: n.key, label: n.label, type: n.type, status: n.status, sourceIds: n.sourceIds })),
      targets, targetKeys: targets.map(n => n.key) },
      instruction: 'LINK PASS: propose only links whose toKey is in targetKeys. Select fromKey and toKey exactly from the application-owned nodes catalog. Do not create or rename nodes. Unknown conditions are questions/hypotheses, not established causes. Omit unjustified links; never connect everything just to fill a graph.',
      // Schema failures still block an unusable response. Semantic failures of
      // individual edges are quarantined below, not retried as a whole batch.
    }));
  }
  const output: CausalAnalysisOutput = { ...nodeResult.output, nodes: unique,
    questions: nodeResults.flatMap(r => r.output.questions),
    edges: linkResults.flatMap(result => result.output.edges) };
  const result = { output, trace: { ...nodeResult.trace,
    durationMs: nodeResults.reduce((n, r) => n + r.trace.durationMs, 0) + linkResults.reduce((n, r) => n + r.trace.durationMs, 0),
    summary: `${nodeResult.trace.summary} Nodes assigned by the application; ${linkResults.length} target-partitioned link operations.`,
    reused: nodeResults.every(r => r.trace.reused) && linkResults.every(r => r.trace.reused),
  }, providerAttempts: { nodes: nodeResults.map(r => r.providerAttempts), links: linkResults.map(r => r.providerAttempts) } };
  const graph = materializeCausalGraph(result.output);
  // Keep a defensive boundary here as well as in the provider's repair loop.
  const problems = causalOutputProblems(result.output);
  if (problems.length) throw new Error(`Causal reference validation was bypassed: ${problems.join('; ')}`);
  const labelCorrections = graph.nodes.flatMap(node => {
    const label = cleanCausalLabel(node.label);
    return label === node.label ? [] : [{ key: node.key, original: node.label, normalized: label }];
  });
  const keyToId = new Map(graph.nodes.map((node) => [node.key, stableId('node', `${node.type}:${node.key}`)]));
  const nodes: CausalNode[] = graph.nodes.map((node) => ({
    id: keyToId.get(node.key)!, type: node.type, label: cleanCausalLabel(node.label), detail: node.detail,
    proposedStatus: node.status,
    status: ['supported', 'verified'].includes(node.status) ? 'proposed' : node.status,
    sourceIds: node.sourceIds, specialistIds: node.specialistIds, verified: false,
  }));
  const findings: VerificationFinding[] = [];
  const rejectedEdges: RejectedCausalEdge[] = [];
  const focalKey = graph.focalKey;
  const byKey = new Map(graph.nodes.map((node) => [node.key, node]));
  const edges = graph.edges.flatMap((edge, index) => {
    const from = keyToId.get(edge.fromKey);
    const to = keyToId.get(edge.toKey);
    if (!from || !to) throw new Error('Causal reference validation was bypassed.');
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
      const rejectionId = stableId('rejected-edge', `${edge.fromKey}:${edge.toKey}:${index}`);
      const reasons = [
        ...(edge.fromKey === edge.toKey ? ['The model proposed a self-referential causal edge.'] : []),
        ...(pointsBackwardFromEvent ? ['The model pointed from the focal event toward a pre-event causal condition.'] : []),
        ...(missingTest ? ['The causal edge did not include a usable counterfactual and competing explanation.'] : []),
      ];
      rejectedEdges.push({ id: rejectionId, fromLabel: byKey.get(edge.fromKey)!.label,
        toLabel: target!.label, reasons, proposal: { ...edge } });
      findings.push({
        id: stableId('verify', rejectionId),
        // Block only this proposal, not its destination or unrelated branches.
        targetId: rejectionId,
        severity: 'blocking',
        issue: reasons.join(' '),
        evidenceNeeded: edge.evidenceGap || 'Evidence that discriminates this causal relationship from its strongest alternative.',
      });
      return [];
    }
    return [{
      id: stableId('edge', `${from}:${to}:${edge.type}:${index}`), from, to, type: edge.type,
      rationale: edge.rationale, proposedStatus: edge.status,
      status: missingSupport || ['supported', 'verified'].includes(edge.status) ? 'proposed' as const : edge.status,
      sourceIds: edge.sourceIds, claimIds: edge.claimIds, counterfactual: edge.counterfactual,
      competingExplanation: edge.competingExplanation, evidenceGap: edge.evidenceGap,
      verified: false,
    }];
  });
  const focalId = keyToId.get(focalKey);
  if (!focalId) throw new Error('Causal reference validation was bypassed: missing focal node.');
  const hasInboundCausalEdge = edges.some((edge) => edge.to === focalId && ['caused', 'enabled', 'failed-to-prevent', 'combined-with'].includes(edge.type));
  const board: CausalBoard = {
    maturity: rejectedEdges.length ? 'developing' : hasInboundCausalEdge ? result.output.maturity : 'initial',
    focalNodeId: focalId,
    nodes, edges, verificationFindings: findings, rejectedEdges,
  };
  const questions: InvestigationQuestion[] = result.output.questions.map((candidate) => ({
    id: stableId('cq', candidate.intent || candidate.text), tagId: 'causal-analysis',
    proposedBy: 'causal-analysis', routedTo: candidate.routedTo, text: candidate.text,
    intent: candidate.intent, rationale: candidate.rationale, evidenceNeeded: candidate.evidenceNeeded,
    priority: candidate.priority, status: 'proposed',
  }));
  return { ...result, board, questions, keyToId, labelCorrections };
}

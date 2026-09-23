import type { CausalAnalysisOutput } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CausalBoard, CausalNode, InvestigationQuestion, ModelDescriptor, RejectedCausalEdge, VerificationFinding } from '@/src/domain/types';
import { cleanCausalLabel } from './label-contract';
import { causalOutputProblems, materializeCausalGraph } from './reference-contract';
import { causalNodesSchema, causalLinksSchema, branchRevisionSchema } from './output-schema';
import { batchesBySize } from '@/src/knowledge/batches';
import { buildCausalContext, initialRecords } from './context-plan';
import { runManagedOperation } from './managed-operation';

export async function runCausalAnalysis(model: ModelDescriptor, packet: unknown) {
  const context = buildCausalContext(packet);
  const { input, archive, base, sources } = context;
  const contextAudit: Array<Record<string, unknown>> = [];
  const unavailable = new Set<string>();
  const changed = new Set(base.evidenceChanges.claimIds);
  const claimPages = batchesBySize([...input.evidenceClaims].sort((a, b) => Number(changed.has(b.id)) - Number(changed.has(a.id))), 8_000, 12);
  const nodeResults = [];
  for (const claims of claimPages.length ? claimPages : [[]]) {
    const operation = await runManagedOperation({
      model, schema: causalNodesSchema, schemaName: 'causal_nodes', archive,
      instruction: `NODE PASS: propose atomic propositions and useful investigation questions from this focused evidence. Do not emit node keys, IDs, or edges. The application assigns identities. A verified label cannot be self-awarded. This is one of ${Math.max(1, claimPages.length)} claim partitions; absence here is not absence in the investigation. Keep observed events distinct from unknown mechanisms. Do not recreate the whole incident board on every page. Request underlying documents when the focused excerpts are insufficient.`,
      packet: { ...base, evidenceClaims: claims,
        workingBranches: initialRecords(context.priorTargets.map(target => ({ id: target.id,
          kind: 'prior-interpretation-not-evidence', value: target })), claims, 3_000).map(r => r.value) },
      records: initialRecords(sources, claims),
    });
    nodeResults.push(...operation.results); contextAudit.push(...operation.audit);
    operation.unavailable.forEach(id => unavailable.add(id));
  }
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
  const compactCatalog = catalog.map(n => ({ key: n.key, label: n.label, type: n.type, status: n.status, sourceIds: n.sourceIds }));
  for (const targets of batchesBySize(compactCatalog, 3_000, 3)) {
    // Cross-partition linking: every source page is paired with every target
    // page. No specialist or discovery partition becomes an isolated subgraph.
    for (const sourceNodes of batchesBySize(compactCatalog, 8_000, 30)) {
      const nodes = [...new Map([...sourceNodes, ...targets].map(n => [n.key, n])).values()];
      const claims = initialRecords(input.evidenceClaims.map(c => archive.get(c.id)!), targets, 7_000);
      const operation = await runManagedOperation({
        model, archive,
        schema: causalLinksSchema(nodes.map(n => n.key), targets.map(n => n.key), input.evidenceClaims.map(c => c.id)),
        schemaName: 'causal_links', packet: { ...base, nodes, targets, targetKeys: targets.map(n => n.key) },
        records: [...claims, ...initialRecords(sources, [...targets, ...claims], 9_000)],
        instruction: 'LINK PASS: examine relationships across the supplied node catalog, including discoveries from different documents and claim partitions. Propose only links whose toKey is in targetKeys. Use exact node keys. Do not create nodes. A sampled observation does not establish continuous coverage. Unknown mechanisms remain hypotheses. Request missing evidence by ID, or leave a bounded gap; never fill a graph with unjustified arrows.',
      });
      linkResults.push(...operation.results); contextAudit.push(...operation.audit);
      operation.unavailable.forEach(id => unavailable.add(id));
    }
  }
  const output: CausalAnalysisOutput = { ...nodeResult.output, nodes: unique,
    questions: nodeResults.flatMap(r => r.output.questions),
    edges: [...new Map(linkResults.flatMap(result => result.output.edges).map(edge => [JSON.stringify(edge), edge])).values()] };
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
  // Account for old interpretations without automatically inheriting their
  // certainty. The ledger is audit data, never evidence for the new graph.
  const revisionResults = [];
  const currentTargets = [...nodes.map(n => ({ id: n.id, label: n.label, type: n.type, status: n.status })),
    ...edges.map(e => ({ id: e.id, from: e.from, to: e.to, type: e.type, status: e.status }))];
  const currentIds = new Set(currentTargets.map(t => t.id));
  board.branchRevisions = [];
  for (const priorTargets of batchesBySize(context.priorTargets, 5_000, 8)) {
    let operation;
    try {
      operation = await runManagedOperation({ model, archive, schemaName: 'branch_revisions',
      schema: branchRevisionSchema(priorTargets.map(t => t.id)),
      packet: { ...base, priorTargets, currentTargets },
      records: initialRecords([...sources, ...input.evidenceClaims.map(c => archive.get(c.id)!)], priorTargets, 10_000),
      instruction: 'REVISION PASS: account for EVERY supplied previous target. State keep, strengthen, weaken, revise, reject, or unresolved, with a concise evidence-based reason and replacementIds from currentTargets. Lack of a replacement is NOT proof the old claim is false. Use unresolved when the mapping or evidence is insufficient. Rejection requires evidence/reason, not mere absence from the regenerated board. Previous review history can be retrieved by previous target ID. This operation records accountability; it cannot make a new finding verified.',
      });
    } catch (error) {
      // Revision accounting must not erase a successfully generated graph.
      // Keep every affected old branch explicitly unresolved and preserve the
      // failed model-call checkpoint for a targeted retry/human reconciliation.
      const reason = `Revision review did not complete: ${error instanceof Error ? error.message : String(error)}`;
      contextAudit.push({ schemaName: 'branch_revisions', failedTargets: priorTargets.map(t => t.id), reason });
      for (const target of priorTargets) {
        board.branchRevisions.push({ previousTargetId: target.id,
          previousLabel: 'label' in target ? target.label : `${target.from} → ${target.to}`,
          action: 'unresolved', reason, replacementIds: [], evidenceIds: [] });
        findings.push({ id: stableId('revision-gap', target.id), targetId: target.id, severity: 'important',
          issue: reason, evidenceNeeded: 'Reconcile this previous branch; no rejection or retention decision was established.' });
      }
      continue;
    }
    revisionResults.push(...operation.results); contextAudit.push(...operation.audit);
    operation.unavailable.forEach(id => unavailable.add(id));
    for (const target of priorTargets) {
      const rows = operation.results.map(r => r.output.updates[target.id]);
      const last = rows.at(-1)!;
      const ambiguous = rows.some(row => row.action !== last.action);
      const replacementIds = last.replacementIds.filter(id => currentIds.has(id));
      const action = ambiguous || (last.action !== 'reject' && !replacementIds.length) ? 'unresolved' : last.action;
      const reason = [ambiguous ? 'Evidence pages produced different dispositions; human reconciliation is required.' : '',
        ...new Set(rows.map(row => row.reason)),
        last.replacementIds.some(id => !currentIds.has(id)) ? 'An invalid replacement reference was excluded.' : '',
      ].filter(Boolean).join(' ');
      board.branchRevisions.push({ previousTargetId: target.id,
        previousLabel: 'label' in target ? target.label : `${target.from} → ${target.to}`,
        action, reason, replacementIds, evidenceIds: [...new Set(rows.flatMap(row => row.evidenceIds))] });
      if (action === 'unresolved') findings.push({ id: stableId('revision-gap', target.id), targetId: target.id,
        severity: 'important', issue: `Previous branch remains unresolved: ${reason}`,
        evidenceNeeded: 'Reconcile this previous interpretation with the current evidence; do not treat its disappearance as disproof.' });
    }
  }
  for (const id of unavailable) findings.push({ id: stableId('retrieval-gap', id), targetId: focalId,
    severity: 'important', issue: `The causal agent requested an unavailable record: ${id}`,
    evidenceNeeded: 'Locate the requested source or clarify its identifier.' });
  result.trace.durationMs += revisionResults.reduce((n, r) => n + r.trace.durationMs, 0);
  result.trace.summary += ` ${board.branchRevisions.length} previous targets accounted for; ${unavailable.size} unavailable retrieval requests.`;
  result.trace.reused = result.trace.reused && revisionResults.every(r => r.trace.reused);
  const questions: InvestigationQuestion[] = result.output.questions.map((candidate) => ({
    id: stableId('cq', candidate.intent || candidate.text), tagId: 'causal-analysis',
    proposedBy: 'causal-analysis', routedTo: candidate.routedTo, text: candidate.text,
    intent: candidate.intent, rationale: candidate.rationale, evidenceNeeded: candidate.evidenceNeeded,
    priority: candidate.priority, status: 'proposed',
  }));
  return { ...result, board, questions, keyToId, labelCorrections, contextAudit,
    providerAttempts: { ...result.providerAttempts, revisions: revisionResults.map(r => r.providerAttempts) } };
}

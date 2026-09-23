import type { CausalAnalysisOutput } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CausalBoard, CausalNode, InvestigationQuestion, ModelDescriptor, RejectedCausalEdge, VerificationFinding } from '@/src/domain/types';
import { cleanCausalLabel } from './label-contract';
import { causalOutputProblems, materializeCausalGraph } from './reference-contract';
import { causalNodesSchema, causalLinksSchema, branchRevisionSchema } from './output-schema';
import { batchesBySize } from '@/src/knowledge/batches';
import { buildCausalContext, initialRecords } from './context-plan';
import { runManagedOperation } from './managed-operation';
import { consolidateCandidates, type PhaseSink } from './consolidate';
import { runFocusedOperation } from './focused-operation';
import { causalPhasePrompt } from '@/src/prompts/manifest';
import { coalesceEdges } from './edge-identity';
import { z } from 'zod';

export async function runCausalAnalysis(model: ModelDescriptor, packet: unknown, sink?: PhaseSink) {
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
  const drafts = [...new Map(assigned.map(n => [n.key, n])).values()];
  await sink?.('discovery', { calls: nodeResults.length, reused: nodeResults.filter(r => r.trace.reused).length, candidates: drafts });
  const consolidated = await consolidateCandidates(model, packet, drafts, nodeResult.output.focalEvent, sink);
  const { catalog, index } = consolidated;
  await sink?.('consolidation-complete', { catalog, ledger: consolidated.ledger, audit: consolidated.audit });
  const compactCatalog = catalog.map(n => ({ key: n.key, label: n.label, type: n.type,
    assessmentKind: n.assessmentKind, sourceIds: n.sourceIds, claimIds: n.claimIds }));
  const linkResults = [];
  // Each target is owned once. There is no target-page × source-node-page loop.
  for (const targets of batchesBySize(compactCatalog, 4_000, 4)) {
    const focused = index.workingSet(targets.flatMap(t => [...t.sourceIds, ...t.claimIds]), targets);
    const calls = await runFocusedOperation({ model, schemaName: 'causal_links_consolidated',
      systemPrompt: causalPhasePrompt('linking'), targets, records: focused.records,
      schemaFor: owned => causalLinksSchema(compactCatalog.map(n => n.key), owned.map(n => n.key), [...index.claims.keys()])
        .omit({ evidenceRequests: true }).extend({
          edges: z.array(causalLinksSchema(compactCatalog.map(n => n.key), owned.map(n => n.key), [...index.claims.keys()])
            .shape.edges.element.extend({ sourceIds: z.array(z.enum(index.sourceIds as [string, ...string[]])) })),
        }),
      packetFor: owned => ({ nodes: compactCatalog, targets: owned, targetKeys: owned.map(n => n.key),
        sourceCatalog: index.sourceCatalog, evidenceCoverage: focused.coverage }),
    });
    linkResults.push(...calls);
    contextAudit.push({ phase: 'linking', targets: targets.map(t => t.key), coverage: focused.coverage });
    await sink?.(`linking-${linkResults.length}`, { completedTargets: linkResults.length, proposals: linkResults.flatMap(r => r.output.edges) });
  }
  const links = coalesceEdges(linkResults.flatMap(r => r.output.edges));
  const output: CausalAnalysisOutput = { ...nodeResult.output,
    focalEvent: catalog[0], nodes: catalog.slice(1) as CausalAnalysisOutput['nodes'],
    questions: nodeResults.flatMap(r => r.output.questions), edges: links.active };
  const graph = materializeCausalGraph(output);
  const problems = causalOutputProblems(output);
  if (problems.length) throw new Error(`Invalid consolidated references: ${problems.join('; ')}`);
  const keyToId = new Map(graph.nodes.map(n => [n.key, stableId('node', `${n.type}:${n.key}`)]));
  const nodes: CausalNode[] = catalog.map(n => ({ id: keyToId.get(n.key)!, type: n.type,
    label: cleanCausalLabel(n.label), detail: n.detail, status: n.assessmentKind === 'hypothesis' ? 'unknown' : 'proposed',
    proposedStatus: n.status, sourceIds: n.sourceIds, claimIds: n.claimIds, specialistIds: n.specialistIds,
    assessmentKind: n.assessmentKind, verified: false }));
  const labelCorrections = catalog.filter(n => cleanCausalLabel(n.label) !== n.label).map(n => ({
    key: n.key, original: n.label, normalized: cleanCausalLabel(n.label),
  }));
  const findings: VerificationFinding[] = [];
  const rejectedEdges: RejectedCausalEdge[] = [];
  const byKey = new Map(catalog.map(n => [n.key, n]));
  const quarantine = (edge: CausalAnalysisOutput['edges'][number], reasons: string[]) => {
    rejectedEdges.push({ id: stableId('rejected-edge', JSON.stringify(edge)),
      fromLabel: byKey.get(edge.fromKey)?.label || edge.fromKey, toLabel: byKey.get(edge.toKey)?.label || edge.toKey,
      reasons, proposal: edge });
  };
  links.rejected.forEach(edge => quarantine(edge, ['The linking agent rejected or contradicted this proposal; it is not an active relationship.']));
  const edges = links.active.flatMap(edge => {
    const from = keyToId.get(edge.fromKey)!, to = keyToId.get(edge.toKey)!;
    const target = byKey.get(edge.toKey)!;
    const reasons = [
      ...(from === to ? ['Self-referential relationship.'] : []),
      ...(edge.fromKey === 'focal' && !['impact', 'event'].includes(target.type)
        ? ['The focal event points backwards to a proposed pre-event condition.'] : []),
      ...(['caused', 'enabled', 'failed-to-prevent'].includes(edge.type) && (!edge.counterfactual.trim() || !edge.competingExplanation.trim())
        ? ['Causal relationship lacks a counterfactual or competing explanation.'] : []),
    ];
    if (reasons.length) { quarantine(edge, reasons); return []; }
    return [{ id: stableId('edge', `${from}:${to}:${edge.type}`), from, to, type: edge.type,
      rationale: edge.rationale, status: 'proposed' as const, proposedStatus: edge.status, sourceIds: edge.sourceIds,
      claimIds: edge.claimIds, counterfactual: edge.counterfactual, competingExplanation: edge.competingExplanation,
      evidenceGap: edge.evidenceGap, verified: false }];
  });
  const board: CausalBoard = { maturity: edges.length ? 'developing' : 'initial', focalNodeId: keyToId.get('focal')!,
    nodes, edges, verificationFindings: findings, rejectedEdges, proposalLedger: consolidated.ledger, branchRevisions: [] };
  await sink?.('linked-board', { board, edgeVariants: links.variants });
  const currentTargets = [...nodes.map(n => ({ id: n.id, label: n.label, type: n.type, status: n.status })),
    ...edges.map(e => ({ id: e.id, from: e.from, to: e.to, type: e.type, status: e.status }))];
  const currentIds = new Set(currentTargets.map(t => t.id));
  const revisionResults = [];
  for (const priorTargets of batchesBySize(context.priorTargets, 4_000, 6)) {
    const focused = index.workingSet(priorTargets.flatMap(t => t.sourceIds), priorTargets);
    try {
      const calls = await runFocusedOperation({ model, schemaName: 'branch_revisions_consolidated',
        systemPrompt: causalPhasePrompt('branch-revision'), targets: priorTargets, records: focused.records,
        schemaFor: targets => branchRevisionSchema(targets.map(t => t.id)).omit({ evidenceRequests: true }),
        packetFor: targets => ({ priorTargets: targets, currentTargets, evidenceCoverage: focused.coverage,
          sourceCatalog: index.sourceCatalog }),
      });
      revisionResults.push(...calls);
      for (const call of calls) for (const [id, row] of Object.entries(call.output.updates)) {
        const target = priorTargets.find(t => t.id === id)!;
        const replacements = row.replacementIds.filter(id => currentIds.has(id));
        board.branchRevisions!.push({ previousTargetId: id,
          previousLabel: 'label' in target ? target.label : `${target.from} → ${target.to}`,
          action: row.replacementIds.some(id => !currentIds.has(id)) ? 'unresolved' : row.action,
          reason: row.reason, replacementIds: replacements, evidenceIds: index.resolve(row.evidenceIds).sourceIds });
      }
    } catch (error) {
      // A failed audit cannot discard the already durable causal board.
      for (const target of priorTargets) board.branchRevisions!.push({ previousTargetId: target.id,
        previousLabel: 'label' in target ? target.label : `${target.from} → ${target.to}`,
        action: 'unresolved', reason: `Revision audit incomplete: ${String(error)}`, replacementIds: [], evidenceIds: [] });
    }
    await sink?.(`revision-${board.branchRevisions!.length}`, { branchRevisions: board.branchRevisions });
  }
  const questions: InvestigationQuestion[] = output.questions.map(candidate => ({
    id: stableId('cq', candidate.intent || candidate.text), tagId: 'causal-analysis', proposedBy: 'causal-analysis',
    routedTo: candidate.routedTo, text: candidate.text, intent: candidate.intent, rationale: candidate.rationale,
    evidenceNeeded: candidate.evidenceNeeded, priority: candidate.priority, status: 'proposed',
  }));
  for (const row of consolidated.ledger) if (row.question.trim()) questions.push({
    id: stableId('cq', row.question), tagId: 'causal-analysis', proposedBy: 'causal-analysis', routedTo: [],
    text: row.question, intent: `resolve-${row.candidateId}`, rationale: row.reason, evidenceNeeded: [row.question],
    priority: 'medium', status: 'proposed',
  });
  for (const id of unavailable) findings.push({ id: stableId('retrieval-gap', id), targetId: board.focalNodeId,
    severity: 'important', issue: `Discovery requested an unavailable record: ${id}`,
    evidenceNeeded: 'Resolve the source identifier; do not treat this as evidence of absence.' });
  const allResults = [...nodeResults, ...consolidated.results, ...linkResults, ...revisionResults];
  return { output, board, questions, keyToId, labelCorrections,
    contextAudit: [...contextAudit, ...consolidated.audit], edgeVariants: links.variants,
    trace: { ...nodeResult.trace, durationMs: allResults.reduce((n, r) => n + r.trace.durationMs, 0),
      reused: allResults.every(r => r.trace.reused),
      summary: `${drafts.length} discovery proposals accounted for; ${nodes.length} consolidated nodes; ${edges.length} relationships; ${board.branchRevisions!.length} prior targets accounted for.` },
    providerAttempts: { nodes: nodeResults.map(r => r.providerAttempts), consolidation: consolidated.results.map(r => r.providerAttempts),
      links: linkResults.map(r => r.providerAttempts), revisions: revisionResults.map(r => r.providerAttempts) } };
}

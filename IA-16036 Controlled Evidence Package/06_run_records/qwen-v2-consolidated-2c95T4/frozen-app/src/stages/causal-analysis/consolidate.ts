import { z } from 'zod';
import { stableId } from '@/src/domain/ids';
import { causalAnalysisSchema, decisionSchema, type CausalAnalysisOutput } from '@/src/domain/schemas';
import type { CausalBoard, ModelDescriptor } from '@/src/domain/types';
import { causalPhasePrompt } from '@/src/prompts/manifest';
import { batchesBySize } from '@/src/knowledge/batches';
import { createEvidenceIndex } from './evidence-index';
import { runFocusedOperation } from './focused-operation';
import { cleanCausalLabel } from './label-contract';

export type DraftNode = CausalAnalysisOutput['nodes'][number];
export type CanonicalNode = DraftNode & { claimIds: string[]; assessmentKind: 'observation' | 'hypothesis' };
export type PhaseSink = (phase: string, value: unknown) => Promise<void>;

const proposition = causalAnalysisSchema.shape.nodes.element.pick({ type: true, label: true, detail: true }).extend({
  assessmentKind: z.enum(['observation', 'hypothesis']), sourceIds: z.array(z.string()), claimIds: z.array(z.string()),
});
export function consolidationSchema(ids: string[], keys: string[], sourceIds: string[]) {
  const row = z.object({ disposition: z.enum(['board', 'merge', 'context', 'question', 'rejected']),
    reason: z.string().min(1), targetKey: z.enum(keys as [string, ...string[]]).nullable(), question: z.string(),
    proposition: proposition.extend({ sourceIds: z.array(z.enum(sourceIds as [string, ...string[]])) }).nullable(),
  }).strict();
  return z.object({ dispositions: z.object(Object.fromEntries(ids.map(id => [id, row]))).strict(), decision: decisionSchema });
}
export type Disposition = z.infer<ReturnType<typeof consolidationSchema>>['dispositions'][string];

export function consolidationProblems(rows: Record<string, Disposition>, existing: Set<string>, candidates: Set<string>, claimIds: Set<string>) {
  const errors: string[] = [];
  for (const [id, row] of Object.entries(rows)) {
    if ((row.disposition === 'board') !== Boolean(row.proposition)) errors.push(`${id}: only board requires a proposition; all other dispositions use null.`);
    if ((row.disposition === 'merge') !== Boolean(row.targetKey)) errors.push(`${id}: only merge requires targetKey; otherwise null.`);
    if (row.disposition === 'question' && !row.question.trim().endsWith('?')) errors.push(`${id}: question must be a useful question ending with ?.`);
    if (row.proposition?.claimIds.some(id => !claimIds.has(id))) errors.push(`${id}: use actual claim IDs; document IDs belong in sourceIds.`);
    if (row.disposition !== 'merge') continue;
    const seen = new Set([id]); let to = row.targetKey;
    while (to && !existing.has(to)) {
      if (seen.has(to) || !candidates.has(to)) { errors.push(`${id}: merge target is cyclic or outside the supplied catalog.`); break; }
      seen.add(to);
      const target = rows[to];
      if (!target || !['board', 'merge'].includes(target.disposition)) { errors.push(`${id}: merge target must resolve to a board proposition.`); break; }
      to = target.disposition === 'board' ? null : target.targetKey;
    }
  }
  return errors;
}

export async function consolidateCandidates(model: ModelDescriptor, packet: unknown, drafts: DraftNode[],
  focal: CausalAnalysisOutput['focalEvent'], sink?: PhaseSink) {
  const index = createEvidenceIndex(packet);
  const focalResolution = index.resolve(focal.sourceIds);
  const catalog: Array<CanonicalNode | (Omit<CanonicalNode, 'type'> & { type: 'focal-event' })> = [{
    ...focal, key: 'focal', type: 'focal-event', label: cleanCausalLabel(focal.label),
    sourceIds: focalResolution.sourceIds, claimIds: focalResolution.claimIds, assessmentKind: 'observation', status: 'proposed',
  }];
  const ledger: NonNullable<CausalBoard['proposalLedger']> = [];
  const results = [], audit = [];
  // Per-operation work units, not a limit on total causes or questions.
  for (const page of batchesBySize(drafts, 7_000, 8)) {
    const candidates = page.map(draft => ({ ...draft, referenceResolution: index.resolve(draft.sourceIds) }));
    const focused = index.workingSet(page.flatMap(d => d.sourceIds), page);
    const rows: Record<string, Disposition> = {};
    const calls = await runFocusedOperation({ model, schemaName: 'causal_consolidation',
      systemPrompt: causalPhasePrompt('consolidation'), targets: candidates, records: focused.records,
      schemaFor: targets => consolidationSchema(targets.map(t => t.key), [...catalog.map(n => n.key), ...targets.map(t => t.key)], index.sourceIds),
      packetFor: targets => ({ candidates: targets.map(({ referenceResolution, ...draft }) => ({ ...draft,
        referenceResolution: { sourceIds: referenceResolution.sourceIds, claimIds: referenceResolution.claimIds, unresolved: referenceResolution.unresolved },
      })), canonicalCatalog: catalog.map(n => ({ key: n.key, type: n.type, label: n.label, detail: n.detail,
        assessmentKind: n.assessmentKind })), sourceCatalog: index.sourceCatalog, evidenceCoverage: focused.coverage }),
      validateOutput: output => consolidationProblems(output.dispositions, new Set(catalog.map(n => n.key)), new Set(Object.keys(output.dispositions)), new Set(index.claims.keys())),
    });
    for (const call of calls) Object.assign(rows, call.output.dispositions);
    results.push(...calls);
    for (const draft of page) {
      const row = rows[draft.key];
      if (row.disposition === 'board' && row.proposition) {
        catalog.push({ ...draft, ...row.proposition, label: cleanCausalLabel(row.proposition.label), status: 'proposed' });
      }
    }
    for (const draft of page) {
      const row = rows[draft.key]; let key = row.disposition === 'board' ? draft.key : row.targetKey;
      while (key && !catalog.some(n => n.key === key)) key = rows[key]?.targetKey || null;
      ledger.push({ candidateId: draft.key, originalLabel: draft.label, disposition: row.disposition,
        reason: row.reason, canonicalId: key ? stableId('node', `${catalog.find(n => n.key === key)!.type}:${key}`) : null,
        question: row.question });
    }
    audit.push({ candidateIds: page.map(d => d.key), coverage: focused.coverage, referenceResolutions: page.map(d => ({ id: d.key, ...index.resolve(d.sourceIds), records: undefined })) });
    await sink?.(`consolidation-${ledger.length}`, { processed: ledger.length, total: drafts.length, catalog, ledger, audit });
  }
  if (ledger.length !== drafts.length || new Set(ledger.map(r => r.candidateId)).size !== drafts.length) throw new Error('Consolidation lost candidate accounting.');
  return { catalog, ledger, results, audit, index };
}

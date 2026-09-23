import { z } from 'zod';
import type { ModelDescriptor } from '@/src/domain/types';
import { promptFor } from '@/src/prompts/manifest';
import { contextBudget, ContextOverflowError, isContextOverflow } from '@/src/providers/context-budget';
import { runAgentStage } from '../run-agent-stage';

export interface ContextRecord { id: string; kind: string; value: unknown }
type Decision = { decision: { summary: string; evidenceUsed: string[]; unknowns: string[]; alternatives: string[]; confidence: number } };
interface ManagedResult<T extends Decision> {
  results: Array<Awaited<ReturnType<typeof runAgentStage<T>>>>;
  audit: Array<Record<string, unknown>>;
  unavailable: string[];
}

export function expandContextRecord(record: ContextRecord): ContextRecord[] {
  if (record.kind === 'source-document' && Array.isArray(record.value)) return record.value.map(segment => ({
    id: segment.sourceId, kind: 'source-passage', value: segment,
  }));
  if (record.kind === 'prior-interpretation-not-evidence') {
    const value = record.value as { target: unknown; unresolvedIssues: Array<{ id: string }> };
    if (value.unresolvedIssues?.length) return [{ ...record, value: { target: value.target,
      issueIds: value.unresolvedIssues.map(issue => issue.id) } }, ...value.unresolvedIssues.map(issue => ({
      id: `prior-review:${issue.id}`, kind: 'prior-review-not-evidence', value: issue,
    }))];
  }
  return [record];
}

/** Only record boundaries are partitioned. No prefixes or low-ranked records
 * are discarded; each selected record is presented on at least one page. */
export function partitionContext<T>(records: T[], fits: (page: T[]) => boolean): T[][] {
  if (!fits([])) throw new ContextOverflowError('The task itself exceeds the context budget; divide its targets before dispatch.');
  const pages: T[][] = [];
  let page: T[] = [];
  for (const record of records) {
    if (!fits([...page, record])) {
      if (page.length) pages.push(page);
      page = [];
      if (!fits([record])) throw new ContextOverflowError('A context record exceeds one request. Segment this record losslessly before dispatch.');
    }
    page.push(record);
  }
  if (page.length || !pages.length) pages.push(page);
  return pages;
}

export async function runManagedOperation<T extends Decision>(options: {
  model: ModelDescriptor; stage?: 'causal-analysis' | 'causal-verification';
  schema: z.ZodType<T>; schemaName: string; instruction: string;
  packet: Record<string, unknown>; records: ContextRecord[];
  archive?: Map<string, ContextRecord>;
}): Promise<ManagedResult<T>> {
  const stage = options.stage || 'causal-analysis';
  const instruction = `${options.instruction}\nEvidence records are supplied in retrievedEvidence. These are exact stored records, not additional independent witnesses. This may be one page of the context. Missing records never prove absence. Where evidenceRequests is available, request a source, claim or prior-target ID from availableEvidence; requested records are read in subsequent operations. Keep conclusions provisional if the supplied pages do not jointly establish them.`;
  const system = `${promptFor(stage)}\n\n${instruction}`;
  const schema = z.toJSONSchema(options.schema, { target: 'draft-7' });
  const packet = (records: ContextRecord[]) => ({ ...options.packet, retrievedEvidence: records });
  const fits = (records: ContextRecord[]) => contextBudget(system, packet(records), schema, stage).fits;
  // A growing replacement catalog is context, not an indivisible task. Review
  // all catalog pages against the same fixed previous targets; callers retain
  // disagreements as unresolved instead of silently choosing one disposition.
  if (Array.isArray(options.packet.currentTargets) && options.packet.currentTargets.length > 1
    && (!fits([]) || options.records.flatMap(expandContextRecord).some(record => !fits([record])))) {
    const targets = options.packet.currentTargets;
    const middle = Math.ceil(targets.length / 2);
    const parts = [];
    for (const page of [targets.slice(0, middle), targets.slice(middle)]) {
      parts.push(await runManagedOperation({ ...options, packet: { ...options.packet, currentTargets: page,
        targetCatalogCoverage: 'Only a partition of current targets is visible. Every partition is reviewed. An absent replacement here is not grounds to reject a prior branch.' } }));
    }
    return { results: parts.flatMap(part => part.results), audit: parts.flatMap(part => part.audit),
      unavailable: [...new Set(parts.flatMap(part => part.unavailable))] };
  }
  const initial = options.records.flatMap(expandContextRecord);
  const queue = partitionContext(initial, fits);
  const scheduled = new Set([...options.records, ...initial].map(record => record.id));
  const results: Array<Awaited<ReturnType<typeof runAgentStage<T>>>> = [];
  const audit: Array<Record<string, unknown>> = [];
  const unavailable = new Set<string>();
  while (queue.length) {
    const page = queue.shift()!;
    try {
      const result = await runAgentStage({ ...options, stage, instruction, packet: packet(page) });
      results.push(result);
      audit.push({ schemaName: options.schemaName, records: page.map(r => r.id),
        budget: contextBudget(system, packet(page), schema, stage), reused: result.trace.reused });
      const requested = (result.output as T & { evidenceRequests?: string[] }).evidenceRequests || [];
      const additional: ContextRecord[] = [];
      for (const id of requested) {
        if (scheduled.has(id)) continue;
        const record = options.archive?.get(id);
        if (!record) { unavailable.add(id); continue; }
        scheduled.add(id);
        for (const part of expandContextRecord(record)) {
          if (part.id !== id && scheduled.has(part.id)) continue;
          scheduled.add(part.id);
          additional.push(part);
        }
      }
      if (additional.length) queue.push(...partitionContext(additional, fits));
    } catch (error) {
      if (!isContextOverflow(error) || page.length < 2) throw error;
      // The estimate is not a tokenizer. An exact server refusal divides just
      // this operation, not the entire RCA run, and never accepts a partial input.
      const middle = Math.ceil(page.length / 2);
      queue.unshift(page.slice(0, middle), page.slice(middle));
      audit.push({ schemaName: options.schemaName, repartitionedAfterServerRefusal: true,
        recordIds: page.map(r => r.id), reason: error.message });
    }
  }
  return { results, audit, unavailable: [...unavailable] };
}

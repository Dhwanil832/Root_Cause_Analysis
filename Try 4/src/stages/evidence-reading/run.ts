import { z } from 'zod';
import { decisionSchema } from '@/src/domain/schemas';
import type { ModelDescriptor } from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { batchesBySize } from '@/src/knowledge/batches';
import { runAgentStage } from '../run-agent-stage';

/** Read every source page; retain the raw readings in durable model-call records.
 * The reasoning context is an explicitly identified retrieval view, not a claim
 * that the original documents have been reduced without semantic loss. */
export async function readEvidenceContext(model: ModelDescriptor, incident: string, sources: EvidenceSegment[]) {
  if (JSON.stringify(sources).length <= 20_000) return { segments: sources, traces: [], coverage: 'Complete source text supplied.' };
  const readings = [], traces = [];
  for (const page of batchesBySize(sources, 12_000, 3)) {
    const result = await runAgentStage({ stage: 'evidence-reading', model, schemaName: 'source_reading',
      schema: z.object({
        passages: z.array(z.object({ sourceId: z.enum(page.map(s => s.sourceId) as [string, ...string[]]),
          excerpt: z.string().max(1200), relevance: z.number().min(0).max(1), note: z.string().max(240) })).max(6),
        decision: decisionSchema,
      }), packet: { incident, sources: page },
      validateOutput: output => output.passages.flatMap(p => {
        const source = page.find(s => s.sourceId === p.sourceId)!;
        return p.excerpt.trim() && source.excerpt.includes(p.excerpt) ? [] : ['Return exact nonempty source passages, without rewriting or ellipses.'];
      }),
    });
    traces.push(result.trace);
    readings.push(...result.output.passages.map(p => ({ ...page.find(s => s.sourceId === p.sourceId)!,
      excerpt: p.excerpt, relevance: p.relevance, readingNote: p.note })));
  }
  const selected: typeof readings = [];
  let size = 0;
  for (const reading of readings.sort((a, b) => b.relevance - a.relevance)) {
    const length = JSON.stringify(reading).length;
    if (size + length > 20_000) continue;
    selected.push(reading); size += length;
  }
  return { segments: selected, traces,
    coverage: `All ${sources.length} source segments were read in ${traces.length} persisted source-reading operations. This reasoning view contains ${selected.length} of ${readings.length} extracted passages, selected by incident relevance. It is NOT the complete document text. All original segments remain available to retrieval, claim review and verification. Do not infer absence from this view.` };
}

import { evidenceAdjudicationSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type {
  EvidenceAdjudicationConflict,
  EvidenceSourceAssessment,
  ModelDescriptor,
} from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { runAgentStage } from '../run-agent-stage';
import { batchesBySize } from '@/src/knowledge/batches';

export async function runEvidenceAdjudication(
  model: ModelDescriptor, incidentContext: unknown, segments: EvidenceSegment[],
) {
  const pages = batchesBySize(segments, 16_000, 6);
  const results = [];
  for (const page of pages.length ? pages : [[]]) {
    const context = incidentContext as Record<string, unknown> & { previousAssessments?: EvidenceSourceAssessment[] };
    const ids = new Set(page.map(s => s.sourceId));
    results.push(await adjudicateBatch(model, { ...context,
      previousAssessments: context.previousAssessments?.filter(s => ids.has(s.sourceId)),
    }, page));
  }
  const first = results[0];
  return { ...first, assessments: results.flatMap(r => r.assessments), conflicts: results.flatMap(r => r.conflicts),
    trace: { ...first.trace, durationMs: results.reduce((n, r) => n + r.trace.durationMs, 0),
      summary: `${segments.length} source segments reviewed in ${results.length} durable batches. Cross-batch claim disagreements are reviewed in claim review and causal verification.` } };
}

async function adjudicateBatch(
  model: ModelDescriptor,
  incidentContext: unknown,
  segments: EvidenceSegment[],
) {
  const result = await runAgentStage({
    stage: 'evidence-adjudication',
    model,
    schema: evidenceAdjudicationSchema,
    schemaName: 'evidence_adjudication',
    packet: { incidentContext, evidenceSegments: segments },
  });
  const supplied = new Map(segments.map((segment) => [segment.sourceId, segment]));
  const seen = new Set<string>();
  const assessments: EvidenceSourceAssessment[] = result.output.assessments.flatMap((assessment) => {
    if (!supplied.has(assessment.sourceId) || seen.has(assessment.sourceId)) return [];
    seen.add(assessment.sourceId);
    return [{
      ...assessment,
      id: stableId('source-assessment', `${assessment.documentId}:${assessment.sourceId}`),
    }];
  });
  const conflicts: EvidenceAdjudicationConflict[] = result.output.conflicts.map((conflict) => ({
    ...conflict,
    id: stableId('adjudication-conflict', `${conflict.sourceIds.join(':')}:${conflict.summary}`),
  }));
  const missing = segments.filter((segment) => !seen.has(segment.sourceId));
  if (missing.length) {
    conflicts.push({
      id: stableId('adjudication-conflict', `missing-source-assessments:${missing.map((item) => item.sourceId).join(':')}`),
      summary: `The model did not adjudicate ${missing.length} of ${segments.length} supplied evidence segments.`,
      sourceIds: missing.slice(0, 8).map((segment) => segment.sourceId),
      resolutionNeeded: 'Re-run source adjudication in smaller batches before treating the evidence review as complete.',
    });
  }
  return { ...result, assessments, conflicts };
}

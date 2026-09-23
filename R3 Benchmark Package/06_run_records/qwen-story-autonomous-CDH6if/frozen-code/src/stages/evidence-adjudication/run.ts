import { evidenceAdjudicationSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type {
  EvidenceAdjudicationConflict,
  EvidenceSourceAssessment,
  ModelDescriptor,
} from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { runAgentStage } from '../run-agent-stage';

export async function runEvidenceAdjudication(
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

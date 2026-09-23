import { evidenceProcessingSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { EvidenceClaim, EvidenceConflict, EvidenceSourceAssessment, InvestigationAnswer, ModelDescriptor } from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { runAgentStage } from '../run-agent-stage';

export async function runEvidenceProcessing(
  model: ModelDescriptor,
  packet: unknown,
  answers: InvestigationAnswer[],
  evidenceSegments: EvidenceSegment[],
  sourceAssessments: EvidenceSourceAssessment[],
  existingClaims: EvidenceClaim[],
) {
  const result = await runAgentStage({
    stage: 'evidence-processing', model, schema: evidenceProcessingSchema, schemaName: 'evidence_processing',
    packet: {
      investigationContext: packet,
      answers,
      evidenceSegments,
      sourceAssessments,
      existingClaims,
    },
  });
  const claims: EvidenceClaim[] = result.output.claims.map((claim) => ({
    ...claim, id: stableId('claim', `${claim.questionId}:${claim.text}`),
    questionId: claim.questionId || undefined,
  }));
  const conflicts: EvidenceConflict[] = result.output.conflicts.map((conflict) => ({
    id: stableId('conflict', conflict.summary), summary: conflict.summary,
    claimIds: conflict.claimIndexes.map((index) => claims[index]?.id).filter(Boolean),
    status: 'open', resolutionNeeded: conflict.resolutionNeeded,
  }));
  return { ...result, claims, conflicts };
}

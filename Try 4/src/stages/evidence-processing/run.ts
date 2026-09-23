import { evidenceProcessingSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { EvidenceClaim, EvidenceConflict, EvidenceSourceAssessment, InvestigationAnswer, ModelDescriptor } from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { runAgentStage } from '../run-agent-stage';
import { batchesBySize } from '@/src/knowledge/batches';

export async function runEvidenceProcessing(
  model: ModelDescriptor, packet: unknown, answers: InvestigationAnswer[], evidenceSegments: EvidenceSegment[],
  sourceAssessments: EvidenceSourceAssessment[], existingClaims: EvidenceClaim[],
) {
  const pages = batchesBySize(evidenceSegments, 16_000, 6);
  const results = [];
  for (const page of pages.length ? pages : [[]]) {
    const ids = new Set(page.flatMap(s => [s.sourceId, s.documentId]));
    results.push(await processBatch(model, packet, answers, page,
      sourceAssessments.filter(s => ids.has(s.sourceId)),
      existingClaims.filter(c => c.sourceIds.some(id => ids.has(id))).map(c => ({
        id: c.id, text: c.text, kind: c.kind, status: c.status, sourceIds: c.sourceIds,
        questionId: c.questionId, routedTo: c.routedTo,
      }))));
  }
  const first = results[0];
  return { ...first, claims: results.flatMap(r => r.claims), conflicts: results.flatMap(r => r.conflicts),
    trace: { ...first.trace, durationMs: results.reduce((n, r) => n + r.trace.durationMs, 0),
      summary: `Candidate extraction over ${results.length} complete source batches. All candidates require claim review before causal use.` } };
}

async function processBatch(
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

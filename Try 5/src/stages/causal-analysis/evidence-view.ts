import type { EvidenceClaim, InvestigationQuestion, SpecialistKnowledgeBase } from '@/src/domain/types';
import type { CausalBoard } from '@/src/domain/types';
import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import { previousBoardContext } from './label-contract';

/** A task-specific view. Stored claims, source documents and specialist records
 * are unchanged; only duplicated context and presentation metadata are excluded. */
export function causalEvidenceView(packet: unknown) {
  const p = packet as Record<string, unknown>;
  const claims = (p.evidenceClaims || []) as EvidenceClaim[];
  const questions = (p.questions || []) as InvestigationQuestion[];
  const specialists = (p.specialistKnowledgeBases || []) as SpecialistKnowledgeBase[];
  return {
    originalIncident: p.originalIncident, structuredIncident: p.structuredIncident,
    evidenceClaims: claims.map(c => ({ id: c.id, text: c.text, kind: c.kind, status: c.status,
      sourceIds: c.sourceIds, review: c.review && { verdict: c.review.verdict, reason: c.review.reason }, routedTo: c.routedTo })),
    evidenceSegments: (p.evidenceSegments || []) as EvidenceSegment[], documentCoverage: p.documentCoverage,
    specialistScopes: specialists.map(k => ({ tagId: k.tagId, handoffs: k.handoffs })),
    openQuestions: questions.filter(q => q.status !== 'answered').map(q => ({
      id: q.id, text: q.text, evidenceNeeded: q.evidenceNeeded, routedTo: q.routedTo,
    })),
    conflicts: p.conflicts, adjudicationConflicts: p.adjudicationConflicts,
    previousBoard: previousBoardContext(p.previousBoard as CausalBoard | null),
    evidenceUse: 'The ledger contains model-reviewed claims and review limitations; underlying passages are supplied separately in evidenceSegments, subject to documentCoverage. Exact claim-review quotations are preserved in the stored ledger rather than repeated here. Review is not human verification. Unsupported/contradicted claims are investigative leads, never facts. Complete source texts remain available to independent verification. Specialist findings duplicate this ledger and are not independent corroboration.',
  };
}

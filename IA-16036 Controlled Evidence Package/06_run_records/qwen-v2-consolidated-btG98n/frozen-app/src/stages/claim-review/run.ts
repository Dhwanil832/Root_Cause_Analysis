import type { Citation, EvidenceClaim, ModelDescriptor, TraceEntry } from '@/src/domain/types';
import { batchesBySize } from '@/src/knowledge/batches';
import { runAgentStage } from '../run-agent-stage';
import { claimReviewSchema, resolveClaimReview, sourcePassages, type ReviewSource } from './evidence-contract';
export type { ReviewSource } from './evidence-contract';

/** Model review is recorded as review, not promoted to human verification. */
export async function runClaimReview(model: ModelDescriptor, claims: EvidenceClaim[], sources: ReviewSource[]) {
  const reviewed: EvidenceClaim[] = [], traces: TraceEntry[] = [];
  for (const batch of batchesBySize(claims, 9_000, 4)) {
    const ids = new Set(batch.flatMap(c => c.sourceIds));
    const terms = [...new Set(batch.flatMap(c => c.text.toLowerCase().match(/[a-z0-9][a-z0-9-]{4,}/g) || []))];
    const allFit = JSON.stringify(sources).length <= 20_000;
    const relevant = sources.filter(s => allFit || ids.has(s.sourceId) || (s.documentId && ids.has(s.documentId))
      || s.sourceId === 'incident-description'
      || terms.filter(term => s.excerpt.toLowerCase().includes(term)).length >= 2);
    // Split source-heavy reviews as well: disagreement between pages remains
    // unresolved, and no page can establish an exhaustive absence.
    const pages = batchesBySize(relevant, 20_000, 10);
    const results = [];
    for (const page of pages.length ? pages : [[]]) {
      const passages = sourcePassages(page);
      const schema = claimReviewSchema(batch.map(claim => claim.id), passages);
      const result = await runAgentStage({ stage: 'claim-review', model, schema, schemaName: 'claim_review',
        packet: { candidates: batch, passages, sourcePages: Math.max(1, pages.length),
          instruction: 'Assess ONLY these exact passages. Select their passageIds; do not generate source IDs or quotations. Missing support on this page means unknown, not absent everywhere.' },
      });
      results.push(Object.fromEntries(batch.map(claim => [claim.id, resolveClaimReview(result.output.reviews[claim.id], passages)])));
      traces.push(result.trace);
    }
    for (const claim of batch) {
      const rows = results.map(result => result[claim.id]);
      const supported = rows.filter(r => r.verdict === 'supported');
      const contradicted = rows.filter(r => r.verdict === 'contradicted');
      const partial = rows.filter(r => r.verdict === 'partial');
      const conflict = supported.length > 0 && contradicted.length > 0;
      const verdict = contradicted.length ? 'contradicted' : supported.length ? 'supported' : partial.length ? 'partial' : 'unsupported';
      const selected = conflict ? [...supported, ...contradicted] : contradicted.length ? contradicted : supported.length ? supported : partial.length ? partial : rows;
      const citations: Citation[] = selected.flatMap(r => r.citations);
      reviewed.push({ ...claim, proposedStatus: claim.proposedStatus || claim.status,
        status: verdict === 'supported' ? 'supported' : verdict === 'partial' ? 'partially-supported' : verdict === 'contradicted' ? 'contradicted' : 'unknown',
        review: { verdict, reason: `${conflict ? 'Unresolved source disagreement. ' : ''}${selected.map(r => r.reason).join(' ')}`, citations,
          assessments: rows.map(row => ({ proposedVerdict: row.proposedVerdict, effectiveVerdict: row.verdict, checks: row.checks, issues: row.issues })) },
      });
    }
  }
  return { claims: reviewed, traces };
}

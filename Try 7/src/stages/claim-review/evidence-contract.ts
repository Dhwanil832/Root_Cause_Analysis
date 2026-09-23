import { z } from 'zod';
import { decisionSchema } from '@/src/domain/schemas';

export interface ReviewSource { sourceId: string; label: string; excerpt: string; documentId?: string }
export interface ReviewPassage { passageId: string; sourceId: string; label: string; excerpt: string }

/** Exact consecutive slices, not model-written quotations or summaries. */
export function sourcePassages(sources: ReviewSource[]): ReviewPassage[] {
  const passages: ReviewPassage[] = [];
  for (const source of sources) {
    let start = 0;
    while (start < source.excerpt.length) {
      let end = Math.min(start + 900, source.excerpt.length);
      if (end < source.excerpt.length) {
        const newline = source.excerpt.lastIndexOf('\n', end - 1);
        const sentence = source.excerpt.lastIndexOf('. ', end - 1);
        const boundary = Math.max(newline + 1, sentence + 2);
        if (boundary > start + 200) end = boundary;
      }
      passages.push({ passageId: `p${passages.length + 1}`, sourceId: source.sourceId,
        label: source.label, excerpt: source.excerpt.slice(start, end) });
      start = end;
    }
  }
  return passages;
}

export function claimReviewSchema(claimIds: string[], passages: ReviewPassage[]) {
  const ids = passages.map(p => p.passageId);
  const passageIds = ids.length
    ? z.array(z.enum(ids as [string, ...string[]]))
    : z.array(z.string()).max(0);
  const row = z.object({
    verdict: z.enum(['supported', 'partial', 'unsupported', 'contradicted']),
    reason: z.string().max(1000),
    checks: z.object({ entity: z.boolean(), location: z.boolean(), time: z.boolean(), meaning: z.boolean(), qualifications: z.boolean() }),
    passageIds,
  });
  // Claim ownership and citation vocabulary are supplied by the application.
  return z.object({ reviews: z.object(Object.fromEntries(claimIds.map(id => [id, row]))), decision: decisionSchema });
}

export type ClaimReviewRow = z.infer<ReturnType<typeof claimReviewSchema>>['reviews'][string];

/** An inconsistent assessment stays visible but can never establish support. */
export function resolveClaimReview(row: ClaimReviewRow, passages: ReviewPassage[]) {
  const byId = new Map(passages.map(p => [p.passageId, p]));
  const selected = [...new Set(row.passageIds)].map(id => byId.get(id));
  const issues: string[] = [];
  let verdict = row.verdict;
  if (selected.some(p => !p)) issues.push('A selected passage is outside this review page.');
  const citations = selected.filter((p): p is ReviewPassage => Boolean(p))
    .map(p => ({ sourceId: p.sourceId, label: p.label, excerpt: p.excerpt }));
  if (verdict !== 'unsupported' && (!citations.length || issues.length)) {
    verdict = 'unsupported';
    issues.push('No valid selected evidence establishes the proposed verdict.');
  }
  if (verdict === 'supported' && Object.values(row.checks).some(value => !value)) {
    verdict = 'partial';
    issues.push(`Full support withheld: checks not satisfied (${Object.entries(row.checks).filter(([, value]) => !value).map(([name]) => name).join(', ')}).`);
  }
  return { verdict, reason: `${row.reason}${issues.length ? ` Harness assessment: ${issues.join(' ')}` : ''}`,
    citations, proposedVerdict: row.verdict, checks: row.checks, issues };
}

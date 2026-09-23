import type { ContextRecord } from '../causal-analysis/managed-operation';
import { sourceText } from '../causal-analysis/evidence-index';

export interface TargetReview {
  verdict: 'supported' | 'contradicted' | 'insufficient' | 'viable-hypothesis';
  issue: string; evidenceNeeded: string; question: string;
  citations: Array<{ sourceId: string; quote: string }>;
}
const normalized = (text: string) => text.replace(/\s+/g, ' ').trim();
/** A bad quote downgrades this target only, not the entire investigation.
 * Exact quotations establish traceability, not entailment; the reviewer still
 * must evaluate whether the complete proposition follows from those passages. */
export function groundReview(row: TargetReview, records: ContextRecord[]): TargetReview {
  const byId = new Map(records.map(r => [r.id, r]));
  const invalid = row.citations.filter(c => !c.quote.trim() || !byId.has(c.sourceId)
    || !normalized(sourceText(byId.get(c.sourceId)!)).includes(normalized(c.quote)));
  const independent = row.citations.some(c => byId.has(c.sourceId) && !c.sourceId.startsWith('story-release:'));
  if (invalid.length || (['supported', 'contradicted'].includes(row.verdict) && !independent)) return {
    ...row, verdict: 'insufficient', issue: [row.issue,
      invalid.length ? 'Review contained an unavailable or nonmatching quotation.' : 'No direct source quotation independent of the simulated answer supports this verdict.',
    ].filter(Boolean).join(' '), evidenceNeeded: row.evidenceNeeded || 'Check the proposition against a traceable source passage.',
  };
  return row;
}

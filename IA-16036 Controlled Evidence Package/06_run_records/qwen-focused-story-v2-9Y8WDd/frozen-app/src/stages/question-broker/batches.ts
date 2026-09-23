import type { InvestigationQuestion } from '../../domain/types';

export const BROKER_BATCH_SIZE = 4;
export const BROKER_CATALOG_PAGE_SIZE = 16;

export interface BrokerDisposition {
  candidateKey: string;
  disposition: 'keep' | 'covered';
  coveredByCandidateKey: string;
  reason: string;
}

export function brokerBatchProblems(
  output: { decisions: BrokerDisposition[] }, candidates: InvestigationQuestion[], catalog: InvestigationQuestion[],
) {
  const problems: string[] = [];
  const ids = new Set(candidates.map(q => q.id));
  const owners = new Set(catalog.map(q => q.id));
  const rows = new Map<string, BrokerDisposition>();
  for (const row of output.decisions) {
    if (!ids.has(row.candidateKey) || rows.has(row.candidateKey)) problems.push(`Unexpected or duplicate candidateKey ${row.candidateKey}.`);
    rows.set(row.candidateKey, row);
  }
  // Candidate order, not generated row order, defines permissible local owners.
  for (const candidate of candidates) {
    const row = rows.get(candidate.id);
    if (!row) { problems.push(`Missing decision for ${candidate.id}. Account for every candidate exactly once.`); continue; }
    if (!row.reason.trim()) problems.push(`Missing reason for ${candidate.id}.`);
    if (row.disposition === 'covered') {
      if (!owners.has(row.coveredByCandidateKey)) problems.push(`Invalid coverage owner for ${candidate.id}: ${row.coveredByCandidateKey}. Use a catalog key or an earlier kept candidate, never itself, a screened candidate, or a future candidate.`);
      if (candidate.status === 'answered') problems.push(`Keep answered question ${candidate.id}; do not redirect an existing answer to a different question.`);
    } else if (row.coveredByCandidateKey !== '') {
      problems.push(`Use an empty coveredByCandidateKey for ${row.disposition} candidate ${candidate.id}.`);
    }
    if (row.disposition === 'keep') owners.add(candidate.id);
  }
  return problems;
}

/** Bounded request/output size, not a cap on investigation questions. */
export async function brokerInBatches(
  candidates: InvestigationQuestion[],
  decide: (batch: InvestigationQuestion[], catalog: InvestigationQuestion[]) => Promise<{ decisions: BrokerDisposition[] }>,
) {
  if (new Set(candidates.map(q => q.id)).size !== candidates.length) throw new Error('Duplicate candidate IDs must be resolved before brokering.');
  const canonical: InvestigationQuestion[] = [];
  const covered: BrokerDisposition[] = [];
  for (let offset = 0; offset < candidates.length; offset += BROKER_BATCH_SIZE) {
    let pending = candidates.slice(offset, offset + BROKER_BATCH_SIZE);
    const pages = Math.max(1, Math.ceil(canonical.length / BROKER_CATALOG_PAGE_SIZE));
    for (let page = 0; page < pages && pending.length; page++) {
      const catalog = canonical.slice(page * BROKER_CATALOG_PAGE_SIZE, (page + 1) * BROKER_CATALOG_PAGE_SIZE);
      const result = await decide(pending, catalog);
      const problems = brokerBatchProblems(result, pending, catalog);
      if (problems.length) throw new Error(problems.join('; '));
      const rows = new Map(result.decisions.map(row => [row.candidateKey, row]));
      pending = pending.filter(candidate => {
        const row = rows.get(candidate.id)!;
        if (row.disposition === 'covered') covered.push(row);
        return row.disposition === 'keep';
      });
    }
    // An earlier local owner may have been merged in a later catalog page.
    canonical.push(...pending);
  }
  const canonicalIds = new Set(canonical.map(q => q.id));
  const byCovered = new Map(covered.map(row => [row.candidateKey, row]));
  for (const row of covered) {
    let owner = row.coveredByCandidateKey;
    const seen = new Set([row.candidateKey]);
    while (!canonicalIds.has(owner)) {
      if (seen.has(owner) || !byCovered.has(owner)) throw new Error(`Coverage for ${row.candidateKey} has no retained canonical owner.`);
      seen.add(owner);
      owner = byCovered.get(owner)!.coveredByCandidateKey;
    }
    row.coveredByCandidateKey = owner;
  }
  return { canonical, covered };
}

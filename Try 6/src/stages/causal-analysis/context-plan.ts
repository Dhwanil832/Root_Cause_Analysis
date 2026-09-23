import type { CausalBoard, EvidenceClaim } from '@/src/domain/types';
import { causalEvidenceView } from './evidence-view';
import type { ContextRecord } from './managed-operation';

const words = (value: unknown) => new Set((JSON.stringify(value).toLowerCase().match(/[a-z0-9][a-z0-9-]{2,}/g) || [])
  .filter(word => !['the', 'and', 'for', 'with', 'that', 'from', 'sourceids', 'status', 'supported', 'unknown'].includes(word)));

export function rankRecords(records: ContextRecord[], query: unknown) {
  const terms = words(query);
  return records.map((record, index) => ({ record, index,
    score: [...words(record.value)].filter(word => terms.has(word)).length }))
    .sort((a, b) => b.score - a.score || a.index - b.index).map(row => row.record);
}

/** This is a retrieval working set, not a deletion from the archive. */
export function initialRecords(records: ContextRecord[], query: unknown, characters = 12_000) {
  const selected: ContextRecord[] = [];
  let length = 0;
  for (const record of rankRecords(records, query)) {
    const size = JSON.stringify(record).length;
    if (length + size > characters) continue;
    selected.push(record); length += size;
  }
  return selected;
}

export function buildCausalContext(packet: unknown) {
  const raw = packet as { previousBoard?: CausalBoard; previousEvidenceClaims?: EvidenceClaim[]; answers?: unknown[] };
  const input = causalEvidenceView(packet);
  const archive = new Map<string, ContextRecord>();
  const add = (id: string, kind: string, value: unknown) => archive.set(id, { id, kind, value });
  input.evidenceSegments.forEach(segment => add(segment.sourceId, 'source-passage', segment));
  // A document ID resolves to all its passages, not just its first chunk.
  for (const id of new Set(input.evidenceSegments.map(segment => segment.documentId))) {
    add(id, 'source-document', input.evidenceSegments.filter(segment => segment.documentId === id));
  }
  input.evidenceClaims.forEach(claim => add(claim.id, 'reviewed-claim-not-independent-evidence', claim));
  for (const target of [...(raw.previousBoard?.nodes || []), ...(raw.previousBoard?.edges || [])]) {
    add(target.id, 'prior-interpretation-not-evidence', { target,
      unresolvedIssues: (raw.previousBoard?.verificationFindings || []).filter(f => f.targetId === target.id) });
  }
  add('structured-incident', 'model-interpretation-not-evidence', input.structuredIncident);
  add('conflicts', 'unresolved-conflicts', { conflicts: input.conflicts, adjudicationConflicts: input.adjudicationConflicts });
  input.openQuestions.forEach(question => add(question.id, 'open-question', question));
  const previous = new Map((raw.previousEvidenceClaims || []).map(claim => [claim.id, claim]));
  const newOrChangedClaims = input.evidenceClaims.filter(claim => {
    const prior = previous.get(claim.id);
    return !prior || prior.text !== claim.text || prior.status !== claim.status || JSON.stringify(prior.sourceIds) !== JSON.stringify(claim.sourceIds);
  }).map(claim => claim.id);
  const changeSetKnown = Array.isArray(raw.previousEvidenceClaims);
  return { input, archive, sources: [...archive.values()].filter(r => r.kind === 'source-passage'),
    base: { originalIncident: input.originalIncident, evidenceUse: input.evidenceUse,
      evidenceChanges: { comparisonAvailable: changeSetKnown,
        claimIds: changeSetKnown ? newOrChangedClaims : [],
        instruction: changeSetKnown ? 'These claims are new or changed since the previous version; not automatically more reliable.' : 'Previous claim ledger unavailable. Do not infer which claims are new.' },
      availableEvidence: [...new Map(input.evidenceSegments.map(s => [s.documentId, { id: s.documentId, label: s.label.split(' · section ')[0] }])).values()],
      retrieval: 'You may request any listed document ID, claim ID, previous target ID, structured-incident, or conflicts. Original records remain stored. Only the focused working set is sent now.' },
    priorTargets: [...(input.previousBoard?.nodes || []), ...(input.previousBoard?.edges || [])],
  };
}

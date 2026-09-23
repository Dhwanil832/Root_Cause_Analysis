import type { EvidenceSegment } from '@/src/knowledge/evidence-segments';
import type { ContextRecord } from './managed-operation';
import { initialRecords } from './context-plan';

interface ClaimRef { id: string; text: string; sourceIds: string[]; status?: string }
interface AnswerRef { sourceId?: string; text?: string; responseStatus?: string; questionId?: string }
export function createEvidenceIndex(packet: unknown) {
  const p = packet as { evidenceSegments?: EvidenceSegment[]; evidenceClaims?: ClaimRef[];
    originalIncident?: { sourceId?: string; text?: string }; answers?: AnswerRef[] };
  const records = new Map<string, ContextRecord>();
  const aliases = new Map<string, Set<string>>();
  const claims = new Map((p.evidenceClaims || []).map(c => [c.id, c]));
  const addAlias = (alias: string, id: string) => {
    if (!aliases.has(alias)) aliases.set(alias, new Set());
    aliases.get(alias)!.add(id);
  };
  for (const segment of p.evidenceSegments || []) {
    records.set(segment.sourceId, { id: segment.sourceId, kind: 'source-passage', value: segment });
    addAlias(segment.documentId, segment.sourceId);
    addAlias(segment.label.split(' · section ')[0], segment.sourceId);
  }
  if (p.originalIncident?.sourceId) records.set(p.originalIncident.sourceId, {
    id: p.originalIncident.sourceId, kind: 'incident-report', value: p.originalIncident,
  });
  for (const answer of p.answers || []) if (answer.sourceId) records.set(answer.sourceId, {
    id: answer.sourceId, kind: 'answer-with-provenance-not-independent-corroboration', value: answer,
  });
  function resolve(refs: string[]) {
    const sourceIds = new Set<string>(), claimIds = new Set<string>(), unresolved = new Set<string>();
    const normalizations: Array<{ from: string; to: string[] }> = [];
    const visiting = new Set<string>();
    function visit(id: string) {
      if (visiting.has(id)) { unresolved.add(id); return; }
      if (records.has(id)) { sourceIds.add(id); return; }
      if (claims.has(id)) {
        claimIds.add(id); visiting.add(id);
        const refs = claims.get(id)!.sourceIds;
        normalizations.push({ from: id, to: refs }); refs.forEach(visit); visiting.delete(id); return;
      }
      if (aliases.has(id)) {
        const parts = [...aliases.get(id)!];
        // A filename collision across different documents is ambiguous, not a citation.
        const docs = new Set(parts.map(part => (records.get(part)!.value as EvidenceSegment).documentId));
        if (docs.size > 1) { unresolved.add(id); return; }
        normalizations.push({ from: id, to: parts }); parts.forEach(visit); return;
      }
      unresolved.add(id);
    }
    refs.forEach(visit);
    return { sourceIds: [...sourceIds], claimIds: [...claimIds], unresolved: [...unresolved], normalizations,
      records: [...sourceIds].map(id => records.get(id)!) };
  }
  return { records, claims, resolve, sourceIds: [...records.keys()],
    workingSet(refs: string[], query: unknown) {
      const resolved = resolve(refs);
      // Always include cited records, then whole complementary records. For this
      // controlled package every available source fits. Larger archives retain
      // explicit coverage; unselected evidence never proves absence.
      const required = resolved.records;
      const extras = initialRecords([...records.values()].filter(r => !resolved.sourceIds.includes(r.id)), query,
        Math.max(0, 22_000 - JSON.stringify(required).length));
      const selected = [...required, ...extras];
      return { records: selected, coverage: { selected: selected.map(r => r.id),
        omitted: [...records.keys()].filter(id => !selected.some(r => r.id === id)),
        instruction: 'Only selected records were inspected. Missing or omitted records do not establish physical absence.' }, resolution: resolved };
    },
    sourceCatalog: [...records.values()].map(r => ({ id: r.id, kind: r.kind,
      label: (r.value as { label?: string }).label || r.id })),
  };
}

export function sourceText(record: ContextRecord) {
  const value = record.value as { excerpt?: string; text?: string };
  return value.excerpt || value.text || '';
}

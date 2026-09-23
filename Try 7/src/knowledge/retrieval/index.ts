import type { EngineSource, SourceSpan } from '@/src/engine/types';
import { words } from '@/src/engine/identity';

const indexCache=new Map<string,{identity:string;index:EvidenceIndex}>();
export function evidenceIndex(trackId:string,sources:EngineSource[]) {
  const identity=sources.map(s=>`${s.id}:${s.revision}:${s.textHash}`).sort().join('|');
  const old=indexCache.get(trackId);
  if(old?.identity===identity)return old.index;
  const index=new EvidenceIndex(sources);
  if(indexCache.size>=4)indexCache.delete(indexCache.keys().next().value!);
  indexCache.set(trackId,{identity,index});return index;
}

/** An index is constructed once per worker step and reused for all lookups there. */
export class EvidenceIndex {
  readonly spans: SourceSpan[];
  readonly byId: Map<string, SourceSpan>;
  private postings = new Map<string, Set<string>>();
  readonly sources: EngineSource[];
  constructor(sources: EngineSource[]) {
    this.sources = sources;
    this.spans = sources.flatMap(s => s.spans);
    this.byId = new Map(this.spans.map(s => [s.id, s]));
    for (const span of this.spans) for (const word of words(`${span.label} ${span.heading} ${span.tableHeader} ${span.text}`)) {
      if (!this.postings.has(word)) this.postings.set(word, new Set());
      this.postings.get(word)!.add(span.id);
    }
  }
  ranked(query: string, required: string[] = []) {
    const scores = new Map<string, number>();
    for (const term of words(query)) {
      const ids = this.postings.get(term);
      if (!ids) continue;
      const weight = 1 + Math.log(1 + this.spans.length / ids.size);
      for (const id of ids) scores.set(id, (scores.get(id) || 0) + weight);
    }
    const forced = new Set(required);
    // Include context neighbors so headers/definitions on adjacent blocks remain discoverable.
    for (const id of required) {
      const pos = this.spans.findIndex(s => s.id === id), span = this.spans[pos];
      for (const i of [pos - 1, pos + 1]) if (span && this.spans[i]?.sourceId === span.sourceId) scores.set(this.spans[i].id, (scores.get(this.spans[i].id) || 0) + 2);
    }
    return this.spans.filter(s => forced.has(s.id) || scores.has(s.id)).sort((a, b) =>
      Number(forced.has(b.id)) - Number(forced.has(a.id)) || (scores.get(b.id) || 0) - (scores.get(a.id) || 0) || a.id.localeCompare(b.id));
  }
}

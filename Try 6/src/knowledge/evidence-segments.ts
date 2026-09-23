import type { DocumentRecord } from '@/src/domain/types';

export interface EvidenceSegment {
  sourceId: string;
  documentId: string;
  label: string;
  scope: string;
  revision: string;
  excerpt: string;
  /** Half-open UTF-16 offsets into the preserved extracted text. */
  start: number;
  end: number;
  documentCharacters: number;
  sourceMarkers: string[];
}

const SOURCE_MARKER = /\bR3-(?:EV|CH|START|DEF)-\d{3}\b/g;
export const EVIDENCE_CHUNK_CHARACTERS = 2_400;

/** Lossless, document-scoped chunks. Retrieval may rank them; ingestion never drops them. */
export function buildEvidenceSegments(documents: DocumentRecord[]): EvidenceSegment[] {
  const segments: EvidenceSegment[] = [];
  for (const document of documents) {
    const text = document.extractedText;
    if (!text.trim()) continue;
    for (let start = 0, part = 1; start < text.length; part += 1) {
      let end = Math.min(text.length, start + EVIDENCE_CHUNK_CHARACTERS);
      if (end < text.length) {
        const paragraph = text.lastIndexOf('\n', end - 1);
        if (paragraph > start + EVIDENCE_CHUNK_CHARACTERS * 0.75) end = paragraph + 1;
        // Never split a UTF-16 surrogate pair.
        else if (/[\uD800-\uDBFF]/.test(text[end - 1])) end -= 1;
      }
      const excerpt = text.slice(start, end);
      segments.push({
        sourceId: `${document.id}#${part}`,
        documentId: document.id,
        label: `${document.title} · section ${part} · characters ${start + 1}–${end}`,
        scope: document.scope,
        revision: document.revision,
        excerpt, start, end, documentCharacters: text.length,
        // Printed markers are metadata, not globally unique citation IDs.
        sourceMarkers: [...new Set([...excerpt.matchAll(SOURCE_MARKER)].map(match => match[0]))],
      });
      start = end;
    }
  }
  return segments;
}

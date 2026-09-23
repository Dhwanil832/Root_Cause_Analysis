import type { DocumentRecord } from '@/src/domain/types';

export interface EvidenceSegment {
  sourceId: string;
  documentId: string;
  label: string;
  scope: string;
  revision: string;
  excerpt: string;
}

const SOURCE_MARKER = /\bR3-(?:EV|CH|START|DEF)-\d{3}\b/g;

function genericChunks(document: DocumentRecord): EvidenceSegment[] {
  const text = document.extractedText.trim();
  if (!text) return [];
  return [{
      sourceId: `${document.id}#1`,
      documentId: document.id,
      label: `${document.title} · representative section`,
      scope: document.scope,
      revision: document.revision,
      excerpt: text.slice(0, 900),
  }];
}

export function buildEvidenceSegments(documents: DocumentRecord[]): EvidenceSegment[] {
  const segments: EvidenceSegment[] = [];
  for (const document of documents) {
    const text = document.extractedText.trim();
    const markers = [...text.matchAll(SOURCE_MARKER)];
    if (!markers.length) {
      segments.push(...genericChunks(document));
      continue;
    }
    for (let index = 0; index < markers.length; index += 1) {
      const marker = markers[index];
      const start = Math.max(0, (marker.index || 0) - 240);
      const end = Math.min(text.length, markers[index + 1]?.index || text.length);
      segments.push({
        sourceId: marker[0],
        documentId: document.id,
        label: `${document.title} · ${marker[0]}`,
        scope: document.scope,
        revision: document.revision,
        excerpt: text.slice(start, Math.min(end, start + 900)),
      });
    }
  }
  const unique = new Map(segments.map((segment) => [`${segment.documentId}:${segment.sourceId}`, segment]));
  return [...unique.values()].slice(0, 32);
}

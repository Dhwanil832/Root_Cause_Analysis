import { env } from 'cloudflare:workers';
import type { DocumentRecord } from '@/src/domain/types';
import type { ModelMedia } from '@/src/providers/types';

function bucket() {
  if (!env.FILES) throw new Error('The R2 binding FILES is unavailable.');
  return env.FILES;
}

function rawBase64(bytes: ArrayBuffer) {
  const values = new Uint8Array(bytes);
  let binary = '';
  for (let offset = 0; offset < values.length; offset += 32_768) {
    binary += String.fromCharCode(...values.subarray(offset, offset + 32_768));
  }
  return btoa(binary);
}

export function needsOriginalModelReading(document: DocumentRecord) {
  if (document.contentType.startsWith('image/')) return true;
  if (document.contentType === 'application/pdf' || document.fileName.toLowerCase().endsWith('.pdf')) {
    return !document.extractedText.trim() || /no machine-readable text/i.test(document.extractionNotes);
  }
  return false;
}

export async function loadDocumentMedia(
  documents: DocumentRecord[],
  alreadyProcessed: Set<string> = new Set(),
  readOriginal: (fileKey: string) => Promise<{ arrayBuffer(): Promise<ArrayBuffer> } | null> = key => bucket().get(key),
): Promise<ModelMedia[]> {
  const media: ModelMedia[] = [];
  for (const document of documents) {
    if (alreadyProcessed.has(document.id) || !needsOriginalModelReading(document)) continue;
    const object = await readOriginal(document.fileKey);
    if (!object) continue;
    const bytes = await object.arrayBuffer();
    media.push({
      documentId: document.id,
      fileName: document.fileName,
      contentType: document.contentType,
      dataBase64: rawBase64(bytes),
      kind: document.contentType.startsWith('image/') ? 'image' : 'file',
    });
  }
  return media;
}

export async function readStoredDocument(fileKey: string) {
  return bucket().get(fileKey);
}

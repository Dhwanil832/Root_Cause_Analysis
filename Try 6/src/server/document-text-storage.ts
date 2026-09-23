import { putJSON, readJSON } from '@/src/engine/tasks/artifacts';

// A larger upload must not merely hit D1's smaller per-row string limit next.
// Reuse the same lossless artifact storage as investigation checkpoints.
const PREFIX = '\u001eRCA_DOCUMENT_TEXT_V1\n';
export async function storeDocumentText(db: D1Database, text: string) {
  return PREFIX + await putJSON(db, text);
}
export async function readDocumentText(db: D1Database, stored: string) {
  return stored.startsWith(PREFIX) ? readJSON<string>(db, stored.slice(PREFIX.length)) : stored;
}

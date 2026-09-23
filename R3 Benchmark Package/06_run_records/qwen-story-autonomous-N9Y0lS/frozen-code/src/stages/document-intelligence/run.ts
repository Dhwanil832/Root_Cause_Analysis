import { documentIntelligenceSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type {
  DocumentIntelligenceRecord,
  DocumentRecord,
  EvidenceClaim,
  ModelDescriptor,
  TagId,
  TraceEntry,
} from '@/src/domain/types';
import type { ModelMedia } from '@/src/providers/types';
import { PROMPT_VERSION } from '@/src/prompts/manifest';
import { needsOriginalModelReading } from '@/src/server/document-media';
import { runAgentStage } from '../run-agent-stage';

function embeddedTextRecord(document: DocumentRecord): DocumentIntelligenceRecord {
  return {
    documentId: document.id,
    title: document.title,
    fileName: document.fileName,
    contentType: document.contentType,
    mode: document.extractedText ? 'embedded-text' : 'unavailable',
    documentType: document.extractedText ? 'machine-readable document' : 'unread document',
    summary: document.extractedText
      ? 'Machine-readable text was extracted and is available to the investigation stages.'
      : 'The original is preserved, but this model track could not read its contents.',
    observations: [],
    limitations: document.extractedText ? [] : [document.extractionNotes || 'No readable content is available.'],
    processedAt: new Date().toISOString(),
    engine: 'deterministic:document-extraction',
    validation: 'fallback',
  };
}

function unavailableRecord(document: DocumentRecord, limitation: string): DocumentIntelligenceRecord {
  return {
    ...embeddedTextRecord(document),
    mode: 'unavailable',
    documentType: document.contentType.startsWith('image/') ? 'image' : 'scanned or visual document',
    summary: 'The original evidence is preserved, but no model interpretation was produced.',
    limitations: [limitation],
    engine: 'harness:capability-router',
    validation: 'failed',
  };
}

function canRead(model: ModelDescriptor, media: ModelMedia) {
  if (model.provider === 'builtin') return false;
  if (media.kind === 'file') return model.provider === 'openai-compatible' && model.apiMode === 'responses';
  if (model.provider === 'ollama') return model.capabilities?.includes('vision') === true;
  return true;
}

export function baselineDocumentIntelligence(
  documents: DocumentRecord[],
  previous: DocumentIntelligenceRecord[] = [],
) {
  const previousByDocument = new Map(previous.map((record) => [record.documentId, record]));
  return documents.map((document) => previousByDocument.get(document.id) || embeddedTextRecord(document));
}

export async function runDocumentIntelligence(
  model: ModelDescriptor,
  incident: string,
  documents: DocumentRecord[],
  mediaInputs: ModelMedia[],
  previous: DocumentIntelligenceRecord[] = [],
) {
  const records = new Map(previous.map((record) => [record.documentId, record]));
  const traces: TraceEntry[] = [];
  const failures: Array<{ documentId: string; error: Error }> = [];
  const mediaByDocument = new Map(mediaInputs.map((media) => [media.documentId, media]));

  for (const document of documents) {
    if (records.has(document.id)) continue;
    if (!needsOriginalModelReading(document)) {
      records.set(document.id, embeddedTextRecord(document));
      continue;
    }
    const media = mediaByDocument.get(document.id);
    if (!media) {
      records.set(document.id, unavailableRecord(document, 'The original exceeded the visual-processing limit or could not be loaded.'));
      continue;
    }
    if (!canRead(model, media)) {
      records.set(document.id, unavailableRecord(document, media.kind === 'file'
        ? 'This provider cannot receive scanned PDF files directly. Use a Responses-compatible vision model or provide page images.'
        : 'The selected model does not report vision capability.'));
      continue;
    }
    try {
      const result = await runAgentStage({
        stage: 'document-intelligence',
        model,
        schema: documentIntelligenceSchema,
        schemaName: 'document_intelligence',
        media: [media],
        packet: {
          originalIncident: incident,
          document: {
            id: document.id,
            scope: document.scope,
            title: document.title,
            fileName: document.fileName,
            contentType: document.contentType,
            revision: document.revision,
            sha256: document.sha256,
            extractionStatus: document.extractionStatus,
            extractionNotes: document.extractionNotes,
            extractedText: document.extractedText.slice(0, 12_000),
          },
        },
      });
      const record: DocumentIntelligenceRecord = {
        documentId: document.id,
        title: document.title,
        fileName: document.fileName,
        contentType: document.contentType,
        mode: media.kind === 'image' ? 'vision' : 'file-vision',
        documentType: result.output.documentType,
        summary: result.output.summary,
        observations: result.output.observations.map((observation) => ({
          ...observation,
          id: stableId('observation', `${document.id}:${observation.kind}:${observation.location}:${observation.text}`),
          documentId: document.id,
          status: 'proposed',
        })),
        limitations: result.output.limitations,
        processedAt: new Date().toISOString(),
        engine: result.trace.engine,
        validation: result.trace.validation,
      };
      records.set(document.id, record);
      traces.push(result.trace);
    } catch (caught) {
      const error = caught instanceof Error ? caught : new Error('Document interpretation failed.');
      failures.push({ documentId: document.id, error });
      records.set(document.id, unavailableRecord(document, error.message));
    }
  }

  return {
    records: documents.map((document) => records.get(document.id) || embeddedTextRecord(document)),
    traces,
    failures,
  };
}

export function documentObservationClaims(records: DocumentIntelligenceRecord[]): EvidenceClaim[] {
  return records.flatMap((record) => record.observations.map((observation): EvidenceClaim => ({
    id: stableId('claim', `document-observation:${observation.id}`),
    text: `${observation.text}${observation.location ? ` [Location: ${observation.location}]` : ''}`,
    kind: observation.kind === 'transcribed-text' || observation.kind === 'document-structure'
      ? 'record'
      : 'direct-observation',
    status: observation.status,
    sourceIds: [record.documentId],
    routedTo: observation.routedTo as TagId[],
  })));
}

export function documentIntelligenceTrace(records: DocumentIntelligenceRecord[]): TraceEntry | null {
  const embedded = records.filter((record) => record.mode === 'embedded-text');
  if (!embedded.length) return null;
  return {
    id: crypto.randomUUID(),
    stage: 'document-intelligence',
    summary: `Made embedded text from ${embedded.length} preserved document(s) available without adding model interpretation.`,
    evidence: embedded.map((record) => record.documentId),
    unknowns: [],
    alternatives: [],
    confidence: 1,
    promptVersion: PROMPT_VERSION,
    engine: 'deterministic:document-extraction',
    durationMs: 0,
    validation: 'valid',
  };
}

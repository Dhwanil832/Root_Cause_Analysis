import { readStoredDocument } from '@/src/server/document-media';
import { readJSON } from '@/src/engine/tasks/artifacts';
import { engineVersions, latestInput, retryFailedTasks, type ResumeOptions } from './engine-repository';
import { queueInvestigation as enqueueRevision } from '@/src/orchestrator/main-router';
import { env } from 'cloudflare:workers';
import type {
  AnalysisSnapshot,
  DocumentRecord,
  DocumentScope,
  IncidentRecord,
  InvestigationAnswer,
  ModelDescriptor,
  AgentId,
  StageCheckpointRecord,
  TrackRecord,
  VersionRecord,
} from '@/src/domain/types';
import { extractDocument, sha256 } from '@/src/knowledge/document-extraction';
import { resolveHostedModel } from '@/src/server/provider-vault';

const MAX_FILE_BYTES = 16 * 1024 * 1024;
const capabilityCache=new Map<string,string[]>();
const BUILTIN_MODEL: ModelDescriptor = {
  id: 'demo-field-analyst',
  name: 'Field Analyst',
  provider: 'builtin',
  detail: 'Built-in deterministic preview',
  available: true,
};

export function database() {
  if (!env.DB) throw new Error('The D1 binding DB is unavailable. Apply the generated migrations before running the app.');
  return env.DB;
}

function filesBucket() {
  if (!env.FILES) throw new Error('The R2 binding FILES is unavailable.');
  return env.FILES;
}

function titleFromDescription(description: string) {
  const first = description.split(/(?<=[.!?])\s+/)[0] || description;
  return first.length > 105 ? `${first.slice(0, 102).trimEnd()}…` : first;
}

export async function modelFromId(id: string): Promise<ModelDescriptor> {
  if (id === BUILTIN_MODEL.id) return BUILTIN_MODEL;
  if (id.startsWith('ollama:')) {
    const name = id.slice(7);
    let capabilities: string[] = [];
    let digest: string | undefined;
    try {
      const response = await fetch((process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434') + '/api/tags', {
        signal: AbortSignal.timeout(1_800), cache: 'no-store',
      });
      if (response.ok) {
        const payload = await response.json() as { models?: Array<{ name: string; digest?: string; capabilities?: string[] }> };
        const installed = payload.models?.find((model) => model.name === name);
        capabilities = installed?.capabilities || [];
        digest = installed?.digest;
        if(digest) {
          if(capabilityCache.has(digest))capabilities=capabilityCache.get(digest)!;
          else {
            const show=await fetch((process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434')+'/api/show',{
              method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({model:name}),signal:AbortSignal.timeout(1800)});
            if(show.ok){capabilities=((await show.json()) as {capabilities?:string[]}).capabilities||[];capabilityCache.set(digest,capabilities);}
          }
        }
      }
    } catch {
      // The provider stage will report availability if Ollama becomes unreachable.
    }
    return { id, name, provider: 'ollama', detail: 'Ollama · local', available: true, capabilities, digest };
  }
  const hosted = await resolveHostedModel(id);
  if (hosted) return hosted;
  return { id, name: id, provider: 'openai-compatible', detail: 'API provider', available: true };
}

interface IncidentRow { id: string; title: string; description: string; created_at: string; updated_at: string }
interface TrackRow { id: string; incident_id: string; model_id: string; model_name: string; provider: string; created_at: string }
interface VersionRow { id: string; track_id: string; number: number; trigger: string; analysis_json: string; created_at: string }
interface StageCheckpointRow {
  id: string;
  track_id: string;
  run_id: string;
  target_version: number;
  sequence: number;
  stage: AgentId;
  status: StageCheckpointRecord['status'];
  payload_json: string;
  created_at: string;
}
interface DocumentRow {
  id: string;
  scope: DocumentScope;
  title: string;
  plant: string;
  incident_id: string | null;
  track_id: string | null;
  question_id: string | null;
  introduced_version: number | null;
  file_key: string;
  file_name: string;
  content_type: string;
  size: number;
  sha256: string;
  revision: string;
  extraction_status: DocumentRecord['extractionStatus'];
  extraction_notes: string;
  extracted_text: string;
  created_at: string;
}

function documentFromRow(row: DocumentRow): DocumentRecord {
  return {
    id: row.id,
    scope: row.scope,
    title: row.title,
    plant: row.plant,
    incidentId: row.incident_id || undefined,
    trackId: row.track_id || undefined,
    questionId: row.question_id || undefined,
    introducedVersion: row.introduced_version || undefined,
    fileKey: row.file_key,
    fileName: row.file_name,
    contentType: row.content_type,
    size: row.size,
    sha256: row.sha256,
    revision: row.revision,
    extractionStatus: row.extraction_status,
    extractionNotes: row.extraction_notes,
    extractedText: row.extracted_text,
    createdAt: row.created_at,
  };
}

async function queryDocuments(sql: string, ...bindings: unknown[]) {
  const result = await database().prepare(sql).bind(...bindings).all<DocumentRow>();
  return result.results.map(documentFromRow);
}

async function attachDocument(trackId: string, document: DocumentRecord, introducedVersion: number) {
  await database().prepare(
    'INSERT OR IGNORE INTO track_documents (id, track_id, document_id, source_scope, introduced_version, created_at) VALUES (?, ?, ?, ?, ?, ?)',
  ).bind(crypto.randomUUID(), trackId, document.id, document.scope, introducedVersion, new Date().toISOString()).run();
}



async function persistFile(
  file: File,
  scope: DocumentScope,
  options: {
    title?: string;
    plant?: string;
    revision?: string;
    incidentId?: string;
    trackId?: string;
    questionId?: string;
    introducedVersion?: number;
  } = {},
): Promise<DocumentRecord> {
  if (file.size > MAX_FILE_BYTES) throw new Error(`${file.name} exceeds the 16 MB file limit.`);
  const id = crypto.randomUUID();
  const bytes = await file.arrayBuffer();
  // PDF extraction may transfer/detach its input buffer. Preserve an independent
  // copy for hashing and R2 storage before handing bytes to any extractor.
  const preservedBytes = bytes.slice(0);
  const digest = await sha256(preservedBytes);
  const cacheKey = digest + ':extract-v2:' + (file.type || '') + ':' + (file.name.split('.').at(-1) || '');
  const savedExtraction = await database().prepare('SELECT result_json FROM extraction_cache WHERE cache_key=?').bind(cacheKey).first<{result_json:string}>();
  const extracted = savedExtraction ? JSON.parse(savedExtraction.result_json) as Awaited<ReturnType<typeof extractDocument>> : await extractDocument(bytes, file.name, file.type || 'application/octet-stream');
  if (!savedExtraction) await database().prepare('INSERT OR IGNORE INTO extraction_cache (cache_key,result_json,created_at) VALUES (?,?,?)').bind(cacheKey, JSON.stringify(extracted), new Date().toISOString()).run();
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '-');
  const owner = options.trackId || options.incidentId || 'library';
  const fileKey = `${scope}/${owner}/${id}-${safeName}`;
  const now = new Date().toISOString();
  await filesBucket().put(fileKey, preservedBytes, {
    httpMetadata: { contentType: file.type || 'application/octet-stream' },
    customMetadata: {
      originalName: file.name,
      scope,
      incidentId: options.incidentId || '',
      trackId: options.trackId || '',
      questionId: options.questionId || '',
    },
  });
  const record: DocumentRecord = {
    id,
    scope,
    title: options.title?.trim() || file.name,
    plant: options.plant?.trim() || 'General',
    incidentId: options.incidentId,
    trackId: options.trackId,
    questionId: options.questionId,
    introducedVersion: options.introducedVersion,
    fileKey,
    fileName: file.name,
    contentType: file.type || 'application/octet-stream',
    size: file.size,
    sha256: digest,
    revision: options.revision?.trim() || '1',
    extractionStatus: extracted.status,
    extractionNotes: extracted.notes,
    extractedText: extracted.text,
    createdAt: now,
  };
  await database().prepare([
    'INSERT INTO documents (id, scope, title, plant, incident_id, track_id, question_id, introduced_version,',
    'file_key, file_name, content_type, size, sha256, revision, extraction_status, extraction_notes, extracted_text, created_at)',
    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  ].join(' ')).bind(
    record.id, record.scope, record.title, record.plant, record.incidentId || null,
    record.trackId || null, record.questionId || null, record.introducedVersion || null,
    record.fileKey, record.fileName, record.contentType, record.size, record.sha256,
    record.revision, record.extractionStatus, record.extractionNotes, record.extractedText, record.createdAt,
  ).run();
  return record;
}

export async function listReferenceDocuments() {
  // Incident-specific reference copies must never leak into the shared library.
  return queryDocuments("SELECT * FROM documents WHERE scope = 'reference' AND incident_id IS NULL AND track_id IS NULL ORDER BY plant, title, created_at DESC");
}

export async function getDocumentContent(id: string) {
  const row = await database().prepare('SELECT * FROM documents WHERE id = ?').bind(id).first<DocumentRow>();
  if (!row) return null;
  const document = documentFromRow(row);
  const body = await readStoredDocument(document.fileKey);
  if (!body) return null;
  return { document, body };
}

export async function addReferenceDocument(file: File, title: string, plant: string, revision: string) {
  return persistFile(file, 'reference', { title, plant, revision });
}

export async function addQuestionDocument(trackId: string, questionId: string, file: File, answer='') {
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<TrackRow>();
  if (!track) return null;
  const currentInput = await latestInput(database(), trackId);
  const latest = currentInput?.row;
  const document = await persistFile(file, 'question', {
    trackId,
    incidentId: track.incident_id,
    questionId,
    introducedVersion: (latest?.number || 0) + 1,
  });
  await attachDocument(trackId, document, document.introducedVersion || 1);
  const incident=await database().prepare('SELECT description FROM incidents WHERE id=?').bind(track.incident_id).first<{description:string}>();
  if(!incident)throw new Error('Incident no longer exists.');
  const revision=await enqueueRevision(database(),trackId,incident.description,await modelFromId(track.model_id),await documentsForTrack(trackId),
    answer.trim()?[{questionId,text:answer.trim(),answeredAt:new Date().toISOString()}]:[]);
  if(document.introducedVersion!==revision.version) {
    document.introducedVersion=revision.version;
    await database().batch([
      database().prepare('UPDATE documents SET introduced_version=? WHERE id=?').bind(revision.version,document.id),
      database().prepare('UPDATE track_documents SET introduced_version=? WHERE track_id=? AND document_id=?').bind(revision.version,trackId,document.id),
    ]);
  }
  return document;
}

export async function createIncident(description: string, modelIds: string[], starterFiles: File[] = [], options: { deferAnalysis?: boolean; title?: string; referenceFiles?: File[] } = {}) {
  const incidentId = crypto.randomUUID();
  const now = new Date().toISOString();
  await database().prepare(
    'INSERT INTO incidents (id, title, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
  ).bind(incidentId, options.title?.trim().slice(0, 150) || titleFromDescription(description), description, now, now).run();

  const starterDocuments: DocumentRecord[] = [];
  for (const file of starterFiles) {
    starterDocuments.push(await persistFile(file, 'starter', { incidentId }));
  }
  const references: DocumentRecord[] = [];
  if(options.referenceFiles !== undefined) {
    for(const file of options.referenceFiles) references.push(await persistFile(file,'reference',{incidentId}));
  } else references.push(...await listReferenceDocuments());

  for (const modelId of modelIds) {
    const model = await modelFromId(modelId);
    const trackId = crypto.randomUUID();
    await database().prepare(
      'INSERT INTO model_tracks (id, incident_id, model_id, model_name, provider, created_at) VALUES (?, ?, ?, ?, ?, ?)',
    ).bind(trackId, incidentId, model.id, model.name, model.provider, now).run();
    const trackDocuments = [...references, ...starterDocuments];
    for (const document of trackDocuments) await attachDocument(trackId, document, 1);
    if (!options.deferAnalysis) await initializeTrack(trackId, true);
  }
  return incidentId;
}

export async function initializeTrack(trackId: string, _strictCausal = true, options:{reviewAfterReading?:boolean}={}) {
  void _strictCausal;
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id=?').bind(trackId).first<TrackRow>();
  if (!track) throw new Error('Track not found.');
  const incident = await database().prepare('SELECT * FROM incidents WHERE id=?').bind(track.incident_id).first<IncidentRow>();
  if (!incident) throw new Error('Incident not found.');
  const result = await enqueueRevision(database(), trackId, incident.description, await modelFromId(track.model_id), await documentsForTrack(trackId), [], { initial: true,...options });
  return { incidentId: incident.id, ...result };
}

async function documentsForTrack(trackId: string) {
  return queryDocuments([
    'SELECT d.* FROM documents d',
    'JOIN track_documents td ON td.document_id = d.id',
    'WHERE td.track_id = ? ORDER BY td.introduced_version, d.created_at, d.id',
  ].join(' '), trackId);
}

export async function getIncident(id: string): Promise<IncidentRecord | null> {
  const incident = await database().prepare('SELECT * FROM incidents WHERE id = ?').bind(id).first<IncidentRow>();
  if (!incident) return null;
  const trackRows = await database().prepare(
    'SELECT * FROM model_tracks WHERE incident_id = ? ORDER BY created_at ASC',
  ).bind(id).all<TrackRow>();
  const tracks: TrackRecord[] = [];
  for (const row of trackRows.results) {
    const versionRows = await database().prepare(
      'SELECT * FROM versions WHERE track_id = ? ORDER BY number ASC',
    ).bind(row.id).all<VersionRow>();
    const checkpointRows = await database().prepare(
      'SELECT * FROM stage_checkpoints WHERE track_id = ? ORDER BY created_at, sequence',
    ).bind(row.id).all<StageCheckpointRow>();
    const activeVersions = await engineVersions(database(), row.id);
    const engineNumbers = new Set(activeVersions.map(v => v.number));
    tracks.push({
      id: row.id,
      modelId: row.model_id,
      modelName: row.model_name,
      provider: row.provider,
      documents: await documentsForTrack(row.id),
      checkpoints: checkpointRows.results.map((checkpoint) => ({
        id: checkpoint.id,
        trackId: checkpoint.track_id,
        runId: checkpoint.run_id,
        targetVersion: checkpoint.target_version,
        sequence: checkpoint.sequence,
        stage: checkpoint.stage,
        status: checkpoint.status,
        payload: JSON.parse(checkpoint.payload_json) as unknown,
        createdAt: checkpoint.created_at,
      })),
      versions: [...versionRows.results.filter(version => !engineNumbers.has(version.number)).map((version): VersionRecord => ({
        id: version.id,
        number: version.number,
        trigger: version.trigger,
        createdAt: version.created_at,
        analysis: JSON.parse(version.analysis_json) as AnalysisSnapshot,
      })), ...activeVersions].sort((a, b) => a.number - b.number),
    });
  }
  return {
    id: incident.id,
    title: incident.title,
    description: incident.description,
    createdAt: incident.created_at,
    updatedAt: incident.updated_at,
    starterDocuments: await queryDocuments(
      "SELECT * FROM documents WHERE incident_id = ? AND scope = 'starter' ORDER BY created_at",
      id,
    ),
    tracks,
  };
}

export async function listHistory() {
  const result = await database().prepare([
    'SELECT i.id, i.title, i.description, i.created_at, i.updated_at,',
    't.id AS track_id, t.model_name, MAX(v.number) AS latest_version',
    'FROM incidents i LEFT JOIN model_tracks t ON t.incident_id = i.id',
    'LEFT JOIN engine_runs v ON v.track_id = t.id',
    'GROUP BY i.id, t.id ORDER BY i.updated_at DESC',
  ].join(' ')).all<Record<string, string | number | null>>();
  const grouped = new Map<string, {
    id: string;
    title: string;
    description: string;
    createdAt: string;
    updatedAt: string;
    models: Array<{ name: string; latestVersion: number }>;
  }>();
  for (const row of result.results) {
    const id = String(row.id);
    if (!grouped.has(id)) {
      grouped.set(id, {
        id,
        title: String(row.title),
        description: String(row.description),
        createdAt: String(row.created_at),
        updatedAt: String(row.updated_at),
        models: [],
      });
    }
    if (row.track_id) grouped.get(id)?.models.push({ name: String(row.model_name), latestVersion: Number(row.latest_version || 0) });
  }
  return [...grouped.values()];
}

export async function addTrackVersion(
  trackId: string,
  questionId: string,
  answerText: string,
  file?: { fileName?: string; fileKey?: string },
) {
  return addTrackAnswers(trackId, [{ questionId, text: answerText,
    sourceId: file?.fileKey || `user-answer:${questionId}`, fileName: file?.fileName,
    fileKey: file?.fileKey, answeredAt: new Date().toISOString() }]);
}

export async function resumeTrack(trackId: string, options: ResumeOptions = {}) {
  const result = await retryFailedTasks(database(), trackId, options);
  if (!result) return initializeTrack(trackId);
  return result;
}

/** One entire answer batch produces exactly one immutable RCA version. */
export async function addTrackAnswers(trackId: string, incoming: InvestigationAnswer[], expectedVersion?: number, storyRoundId?: string, _strictCausal = true) {
  void _strictCausal;
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id=?').bind(trackId).first<TrackRow>();
  if (!track) return null;
  const incident = await database().prepare('SELECT * FROM incidents WHERE id=?').bind(track.incident_id).first<IncidentRow>();
  if (!incident) return null;
  if (!incoming.length || new Set(incoming.map(a => a.questionId)).size !== incoming.length) throw new Error('Provide distinct question IDs.');
  const result = await enqueueRevision(database(), trackId, incident.description, await modelFromId(track.model_id), await documentsForTrack(trackId), incoming, { expectedVersion, storyRoundId });
  await database().prepare('UPDATE incidents SET updated_at=? WHERE id=?').bind(new Date().toISOString(), incident.id).run();
  return { incidentId: incident.id, ...result };
}

export async function addHumanReviewVersion(trackId: string, input: {
  targetType: 'causal-node' | 'causal-branch' | 'corrective-action' | 'document-observation'; targetId: string;
  action: 'accept' | 'reject' | 'close-branch' | 'approve'; notes?: string; actor?: string;
  expectedVersion?:number;
}) {
  const current = await latestInput(database(), trackId);
  if (!current) return null;
  if(!['completed','partial'].includes(current.row.status))throw new Error('Wait for the current revision to finish before reviewing it.');
  if(input.expectedVersion!==undefined&&input.expectedVersion!==current.row.number)throw new Error('This review refers to an older version. Review the latest board.');
  const analysis = await readJSON<AnalysisSnapshot>(database(),current.row.snapshot_json);
  const exists = input.targetType === 'corrective-action' ? analysis.correctiveActions.some(a => a.id === input.targetId)
    : input.targetType === 'document-observation' ? analysis.documentIntelligence.some(d => d.observations.some(o => o.id === input.targetId))
    : analysis.causalBoard.nodes.some(n => n.id === input.targetId);
  if (!exists) throw new Error('Review target is not present in the current revision.');
  const decision = { ...input, id: crypto.randomUUID(), notes: input.notes?.trim() || '', actor: input.actor?.trim() || 'Local investigator', createdAt: new Date().toISOString() };
  const result = await enqueueRevision(database(), trackId, current.input.incident, current.input.model, await documentsForTrack(trackId), [], { humanDecision: decision,expectedVersion:current.row.number });
  const track = await database().prepare('SELECT incident_id FROM model_tracks WHERE id=?').bind(trackId).first<{incident_id:string}>();
  return { incidentId: track?.incident_id, ...result };
}

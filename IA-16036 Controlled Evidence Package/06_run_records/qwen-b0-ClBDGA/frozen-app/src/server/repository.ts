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
import { routeAnalysis } from '@/src/orchestrator/main-router';
import { resolveHostedModel } from '@/src/server/provider-vault';
import { loadDocumentMedia, readStoredDocument } from '@/src/server/document-media';
import { stableId } from '@/src/domain/ids';
import { causalCommitProblems } from '@/src/orchestrator/commit-contract';
import type { AnalysisRequest } from '@/src/orchestrator/main-router';
import { fingerprint, withStageRecovery } from '@/src/orchestrator/stage-recovery';
import type { StageResponse } from '@/src/providers/types';
import { PROMPT_VERSION } from '@/src/prompts/manifest';

const MAX_FILE_BYTES = 16 * 1024 * 1024;
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

function checkpointWriter(trackId: string, runId: string, targetVersion: number) {
  let sequence = 0;
  return async (checkpoint: {
    stage: AgentId;
    status: StageCheckpointRecord['status'];
    payload: unknown;
  }) => {
    sequence += 1;
    await database().prepare([
      'INSERT INTO stage_checkpoints',
      '(id, track_id, run_id, target_version, sequence, stage, status, payload_json, created_at)',
      'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
    ].join(' ')).bind(
      crypto.randomUUID(), trackId, runId, targetVersion, sequence,
      checkpoint.stage, checkpoint.status, JSON.stringify(checkpoint.payload), new Date().toISOString(),
    ).run();
  };
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
  const extracted = await extractDocument(bytes, file.name, file.type || 'application/octet-stream');
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
  return queryDocuments("SELECT * FROM documents WHERE scope = 'reference' ORDER BY plant, title, created_at DESC");
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

export async function addQuestionDocument(trackId: string, questionId: string, file: File) {
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<TrackRow>();
  if (!track) return null;
  const latest = await database().prepare(
    'SELECT number FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1',
  ).bind(trackId).first<{ number: number }>();
  const document = await persistFile(file, 'question', {
    trackId,
    incidentId: track.incident_id,
    questionId,
    introducedVersion: (latest?.number || 0) + 1,
  });
  await attachDocument(trackId, document, document.introducedVersion || 1);
  return document;
}

export async function createIncident(description: string, modelIds: string[], starterFiles: File[] = [], options: { deferAnalysis?: boolean; title?: string } = {}) {
  const incidentId = crypto.randomUUID();
  const now = new Date().toISOString();
  await database().prepare(
    'INSERT INTO incidents (id, title, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
  ).bind(incidentId, options.title?.trim().slice(0, 150) || titleFromDescription(description), description, now, now).run();

  const starterDocuments: DocumentRecord[] = [];
  for (const file of starterFiles) {
    starterDocuments.push(await persistFile(file, 'starter', { incidentId }));
  }
  const references = await listReferenceDocuments();

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

async function runForCommit(trackId: string, targetVersion: number, request: Omit<AnalysisRequest, 'onCheckpoint'>, strict: boolean,
  resumePayload?: { incoming: InvestigationAnswer[]; storyRoundId?: string }) {
  // Providers retry only their failed stage/batch. Never rerun successful stages
  // as a whole-cycle retry with the same evidence and deterministic settings.
  const onCheckpoint = checkpointWriter(trackId, crypto.randomUUID(), targetVersion);
  const saved = await database().prepare(
    "SELECT payload_json FROM stage_checkpoints WHERE track_id = ? AND target_version = ? AND status = 'completed' ORDER BY created_at, sequence",
  ).bind(trackId, targetVersion).all<{ payload_json: string }>();
  const cache = new Map<string, StageResponse<unknown>>();
  for (const row of saved.results) {
    const item = JSON.parse(row.payload_json);
    if (item?.kind === 'model-call' && item.key && item.response) cache.set(item.key, item.response);
  }
  const identity = await fingerprint({
    promptVersion: PROMPT_VERSION, request,
    unresolvedModel: request.model.provider === 'ollama' && !request.model.digest ? crypto.randomUUID() : null,
    contextLength: process.env.OLLAMA_CONTEXT_LENGTH || '32768',
    ollamaBaseUrl: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434',
  });
  await onCheckpoint({ stage: 'revision', status: 'completed', payload: {
    kind: 'pending-investigation', targetVersion, answers: request.answers || [],
    previousVersion: targetVersion - 1, promptVersion: PROMPT_VERSION,
    ...resumePayload,
  } });
  const analysis = await withStageRecovery({
    fingerprint: identity, cache,
    persist: (stage, payload) => onCheckpoint({ stage,
      status: (payload as { kind: string }).kind === 'model-call-failure' ? 'failed' : 'completed', payload }),
  }, () => routeAnalysis({ ...request, onCheckpoint, strictExecution: strict }));
  const problems = strict ? causalCommitProblems(analysis) : [];
  if (problems.length) {
    await onCheckpoint({ stage: 'revision', status: 'failed', payload: {
      reason: 'Commit gate rejected incomplete cycle; no automatic full-cycle replay', problems, uncommittedAnalysis: analysis,
    } });
    throw new Error(`No version committed: ${problems.join('; ')}`);
  }
  return analysis;
}

/** Deferred creation gives the unattended driver durable IDs before inference. */
const activeTrackOperations = new Map<string, Promise<unknown>>();
function trackOperation<T>(trackId: string, work: () => Promise<T>): Promise<T> {
  const active = activeTrackOperations.get(trackId);
  if (active) throw new Error('This model track is already processing. Refresh its progress before resuming.');
  const task = work();
  activeTrackOperations.set(trackId, task);
  return task.finally(() => activeTrackOperations.delete(trackId));
}

export function initializeTrack(trackId: string, strictCausal = true) {
  return trackOperation(trackId, () => initializeTrackUnlocked(trackId, strictCausal));
}

async function initializeTrackUnlocked(trackId: string, strictCausal: boolean) {
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<TrackRow>();
  if (!track) throw new Error('Track not found.');
  const existing = await database().prepare('SELECT number FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1').bind(trackId).first<{number:number}>();
  if (existing) return { incidentId: track.incident_id, version: existing.number };
  const incident = await database().prepare('SELECT * FROM incidents WHERE id = ?').bind(track.incident_id).first<IncidentRow>();
  if (!incident) throw new Error('Incident not found.');
  const documents = await documentsForTrack(trackId);
  const analysis = await runForCommit(trackId, 1, {
    incident: incident.description, model: await modelFromId(track.model_id), documents,
    documentMedia: await loadDocumentMedia(documents),
  }, strictCausal);
  const now = new Date().toISOString();
  await database().batch([
    database().prepare('INSERT INTO versions (id, track_id, number, trigger, analysis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)')
      .bind(crypto.randomUUID(), trackId, 1, `Initial account with ${documents.filter(d => d.scope === 'starter').length} starter document(s)`, JSON.stringify(analysis), now),
    database().prepare('UPDATE incidents SET updated_at = ? WHERE id = ?').bind(now, incident.id),
  ]);
  return { incidentId: incident.id, version: 1 };
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
      versions: versionRows.results.map((version): VersionRecord => ({
        id: version.id,
        number: version.number,
        trigger: version.trigger,
        createdAt: version.created_at,
        analysis: JSON.parse(version.analysis_json) as AnalysisSnapshot,
      })),
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
    'LEFT JOIN versions v ON v.track_id = t.id',
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

const activeResumes = new Map<string, Promise<unknown>>();

/** Recover the saved answer payload; the user does not need to retype it. */
export async function resumeTrack(trackId: string) {
  if (activeResumes.has(trackId)) return activeResumes.get(trackId)!;
  const work = (async () => {
    const latest = await database().prepare('SELECT number FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1')
      .bind(trackId).first<{ number: number }>();
    if (!latest) return initializeTrack(trackId, true);
    const rows = await database().prepare(
      "SELECT payload_json FROM stage_checkpoints WHERE track_id = ? AND target_version = ? AND stage = 'revision' ORDER BY created_at DESC, sequence DESC",
    ).bind(trackId, latest.number + 1).all<{ payload_json: string }>();
    for (const row of rows.results) {
      const pending = JSON.parse(row.payload_json);
      if (pending?.kind === 'pending-investigation') return addTrackAnswers(trackId, pending.incoming || pending.answers, latest.number, pending.storyRoundId, true);
    }
    throw new Error('No interrupted investigation is available to resume.');
  })();
  activeResumes.set(trackId, work);
  try { return await work; } finally { activeResumes.delete(trackId); }
}

/** One entire answer batch produces exactly one immutable RCA version. */
export function addTrackAnswers(
  trackId: string, incoming: InvestigationAnswer[], expectedVersion?: number, storyRoundId?: string, strictCausal = true,
) {
  return trackOperation(trackId, () => addTrackAnswersUnlocked(trackId, incoming, expectedVersion, storyRoundId, strictCausal));
}

async function addTrackAnswersUnlocked(
  trackId: string,
  incoming: InvestigationAnswer[],
  expectedVersion?: number,
  storyRoundId?: string,
  strictCausal = true,
) {
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<TrackRow>();
  if (!track) return null;
  const incident = await database().prepare('SELECT * FROM incidents WHERE id = ?').bind(track.incident_id).first<IncidentRow>();
  const latest = await database().prepare(
    'SELECT * FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1',
  ).bind(trackId).first<VersionRow>();
  if (!incident || !latest) return null;
  if (expectedVersion !== undefined && latest.number !== expectedVersion) {
    throw new Error('The RCA version changed. Generate a new story round from the latest version.');
  }
  const previous = JSON.parse(latest.analysis_json) as AnalysisSnapshot;
  if (!incoming.length || new Set(incoming.map(a => a.questionId)).size !== incoming.length) {
    throw new Error('An answer batch must contain distinct question IDs.');
  }
  const ids = new Set(incoming.map(a => a.questionId));
  const answers: InvestigationAnswer[] = [
    ...previous.answers.filter((answer) => !ids.has(answer.questionId)),
    ...incoming,
  ];
  const documents = await documentsForTrack(trackId);
  const processedDocuments = new Set((previous.documentIntelligence || []).map((record) => record.documentId));
  const documentMedia = await loadDocumentMedia(documents, processedDocuments);
  const analysis = await runForCommit(trackId, latest.number + 1, {
    incident: incident.description,
    model: await modelFromId(track.model_id),
    answers,
    documents,
    previous,
    documentMedia,
  }, strictCausal, { incoming, storyRoundId });
  const now = new Date().toISOString();
  const number = latest.number + 1;
  const statements = [database().prepare(
    'INSERT INTO versions (id, track_id, number, trigger, analysis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)',
  ).bind(crypto.randomUUID(), trackId, number, storyRoundId ? `Story batch ${storyRoundId}: ${incoming.length} answers` : `Evidence added for ${incoming[0].questionId}`, JSON.stringify(analysis), now),
  database().prepare('UPDATE incidents SET updated_at = ? WHERE id = ?').bind(now, incident.id)];
  if (storyRoundId) statements.push(database().prepare(
    "UPDATE story_rounds SET status = 'applied', result_version = ?, updated_at = ? WHERE id = ? AND status = 'applying'",
  ).bind(number, now, storyRoundId));
  // Unique track/version index rejects stale competing writes; D1 batch is atomic.
  await database().batch(statements);
  return { incidentId: incident.id, version: number };
}

export async function addHumanReviewVersion(
  trackId: string,
  input: {
    targetType: 'causal-node' | 'causal-branch' | 'corrective-action' | 'document-observation';
    targetId: string;
    action: 'accept' | 'reject' | 'close-branch' | 'approve';
    notes?: string;
    actor?: string;
  },
) {
  const track = await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<TrackRow>();
  if (!track) return null;
  const incident = await database().prepare('SELECT * FROM incidents WHERE id = ?').bind(track.incident_id).first<IncidentRow>();
  const latest = await database().prepare(
    'SELECT * FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1',
  ).bind(trackId).first<VersionRow>();
  if (!incident || !latest) return null;
  const previous = JSON.parse(latest.analysis_json) as AnalysisSnapshot;
  const analysis = structuredClone(previous);
  const now = new Date().toISOString();

  if (input.targetType === 'document-observation') {
    const observation = (analysis.documentIntelligence || [])
      .flatMap((record) => record.observations)
      .find((item) => item.id === input.targetId);
    if (!observation) throw new Error('Document observation was not found in the latest version.');
    observation.status = input.action === 'accept' || input.action === 'approve' ? 'verified' : 'rejected';
    const claim = analysis.evidenceClaims.find((item) => item.id === stableId('claim', `document-observation:${observation.id}`));
    if (claim) claim.status = observation.status;
  } else if (input.targetType === 'causal-node' || input.targetType === 'causal-branch') {
    const node = analysis.causalBoard.nodes.find((item) => item.id === input.targetId);
    if (!node) throw new Error('Causal node was not found in the latest version.');
    if (input.action === 'accept') {
      node.status = 'verified';
      // Human acceptance is recorded below, independently of model verification.
    } else {
      node.status = 'rejected';
      node.verified = false;
      for (const edge of analysis.causalBoard.edges.filter((item) => item.from === node.id || item.to === node.id)) {
        edge.status = 'rejected';
        edge.verified = false;
      }
    }
  } else {
    const action = analysis.correctiveActions.find((item) => item.id === input.targetId);
    if (!action) throw new Error('Corrective action was not found in the latest version.');
    action.status = input.action === 'approve' || input.action === 'accept' ? 'accepted' : 'proposed';
  }

  analysis.humanDecisions = [
    ...(analysis.humanDecisions || []),
    {
      id: crypto.randomUUID(),
      targetType: input.targetType,
      targetId: input.targetId,
      action: input.action,
      notes: input.notes?.trim() || '',
      actor: input.actor?.trim() || 'Local investigator',
      createdAt: now,
    },
  ];
  analysis.revision = {
    added: [`Human review: ${input.action} ${input.targetType}`],
    changed: [input.targetId], resolved: [], reopened: [],
  };
  if (analysis.causalBoard.nodes.some((node) => node.type === 'root-cause-candidate' && node.status === 'verified')) {
    analysis.status = 'root-causes-accepted';
  }
  const number = latest.number + 1;
  await database().prepare(
    'INSERT INTO versions (id, track_id, number, trigger, analysis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)',
  ).bind(
    crypto.randomUUID(), trackId, number,
    `Human review: ${input.action.replaceAll('-', ' ')}`,
    JSON.stringify(analysis), now,
  ).run();
  await database().prepare('UPDATE incidents SET updated_at = ? WHERE id = ?').bind(now, incident.id).run();
  return { incidentId: incident.id, version: number };
}

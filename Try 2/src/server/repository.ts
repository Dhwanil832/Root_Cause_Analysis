import { env } from 'cloudflare:workers';
import type {
  AnalysisSnapshot, IncidentRecord, InvestigationAnswer, ModelDescriptor,
  TrackRecord, VersionRecord,
} from '@/src/domain/types';
import { routeAnalysis } from '@/src/orchestrator/main-router';

const KNOWN_MODELS: Record<string, ModelDescriptor> = {
  'demo-field-analyst': { id: 'demo-field-analyst', name: 'Field Analyst', provider: 'builtin', detail: 'Built-in deterministic preview', available: true },
  'ollama-qwen3': { id: 'ollama-qwen3', name: 'Qwen 3', provider: 'ollama', detail: 'Ollama · local', available: false },
  'ollama-llama33': { id: 'ollama-llama33', name: 'Llama 3.3', provider: 'ollama', detail: 'Ollama · local', available: false },
};

function db() {
  if (!env.DB) throw new Error('The D1 binding DB is unavailable.');
  return env.DB;
}

export async function ensureSchema() {
  const sql = [
    'CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);',
    'CREATE TABLE IF NOT EXISTS model_tracks (id TEXT PRIMARY KEY, incident_id TEXT NOT NULL, model_id TEXT NOT NULL, model_name TEXT NOT NULL, provider TEXT NOT NULL, created_at TEXT NOT NULL);',
    'CREATE INDEX IF NOT EXISTS model_tracks_incident_idx ON model_tracks(incident_id);',
    'CREATE TABLE IF NOT EXISTS versions (id TEXT PRIMARY KEY, track_id TEXT NOT NULL, number INTEGER NOT NULL, trigger TEXT NOT NULL, analysis_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(track_id, number));',
    'CREATE INDEX IF NOT EXISTS versions_track_idx ON versions(track_id);',
    'CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, track_id TEXT NOT NULL, question_id TEXT NOT NULL, file_key TEXT NOT NULL, file_name TEXT NOT NULL, content_type TEXT NOT NULL, size INTEGER NOT NULL, created_at TEXT NOT NULL);',
  ].join('\n');
  await db().exec(sql);
}

function titleFromDescription(description: string) {
  const first = description.split(/(?<=[.!?])\s+/)[0] || description;
  return first.length > 105 ? first.slice(0, 102).trimEnd() + '…' : first;
}

function modelFromId(id: string): ModelDescriptor {
  if (KNOWN_MODELS[id]) return KNOWN_MODELS[id];
  if (id.startsWith('ollama:')) {
    return { id, name: id.slice(7), provider: 'ollama', detail: 'Ollama · local', available: true };
  }
  return { id, name: id, provider: 'openai-compatible', detail: 'API provider', available: true };
}

export async function createIncident(description: string, modelIds: string[]) {
  await ensureSchema();
  const incidentId = crypto.randomUUID();
  const now = new Date().toISOString();
  await db().prepare(
    'INSERT INTO incidents (id, title, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
  ).bind(incidentId, titleFromDescription(description), description, now, now).run();

  for (const modelId of modelIds) {
    const model = modelFromId(modelId);
    const trackId = crypto.randomUUID();
    const analysis = await routeAnalysis({ incident: description, model });
    await db().prepare(
      'INSERT INTO model_tracks (id, incident_id, model_id, model_name, provider, created_at) VALUES (?, ?, ?, ?, ?, ?)',
    ).bind(trackId, incidentId, model.id, model.name, model.provider, now).run();
    await db().prepare(
      'INSERT INTO versions (id, track_id, number, trigger, analysis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)',
    ).bind(crypto.randomUUID(), trackId, 1, 'Initial incident description', JSON.stringify(analysis), now).run();
  }
  return incidentId;
}

interface IncidentRow { id: string; title: string; description: string; created_at: string; updated_at: string }
interface TrackRow { id: string; incident_id: string; model_id: string; model_name: string; provider: string }
interface VersionRow { id: string; track_id: string; number: number; trigger: string; analysis_json: string; created_at: string }

export async function getIncident(id: string): Promise<IncidentRecord | null> {
  await ensureSchema();
  const incident = await db().prepare('SELECT * FROM incidents WHERE id = ?').bind(id).first<IncidentRow>();
  if (!incident) return null;
  const trackResult = await db().prepare(
    'SELECT * FROM model_tracks WHERE incident_id = ? ORDER BY created_at ASC',
  ).bind(id).all<TrackRow>();
  const tracks: TrackRecord[] = [];
  for (const row of trackResult.results) {
    const versionResult = await db().prepare(
      'SELECT * FROM versions WHERE track_id = ? ORDER BY number ASC',
    ).bind(row.id).all<VersionRow>();
    tracks.push({
      id: row.id,
      modelId: row.model_id,
      modelName: row.model_name,
      provider: row.provider,
      versions: versionResult.results.map((version): VersionRecord => ({
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
    tracks,
  };
}

export async function listHistory() {
  await ensureSchema();
  const sql = [
    'SELECT i.id, i.title, i.description, i.created_at, i.updated_at,',
    't.id AS track_id, t.model_name, MAX(v.number) AS latest_version',
    'FROM incidents i',
    'LEFT JOIN model_tracks t ON t.incident_id = i.id',
    'LEFT JOIN versions v ON v.track_id = t.id',
    'GROUP BY i.id, t.id',
    'ORDER BY i.updated_at DESC',
  ].join(' ');
  const result = await db().prepare(sql).all<Record<string, string | number | null>>();
  const grouped = new Map<string, {
    id: string; title: string; description: string; createdAt: string;
    updatedAt: string; models: Array<{ name: string; latestVersion: number }>;
  }>();
  for (const row of result.results) {
    const id = String(row.id);
    if (!grouped.has(id)) {
      grouped.set(id, {
        id, title: String(row.title), description: String(row.description),
        createdAt: String(row.created_at), updatedAt: String(row.updated_at), models: [],
      });
    }
    if (row.track_id) {
      grouped.get(id)?.models.push({
        name: String(row.model_name),
        latestVersion: Number(row.latest_version || 1),
      });
    }
  }
  return [...grouped.values()];
}

export async function addTrackVersion(
  trackId: string,
  questionId: string,
  answerText: string,
  file?: { fileName?: string; fileKey?: string },
) {
  await ensureSchema();
  const track = await db().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<TrackRow>();
  if (!track) return null;
  const incident = await db().prepare('SELECT * FROM incidents WHERE id = ?').bind(track.incident_id).first<IncidentRow>();
  const latest = await db().prepare(
    'SELECT * FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1',
  ).bind(trackId).first<VersionRow>();
  if (!incident || !latest) return null;
  const previous = JSON.parse(latest.analysis_json) as AnalysisSnapshot;
  const answers: InvestigationAnswer[] = [
    ...previous.answers.filter((answer) => answer.questionId !== questionId),
    {
      questionId, text: answerText, fileName: file?.fileName,
      fileKey: file?.fileKey, answeredAt: new Date().toISOString(),
    },
  ];
  const analysis = await routeAnalysis({
    incident: incident.description,
    model: modelFromId(track.model_id),
    answers,
  });
  const now = new Date().toISOString();
  const number = latest.number + 1;
  await db().prepare(
    'INSERT INTO versions (id, track_id, number, trigger, analysis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)',
  ).bind(crypto.randomUUID(), trackId, number, 'Answer added for ' + questionId, JSON.stringify(analysis), now).run();
  await db().prepare('UPDATE incidents SET updated_at = ? WHERE id = ?').bind(now, incident.id).run();
  return { incidentId: incident.id, version: number };
}

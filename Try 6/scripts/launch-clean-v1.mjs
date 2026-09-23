// Operator-side launch only. No ground truth, manifest, future evidence, prior
// model output, or evaluation instructions enter the model context.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';

const base = 'http://127.0.0.1:3016';
const packageRoot = path.resolve(import.meta.dirname, '../../IA-16036 Controlled Evidence Package/07_case_content_inputs');
const modelId = 'ollama:qwen3.5:latest';
const expectedDigest = '6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7';
const title = 'IA-16036 · Try 6 · Clean B0+B1 · Qwen · V1';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
async function api(route, init) {
  const response = await fetch(base + route, init);
  const value = await response.json();
  if (!response.ok) throw Error(`${route}: ${value.error || response.status}`);
  return value;
}

const manifest = JSON.parse(await fs.readFile(path.join(packageRoot, 'package_manifest.json'), 'utf8'));
const records = await Promise.all(manifest.records.filter(r => ['B0','B1'].includes(r.release)).map(async r => {
  if (!r.path.startsWith('02_model_visible/') && r.path !== '04_challenge_evidence/IA-C01_desk_message.md')
    throw Error('Unexpected model-visible path: ' + r.path);
  const data = await fs.readFile(path.join(packageRoot, r.path));
  if (sha(data) !== r.sha256) throw Error('Prepared input changed: ' + r.id);
  return { ...r, data };
}));
if (records.length !== 11) throw Error('Unexpected B0+B1 inventory.');
const models = (await api('/api/models')).models;
const model = models.find(m => m.id === modelId);
if (model?.digest !== expectedDigest || model.contextWindow !== 262144) throw Error('Model identity/context differs from the agreed run.');
// Refuse duplicates, including an interrupted earlier submission. Inspect its
// saved draft instead of automatically creating a second investigation.
if ((await api('/api/incidents')).incidents.length) throw Error('Try 6 already has an incident; inspect it before launching another.');

const form = new FormData();
form.set('description', records.find(r => r.scope === 'incident_description').data.toString('utf8'));
form.set('title', title); form.set('modelIds', JSON.stringify([modelId]));
form.set('deferAnalysis', 'true');
const formFields = { default_reference: 'referenceFiles', starter_document: 'files', answer_request_document: 'initialEvidenceFiles' };
for (const r of records.filter(r => r.scope !== 'incident_description')) {
  form.append(formFields[r.scope], new File([r.data], path.basename(r.path), { type: 'text/markdown' }));
}
const { id } = await api('/api/incidents', { method: 'POST', body: form });
console.log(JSON.stringify({ phase: 'draft-created', incidentId: id, dashboard: `${base}/incident/${id}` }));
const incident = (await api('/api/incidents/' + id)).incident;
const track = incident.tracks[0];
const scopes = { default_reference: 'reference', starter_document: 'starter', answer_request_document: 'question' };
const expected = records.filter(r => r.scope !== 'incident_description');
if (incident.tracks.length !== 1 || track.versions.length || track.documents.length !== 10 ||
    !expected.every(r => track.documents.some(d => d.sha256 === r.sha256 && d.scope === scopes[r.scope] && !d.questionId && d.extractedText.trim() === r.data.toString('utf8').trim())))
  throw Error(`Draft inputs differ; nothing queued. Inspect ${id}.`);
if ((await api('/api/references')).documents.length) throw Error('Shared library unexpectedly changed; nothing queued.');
const initialized = await api(`/api/tracks/${track.id}/initialize`, { method: 'POST',
  headers: { 'content-type': 'application/json' }, body: JSON.stringify({ reviewAfterReading: false }) });
console.log(JSON.stringify({ phase: 'queued', incidentId: id, trackId: track.id, initialized,
  dashboard: `${base}/incident/${id}`, model: { id: model.id, digest: model.digest, contextWindow: model.contextWindow },
  documents: track.documents.map(d => ({ id: d.id, title: d.title, scope: d.scope, sha256: d.sha256 })),
  storyteller: false, priorOutputsImported: false, withheld: ['B2','B3','ground truth','rubric','answer key'] }, null, 2));

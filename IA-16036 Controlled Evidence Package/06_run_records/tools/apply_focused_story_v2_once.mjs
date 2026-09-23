import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { localHttpOnce } from './local_http_once.mjs';

// Separate RCA job. No storyteller invocation, invented answer, model fallback,
// or automatic replay. The explicit reviewed payload must already exist.
const dir = path.resolve(process.argv[2]);
const manifest = JSON.parse(await fs.readFile(path.join(dir, 'manifest.json')));
const identity = JSON.parse(await fs.readFile(path.join(dir, 'identity.json')));
const story = JSON.parse(await fs.readFile(path.join(dir, 'story-result.json')));
const review = JSON.parse(await fs.readFile(path.join(dir, 'story-review.json')));
const resumePreparation = process.argv[3] === 'resume-preparation';
if (process.argv[3] && !resumePreparation) throw Error('Unknown dispatch mode');
if (resumePreparation) {
  const failure = JSON.parse(await fs.readFile(path.join(dir, 'v2-failure.json')));
  if (failure.error !== 'Error: Incomplete extraction or wrong version: IA-P01') throw Error('Unexpected preparation failure');
  try { await fs.access(path.join(dir, 'v2-dispatch.json')); throw Error('RCA was already dispatched; this is not a preparation resume'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}
const sha = value => createHash('sha256').update(value).digest('hex');
const save = (name, data) => fs.writeFile(path.join(dir, name), JSON.stringify(data, null, 2), { flag: 'wx' });
if (manifest.appUrl !== 'http://127.0.0.1:3008' || manifest.selectedQuestionIds?.length !== 4 ||
  review.decision !== 'release_unedited_for_controlled_test' || review.answersSha256 !== story.answersSha256) throw Error('Expected reviewed focused experiment');
const storyRoute = `/api/tracks/${identity.trackId}/story`;
async function request(route, options = {}) {
  const response = await localHttpOnce(manifest.appUrl + route, options);
  const data = JSON.parse(response.body);
  if (response.status < 200 || response.status >= 300 || data.error) throw Error(data.error || `HTTP ${response.status}`);
  return data;
}
await save(resumePreparation ? 'v2-preparation-resume-launch.json' : 'v2-launch.json', { at: new Date().toISOString(), pid: process.pid, permittedApplyCalls: 1, permittedStoryGenerateCalls: 0, ...identity });
try {
  for (const [file, hash] of Object.entries(manifest.codeHashes)) {
    if (sha(await fs.readFile(path.join(manifest.appDirectory, file))) !== hash) throw Error(`Frozen code changed: ${file}`);
  }
  const models = JSON.parse((await localHttpOnce('http://127.0.0.1:11434/api/tags')).body);
  if (models.models.find(m => m.name === 'qwen3.5:latest')?.digest !== manifest.expectedModelDigest) throw Error('Model digest changed');
  const before = await request(`/api/incidents/${identity.incidentId}`);
  await save(resumePreparation ? 'before-v2-preparation-resume.json' : 'before-v2.json', before);
  const track = before.incident.tracks[0];
  const v1 = JSON.parse(await fs.readFile(path.join(dir, 'version-1.json')));
  if (before.incident.tracks.length !== 1 || track.id !== identity.trackId || track.versions.length !== 1 || track.documents.length !== (resumePreparation ? 7 : 6) ||
    JSON.stringify(track.versions[0]) !== JSON.stringify(v1)) throw Error('Unexpected V1 or evidence state');
  if (track.checkpoints.some(c => c.targetVersion === 2)) throw Error('V2 has already started');
  const workspace = await request(storyRoute);
  const round = workspace.rounds.find(r => r.id === story.roundId);
  if (round?.status !== 'ready' || round.base_version !== 1 ||
    JSON.stringify(round.questions.map(q => q.id)) !== JSON.stringify(manifest.selectedQuestionIds) ||
    sha(JSON.stringify(round.output.output)) !== story.answersSha256) throw Error('Story batch changed');
  const uploads = [];
  const newRecords = manifest.inputs.filter(r => r.release === 'B1');
  if (newRecords.map(r => r.id).join(',') !== 'IA-P01,IA-P02') throw Error('Only the two selected records may be added');
  for (const record of newRecords) {
    const bytes = await fs.readFile(path.join(dir, record.path));
    if (sha(bytes) !== record.sha256) throw Error(`Evidence changed: ${record.id}`);
    let upload;
    if (resumePreparation && record.id === 'IA-P01') {
      const saved = JSON.parse(await fs.readFile(path.join(dir, 'upload-IA-P01.json')));
      const existing = track.documents.find(d => d.id === saved.document.id);
      if (!existing) throw Error('Previously uploaded P01 is missing');
      upload = { document: existing };
    } else {
      const form = new FormData();
      form.set('trackId', identity.trackId);
      // Both documents directly bear on this actual V1 pressure-comparison request.
      form.set('questionId', 'bq-1fanm2w');
      form.set('file', new File([bytes], path.basename(record.path), { type: 'text/markdown' }));
      const encoded = new Request(manifest.appUrl + '/api/uploads', { method: 'POST', body: form });
      upload = await request('/api/uploads', { method: 'POST', headers: Object.fromEntries(encoded.headers), body: Buffer.from(await encoded.arrayBuffer()) });
      await save(`upload-${record.id}.json`, upload);
    }
    // Originals are preserved byte-for-byte; the existing text extractor trims
    // surrounding whitespace. Compare the two distinct representations correctly.
    if (upload.document.sha256 !== record.sha256 || upload.document.extractedText !== bytes.toString('utf8').trim() ||
      upload.document.introducedVersion !== 2 || upload.document.questionId !== 'bq-1fanm2w') throw Error(`Incomplete extraction or wrong version: ${record.id}`);
    uploads.push({ recordId: record.id, documentId: upload.document.id, sha256: record.sha256 });
  }
  const staged = await request(`/api/incidents/${identity.incidentId}`);
  if (staged.incident.tracks[0].documents.length !== 8 || staged.incident.tracks[0].versions.length !== 1) throw Error('Expected eight documents and only V1 before dispatch');
  await save('frozen-v2-input.json', {
    incident: staged.incident.description, modelId: track.modelId, previousVersion: v1,
    documents: staged.incident.tracks[0].documents, storyRoundId: round.id,
    storyOutput: round.output.output,
    note: 'The app renders these unmodified story responses using releasedAnswerText and adds delivery timestamps. Evaluator expectations and story-review are excluded from model input.',
  });
  await save('v2-dispatch.json', { at: new Date().toISOString(), ...identity, storyRoundId: round.id,
    storyAnswers: round.output.output.answers.length, sourceDocuments: 8, newlyReleased: uploads,
    frozenInputSha256: sha(await fs.readFile(path.join(dir, 'frozen-v2-input.json'))), strictCausal: true });
  console.log(JSON.stringify({ event: 'v2-started', at: new Date().toISOString(), storyAnswers: 4, newDocuments: ['IA-P01','IA-P02'], url: identity.url }));
  const applied = await request(storyRoute, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ action: 'apply', roundId: round.id, strictCausal: true }), timeoutMs: 3 * 60 * 60 * 1000 });
  await save('v2-apply-response.json', applied);
  const after = await request(`/api/incidents/${identity.incidentId}`);
  await save('after-v2.json', after);
  const final = after.incident.tracks[0];
  const version = final.versions.find(v => v.number === 2);
  if (final.versions.length !== 2 || !version || JSON.stringify(final.versions[0]) !== JSON.stringify(v1)) throw Error('Expected V2 and unchanged V1');
  if (version.analysis.stageErrors.length) throw Error('V2 contains stage errors');
  await save('version-2.json', version);
  const result = { at: new Date().toISOString(), status: 'completed_stopped_after_v2', url: identity.url,
    storyRoundId: round.id, answers: version.analysis.answers.length,
    nodes: version.analysis.causalBoard.nodes.length, edges: version.analysis.causalBoard.edges.length,
    rejectedEdges: version.analysis.causalBoard.rejectedEdges?.length || 0,
    maturity: version.analysis.causalBoard.maturity, stageErrors: version.analysis.stageErrors,
    performanceReview: 'pending; a committed board is not a passing semantic evaluation' };
  await save('v2-result.json', result);
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  try { await save(resumePreparation ? 'v2-run-failure-snapshot.json' : 'v2-failure-snapshot.json', await request(`/api/incidents/${identity.incidentId}`)); } catch {}
  const failure = { at: new Date().toISOString(), status: 'stopped_no_retry', error: String(error), ...identity };
  await save(resumePreparation ? 'v2-run-failure.json' : 'v2-failure.json', failure);
  console.error(JSON.stringify(failure));
  process.exitCode = 1;
}

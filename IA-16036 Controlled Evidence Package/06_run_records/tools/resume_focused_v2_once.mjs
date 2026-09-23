import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { localHttpOnce } from './local_http_once.mjs';

const dir = path.resolve(process.argv[2]);
const manifest = JSON.parse(await fs.readFile(path.join(dir, 'manifest.json')));
const identity = JSON.parse(await fs.readFile(path.join(dir, 'identity.json')));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
if (manifest.appUrl !== 'http://127.0.0.1:3009') throw Error('Expected isolated V2 resume copy');
const save = (name, data) => fs.writeFile(path.join(dir, name), JSON.stringify(data, null, 2), { flag: 'wx' });
async function request(route, options) {
  const response = await localHttpOnce(manifest.appUrl + route, options);
  const data = JSON.parse(response.body);
  if (response.status < 200 || response.status >= 300 || data.error) throw Error(data.error || `HTTP ${response.status}`);
  return data;
}
await save('resume-launch.json', { at: new Date().toISOString(), pid: process.pid, permittedResumeCalls: 1, ...identity });
try {
  for (const [file, hash] of Object.entries(manifest.codeHashes)) {
    if (sha(await fs.readFile(path.join(manifest.appDirectory, file))) !== hash) throw Error(`Frozen code changed: ${file}`);
  }
  const models = JSON.parse((await localHttpOnce('http://127.0.0.1:11434/api/tags')).body);
  if (models.models.find(m => m.name === 'qwen3.5:latest')?.digest !== manifest.expectedModelDigest) throw Error('Model digest changed');
  const before = await request(`/api/incidents/${identity.incidentId}`);
  await save('before-resume.json', before);
  const track = before.incident.tracks[0];
  const v1 = JSON.parse(await fs.readFile(path.join(dir, 'version-1.json')));
  const savedCalls = track.checkpoints.filter(c => c.targetVersion === 2 && c.payload.kind === 'model-call');
  const pending = track.checkpoints.findLast(c => c.targetVersion === 2 && c.payload.kind === 'pending-investigation');
  if (before.incident.tracks.length !== 1 || track.id !== identity.trackId || track.versions.length !== 1 || track.documents.length !== 8 ||
    JSON.stringify(track.versions[0]) !== JSON.stringify(v1) || savedCalls.length !== 2 || pending?.payload.incoming?.length !== 4) throw Error('Unexpected resume state');
  await save('resume-dispatch.json', { at: new Date().toISOString(), savedCalls: savedCalls.length,
    savedIncomingSha256: sha(JSON.stringify(pending.payload.incoming)), targetVersion: 2, ...identity });
  console.log(JSON.stringify({ event: 'v2-resuming', at: new Date().toISOString(), reusableCalls: savedCalls.length, url: identity.url }));
  await save('resume-response.json', await request(`/api/tracks/${identity.trackId}/resume`, { method: 'POST', timeoutMs: 12 * 60 * 60 * 1000 }));
  const after = await request(`/api/incidents/${identity.incidentId}`);
  await save('after-resume.json', after);
  const final = after.incident.tracks[0];
  const version = final.versions.find(v => v.number === 2);
  if (final.versions.length !== 2 || !version || JSON.stringify(final.versions[0]) !== JSON.stringify(v1)) throw Error('Expected committed V2 and unchanged V1');
  await save('version-2.json', version);
  const workspace = await request(`/api/tracks/${identity.trackId}/story`);
  await save('story-after-resume.json', workspace);
  const round = workspace.rounds.find(r => r.id === pending.payload.storyRoundId);
  if (round?.status !== 'applied' || round.result_version !== 2) throw Error('V2 committed but story round application is inconsistent');
  const added = final.checkpoints.slice(track.checkpoints.length);
  const board = version.analysis.causalBoard;
  const result = { at: new Date().toISOString(), status: 'completed_stopped_after_v2', url: identity.url,
    reusedCalls: added.filter(c => c.payload.kind === 'model-call-reused').length,
    newCalls: added.filter(c => c.payload.kind === 'model-call').length,
    nodes: board.nodes.length, edges: board.edges.length, rejectedEdges: board.rejectedEdges?.length || 0,
    maturity: board.maturity, stageErrors: version.analysis.stageErrors };
  await save('result.json', result); console.log(JSON.stringify(result, null, 2));
} catch (error) {
  try { await save('failure-snapshot.json', await request(`/api/incidents/${identity.incidentId}`)); } catch {}
  const failure = { at: new Date().toISOString(), status: 'stopped_no_retry', error: String(error), ...identity };
  await save('failure.json', failure); console.error(JSON.stringify(failure)); process.exitCode = 1;
}

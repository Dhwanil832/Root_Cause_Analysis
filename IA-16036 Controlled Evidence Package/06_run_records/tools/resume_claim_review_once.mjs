import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { localHttpOnce } from './local_http_once.mjs';

const dir = path.resolve(process.argv[2]);
const manifest = JSON.parse(await fs.readFile(path.join(dir, 'manifest.json')));
const localRejections = manifest.resumeProfile === 'local-rejections';
const verificationPackets = manifest.resumeProfile === 'verification-packets';
if (manifest.appUrl !== (verificationPackets ? 'http://127.0.0.1:3006' : localRejections ? 'http://127.0.0.1:3005' : 'http://127.0.0.1:3004') || !manifest.parentDirectory || manifest.batch !== 'B0') throw Error('Resumed B0 only');
const identity = JSON.parse(await fs.readFile(path.join(dir, 'identity.json')));
identity.url = `${manifest.appUrl}/incident/${identity.incidentId}`;
const save = (name, value) => fs.writeFile(path.join(dir, name), JSON.stringify(value, null, 2), { flag: 'wx' });
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const request = async (route, options) => {
  const response = await localHttpOnce(manifest.appUrl + route, options);
  const data = JSON.parse(response.body);
  if (response.status < 200 || response.status >= 300 || data.error) throw Error(data.error || `HTTP ${response.status}`);
  return data;
};
await save('resume-launch.json', { at: new Date().toISOString(), pid: process.pid, permittedResumeCalls: 1, ...identity });
try {
  for (const [file, hash] of Object.entries(manifest.codeHashes)) {
    if (sha(await fs.readFile(path.join(manifest.appDirectory, file))) !== hash) throw Error(`Frozen code changed: ${file}`);
  }
  const models = await (await fetch('http://127.0.0.1:11434/api/tags')).json();
  if (models.models.find(model => model.name === 'qwen3.5:latest')?.digest !== manifest.expectedModelDigest) throw Error('Model digest changed');
  const before = await request(`/api/incidents/${identity.incidentId}`);
  await save('before-resume.json', before);
  const track = before.incident.tracks[0];
  if (before.incident.tracks.length !== 1 || track.id !== identity.trackId || track.versions.length || track.documents.length !== 6) throw Error('Unexpected resumed state');
  const savedCalls = track.checkpoints.filter(c => c.payload.kind === 'model-call');
  if (savedCalls.length !== (verificationPackets ? 77 : localRejections ? 59 : 38) || !track.checkpoints.some(c => c.stage === (verificationPackets ? 'causal-verification' : localRejections ? 'causal-analysis' : 'claim-review') && c.status === 'failed')) throw Error('Expected failed parent checkpoints');
  await save('resume-dispatch.json', { at: new Date().toISOString(), ...identity, savedModelCalls: savedCalls.length, expectedReusableUpstreamCalls: verificationPackets ? 75 : localRejections ? 57 : 36 });
  console.log(JSON.stringify({ event: 'resuming-once', ...identity, savedModelCalls: savedCalls.length }));
  const result = await request(`/api/tracks/${identity.trackId}/resume`, { method: 'POST', timeoutMs: 3 * 60 * 60 * 1000 });
  await save('resume-response.json', result);
  const after = await request(`/api/incidents/${identity.incidentId}`);
  await save('after-resume.json', after);
  const final = after.incident.tracks[0];
  if (final.versions.length !== 1 || final.versions[0].number !== 1) throw Error('Expected one committed V1');
  const version = final.versions[0];
  await save('version-1.json', version);
  const added = final.checkpoints.slice(track.checkpoints.length);
  await save('result.json', { at: new Date().toISOString(), status: 'completed_stopped_after_v1',
    url: `${manifest.appUrl}/incident/${identity.incidentId}`,
    reusedCalls: added.filter(c => c.payload.kind === 'model-call-reused').length,
    newCalls: added.filter(c => c.payload.kind === 'model-call').length,
    nodes: version.analysis.causalBoard.nodes.length, edges: version.analysis.causalBoard.edges.length,
    rejectedEdges: version.analysis.causalBoard.rejectedEdges?.length || 0,
    maturity: version.analysis.causalBoard.maturity,
    verificationFindings: version.analysis.causalBoard.verificationFindings.length,
    stageErrors: version.analysis.stageErrors });
  console.log(await fs.readFile(path.join(dir, 'result.json'), 'utf8'));
} catch (error) {
  try { await save('failure-snapshot.json', await request(`/api/incidents/${identity.incidentId}`)); } catch {}
  const failure = { at: new Date().toISOString(), status: 'stopped_no_retry', error: String(error), ...identity };
  await save('failure.json', failure); console.error(JSON.stringify(failure)); process.exitCode = 1;
}

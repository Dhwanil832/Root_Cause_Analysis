import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { localHttpOnce } from './local_http_once.mjs';

// Answer preparation only. Deliberately has no apply/RCA callback. Re-execution
// is refused by the exclusive launch record; inspect a failure before retrying.
const dir = path.resolve(process.argv[2]);
const manifest = JSON.parse(await fs.readFile(path.join(dir, 'manifest.json')));
const identity = JSON.parse(await fs.readFile(path.join(dir, 'identity.json')));
const scenario = JSON.parse(await fs.readFile(path.join(dir, 'story-scenario.json')));
if (!['http://127.0.0.1:3007','http://127.0.0.1:3008'].includes(manifest.appUrl) || manifest.batch !== 'B1') throw Error('Isolated B1 workflow copy only');
const sha = value => createHash('sha256').update(value).digest('hex');
const save = (name, data) => fs.writeFile(path.join(dir, name), JSON.stringify(data, null, 2), { flag: 'wx' });
const route = `/api/tracks/${identity.trackId}/story`;
async function request(route, body, timeoutMs = 30000) {
  const response = await localHttpOnce(manifest.appUrl + route, body ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), timeoutMs } : { timeoutMs });
  const data = JSON.parse(response.body);
  if (response.status < 200 || response.status >= 300 || data.error) throw Error(data.error || `HTTP ${response.status}`);
  return data;
}
await save('story-launch.json', { at: new Date().toISOString(), pid: process.pid, ...identity, permittedGenerateCalls: 1, permittedApplyCalls: 0 });
try {
  for (const [name, hash] of Object.entries(manifest.codeHashes)) {
    if (sha(await fs.readFile(path.join(manifest.appDirectory, name))) !== hash) throw Error(`Frozen code changed: ${name}`);
  }
  if (sha(JSON.stringify(scenario)) !== manifest.scenarioSha256) throw Error('Scenario changed');
  const models = JSON.parse((await localHttpOnce('http://127.0.0.1:11434/api/tags')).body);
  if (models.models.find(m => m.name === 'qwen3.5:latest')?.digest !== manifest.expectedModelDigest) throw Error('Model digest changed');
  const before = await request(`/api/incidents/${identity.incidentId}`);
  const track = before.incident.tracks[0];
  if (before.incident.tracks.length !== 1 || track.id !== identity.trackId || track.versions.length !== 1 || track.versions[0].number !== 1 || track.documents.length !== 6) throw Error('Unexpected starting state');
  const v1 = JSON.parse(await fs.readFile(path.join(dir, 'version-1.json')));
  if (JSON.stringify(track.versions[0]) !== JSON.stringify(v1)) throw Error('Copied V1 differs from parent');
  await save('before-story.json', before);
  const workspace = await request(route);
  if (workspace.scenario || workspace.rounds.length || workspace.version !== 1 || !workspace.questions.length) throw Error('Expected a fresh storyteller on committed V1');
  const selectedQuestions = manifest.selectedQuestionIds
    ? manifest.selectedQuestionIds.map(id => { const q=workspace.questions.find(q=>q.id===id); if(!q)throw Error(`Selected question is not pending: ${id}`); return q; })
    : workspace.questions;
  await save('questions-v1.json', selectedQuestions);
  await save('scenario-create-response.json', await request(route, { action: 'create', scenario }));
  await save('story-dispatch.json', { at: new Date().toISOString(), questionCount: selectedQuestions.length, questionsSha256: sha(JSON.stringify(selectedQuestions)), scenarioSha256: manifest.scenarioSha256 });
  console.log(JSON.stringify({ event: 'story-generation-started', at: new Date().toISOString(), questions: selectedQuestions.length, storyUrl: `${manifest.appUrl}/story/${identity.trackId}`, automaticRca: false }));
  const generated = await request(route, { action: 'generate', questionIds: manifest.selectedQuestionIds }, 3 * 60 * 60 * 1000);
  await save('story-generate-response.json', generated);
  const after = await request(route);
  await save('story-after.json', after);
  const round = after.rounds.find(r => r.id === generated.id);
  if (!round || round.status !== 'ready' || after.version !== 1) throw Error('Expected a ready answer batch without a new RCA version');
  await save('candidate-answers.json', round.output.output);
  const counts = {};
  for (const answer of round.output.output.answers) counts[answer.status] = (counts[answer.status] || 0) + 1;
  const summary = { at: new Date().toISOString(), status: 'candidate_batch_ready_for_review', roundId: round.id,
    questionCount: selectedQuestions.length, answerCount: round.output.output.answers.length, answerStatuses: counts,
    answersSha256: sha(JSON.stringify(round.output.output)), durationMs: round.output.durationMs,
    semanticApproval: false, rcaStarted: false, url: `${manifest.appUrl}/story/${identity.trackId}` };
  await save('story-result.json', summary);
  console.log(JSON.stringify(summary, null, 2));
} catch (error) {
  try { await save('story-failure-workspace.json', await request(route)); } catch {}
  const failure = { at: new Date().toISOString(), status: 'stopped_no_retry', error: String(error), rcaStarted: false, ...identity };
  await save('story-failure.json', failure);
  console.error(JSON.stringify(failure));
  process.exitCode = 1;
}

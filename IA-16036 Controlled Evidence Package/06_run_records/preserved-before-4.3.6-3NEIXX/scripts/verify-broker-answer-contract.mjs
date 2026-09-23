// Opt-in stage check: read saved questions, never mutate an app incident.
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { normalizeIntent, stableId } from '../src/domain/ids.ts';
import { runQuestionBroker } from '../src/stages/question-broker/run.ts';
import { PROMPT_VERSION, promptFor } from '../src/prompts/manifest.ts';

if (!process.argv.includes('--live')) throw new Error('Pass --live for the focused local Qwen broker check.');
const records = new URL('../../R3 Benchmark Package/06_run_records/', import.meta.url);
const source = new URL('qwen-story-autonomous-A8rNaX/latest-incident.json', records);
const bytes = await fs.readFile(source);
const hash = value => createHash('sha256').update(value).digest('hex');
const track = JSON.parse(bytes).incident.tracks[0];
const failed = track.checkpoints.find(c => c.stage === 'question-broker' && c.status === 'failed');
const checkpoints = track.checkpoints.filter(c => c.runId === failed.runId);
const failedIds = JSON.parse(failed.payload.providerAttempts[0].raw).decisions.map(d => d.candidateKey);
const baseline = checkpoints.find(c => c.stage === 'incident-understanding').payload.questions.map(q => {
  const intent = normalizeIntent(q.intent);
  return { ...q, intent, id: stableId('bq', intent || q.text), tagId: 'baseline', proposedBy: 'incident-understanding', status: 'answered' };
}).filter(q => failedIds.includes(q.id));
if (baseline.length !== 4 || !baseline.every((q, i) => q.id === failedIds[i])) throw new Error('Failed baseline batch could not be reconstructed.');
// Include a subsequent real specialist batch to exercise legal coverage owners,
// not just the keep-only answered-question alternatives.
const followups = checkpoints.flatMap(c => c.payload?.knowledgeBase ? c.payload.questions : []).slice(0, 4);
if (followups.length !== 4) throw new Error('Expected four saved specialist follow-ups.');
const packet = { structuredIncident: checkpoints.find(c => c.stage === 'incident-structuring').payload };
const dir = await fs.mkdtemp(new URL('qwen-broker-answer-contract-', records));
const save = (name, data) => fs.writeFile(`${dir}/${name}`, JSON.stringify(data, null, 2), { flag: 'wx' });
const model = { id: 'ollama:qwen3.5:latest', name: 'qwen3.5:latest', provider: 'ollama', available: true };
const manifest = { purpose: 'Focused answered-batch and subsequent coverage schema check; not a full RCA run', startedAt: new Date().toISOString(), model: model.id, promptVersion: PROMPT_VERSION, sourceSha256: hash(bytes), failedIds };
await save('manifest.json', manifest);
await save('input.json', { packet, candidates: [...baseline, ...followups], prompt: promptFor('question-broker') });
console.log(JSON.stringify({ directory: dir, ...manifest }));
try {
  const result = await runQuestionBroker(model, packet, [...baseline, ...followups]);
  await save('broker.json', result);
  if (!baseline.every(q => result.questions.some(r => r.id === q.id && r.status === 'answered'))) throw new Error('Existing answer identity was lost.');
  if (hash(await fs.readFile(source)) !== manifest.sourceSha256) throw new Error('Original snapshot changed.');
  const summary = { status: 'passed', completedAt: new Date().toISOString(), batches: result.batches.length, attempts: result.batches.map(b => b.providerAttempts.length), retained: result.questions.length, skipped: result.skipped.length, validation: result.trace.validation, durationMs: result.trace.durationMs, originalSnapshotUnchanged: true, incidentCreated: false };
  await save('result.json', summary);
  console.log(JSON.stringify(summary));
} catch (error) {
  await save('failure.json', { status: 'failed', error: String(error), attempts: error.attempts, brokerBatches: error.brokerBatches, finishedAt: new Date().toISOString() });
  console.error(error); process.exitCode = 1;
}

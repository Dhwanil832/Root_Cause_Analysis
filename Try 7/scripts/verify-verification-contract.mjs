// Focused opt-in replay. Never calls app mutations or commits a causal version.
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { z } from 'zod';
import { stableId } from '../src/domain/ids.ts';
import { runCausalVerification } from '../src/stages/causal-verification/run.ts';
import { verificationSchemaFor } from '../src/stages/causal-verification/output-schema.ts';
import { documentObservationClaims } from '../src/stages/document-intelligence/run.ts';
import { PROMPT_VERSION, promptFor } from '../src/prompts/manifest.ts';

if (!process.argv.includes('--live')) throw new Error('Pass --live for the focused local Qwen verification check.');
const records = new URL('../../R3 Benchmark Package/06_run_records/', import.meta.url);
const parent = new URL('qwen-story-autonomous-CDH6if/', records);
const source = new URL('latest-incident.json', parent);
const bytes = await fs.readFile(source);
const sha = value => createHash('sha256').update(value).digest('hex');
const track = JSON.parse(bytes).incident.tracks[0];
const failure = track.checkpoints.find(c => c.stage === 'causal-verification' && c.status === 'failed');
const checkpoints = track.checkpoints.filter(c => c.runId === failure.runId);
const stage = name => checkpoints.find(c => c.stage === name && c.status === 'completed').payload;
const causal = stage('causal-analysis');
const processed = stage('evidence-processing');
const adjudication = stage('evidence-adjudication');
const claims = new Map();
for (const claim of [...processed.claims, ...stage('answer-fetching').fetchedClaims, ...documentObservationClaims(stage('document-intelligence').records)]) claims.set(claim.id, claim);
const packet = { evidenceClaims: [...claims.values()], conflicts: processed.conflicts, sourceAssessments: adjudication.sourceAssessments, adjudicationConflicts: adjudication.adjudicationConflicts };
const keyToId = new Map(causal.rawModelOutput.nodes.map(n => [n.key, stableId('node', `${n.type}:${n.key}`)]));
const dir = await fs.mkdtemp(new URL('qwen-verification-contract-', records));
const save = (name, data) => fs.writeFile(`${dir}/${name}`, JSON.stringify(data, null, 2), { flag: 'wx' });
const model = { id: 'ollama:qwen3.5:latest', name: 'qwen3.5:latest', provider: 'ollama', available: true };
const manifest = { purpose: 'Focused verification-ID contract check using the saved draft and reconstructed saved first-cycle evidence; not a full RCA run', model: model.id, promptVersion: PROMPT_VERSION, sourceSha256: sha(bytes), startedAt: new Date().toISOString() };
await save('manifest.json', manifest);
await save('input.json', { packet, board: causal.board, keyToId: Object.fromEntries(keyToId), prompt: promptFor('causal-verification'), schema: z.toJSONSchema(verificationSchemaFor(causal.board), { target: 'draft-7' }) });
console.log(JSON.stringify({ directory: dir, ...manifest }));
try {
  const installed = (await (await fetch('http://127.0.0.1:11434/api/tags', { signal: AbortSignal.timeout(10000) })).json()).models.find(m => m.name === model.name);
  const original = JSON.parse(await fs.readFile(new URL('manifest.json', parent))).installedModel;
  if (!installed || installed.digest !== original.digest) throw new Error('Exact original Qwen model digest is unavailable.');
  await save('installed-model.json', installed);
  const result = await runCausalVerification(model, packet, causal.board, keyToId);
  await save('verification.json', result);
  if (sha(await fs.readFile(source)) !== manifest.sourceSha256) throw new Error('Original saved snapshot changed.');
  const summary = { status: 'passed', completedAt: new Date().toISOString(), validation: result.trace.validation, attempts: result.providerAttempts.length, durationMs: result.trace.durationMs, verifiedNodes: result.board.nodes.filter(n => n.verified).length, verifiedEdges: result.board.edges.filter(e => e.verified).length, findings: result.board.verificationFindings.length, questions: result.questions.length, originalSnapshotUnchanged: true, incidentCreated: false };
  await save('result.json', summary);
  console.log(JSON.stringify(summary));
} catch (error) {
  await save('failure.json', { status: 'failed', error: String(error), attempts: error.attempts, finishedAt: new Date().toISOString() });
  console.error(error); process.exitCode = 1;
}

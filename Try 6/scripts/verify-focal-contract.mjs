// Opt-in, local causal-stage replay. Never writes to the app or resumes a run.
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { z } from 'zod';
import { causalAnalysisSchema } from '../src/domain/schemas.ts';
import { runCausalAnalysis } from '../src/stages/causal-analysis/run.ts';
import { runCausalVerification } from '../src/stages/causal-verification/run.ts';
import { documentObservationClaims } from '../src/stages/document-intelligence/run.ts';
import { previousBoardContext } from '../src/stages/causal-analysis/label-contract.ts';
import { causalCommitProblems } from '../src/orchestrator/commit-contract.ts';
import { PROMPT_VERSION, promptFor } from '../src/prompts/manifest.ts';

if (!process.argv.includes('--live')) throw new Error('Pass --live for a focused Qwen causal-analysis and verification check.');
const records = new URL('../../R3 Benchmark Package/06_run_records/', import.meta.url);
const parent = new URL('qwen-story-autonomous-pTsSr7/', records);
const source = new URL('latest-incident.json', parent);
const bytes = await fs.readFile(source);
const sha = value => createHash('sha256').update(value).digest('hex');
const track = JSON.parse(bytes).incident.tracks[0];
const failed = track.checkpoints.find(c => c.stage === 'causal-analysis' && c.status === 'failed');
if (!failed || track.versions.length) throw new Error('Expected the preserved initial causal-analysis failure with no committed versions.');
const checkpoints = track.checkpoints.filter(c => c.runId === failed.runId);
const stage = name => checkpoints.find(c => c.stage === name && c.status === 'completed').payload;
const processed = stage('evidence-processing');
const adjudication = stage('evidence-adjudication');
const fetched = stage('answer-fetching');
// Reconstruct the initial packet using the same merge and enrichment order as
// investigation-loop.ts. No failed graph, hidden truth or new answers are input.
const claims = new Map();
for (const claim of [...processed.claims, ...fetched.fetchedClaims, ...documentObservationClaims(stage('document-intelligence').records)]) claims.set(claim.id, claim);
const knowledgeBases = checkpoints.flatMap(c => c.payload.knowledgeBase ? [structuredClone(c.payload.knowledgeBase)] : []);
for (const kb of knowledgeBases) for (const claim of [...claims.values()].filter(c => c.routedTo.includes(kb.tagId))) {
  if (!kb.findings.some(f => f.id === claim.id)) kb.findings.push({ id: claim.id, statement: claim.text, type: claim.kind === 'inference' ? 'hypothesis' : 'finding', status: claim.status, sourceIds: claim.sourceIds });
}
const fetches = new Map(fetched.answerFetches.map(f => [f.questionId, f]));
const questions = stage('question-broker').questions.map(q => {
  const answer = fetches.get(q.id);
  if (!answer) return q;
  const status = answer.status === 'answered' ? 'answered' : answer.status === 'partial' ? 'partially-answered' : answer.status === 'conflicting' ? 'contradicted' : 'awaiting-user';
  return { ...q, status };
});
const packet = {
  structuredIncident: stage('incident-structuring'), specialistKnowledgeBases: knowledgeBases,
  evidenceClaims: [...claims.values()], conflicts: processed.conflicts,
  sourceAssessments: adjudication.sourceAssessments, adjudicationConflicts: adjudication.adjudicationConflicts,
  questions, previousBoard: previousBoardContext(undefined),
};
const model = { id: 'ollama:qwen3.5:latest', name: 'qwen3.5:latest', provider: 'ollama', available: true };
const dir = await fs.mkdtemp(new URL('qwen-explicit-focal-', records));
const save = (name, data) => fs.writeFile(`${dir}/${name}`, JSON.stringify(data, null, 2), { flag: 'wx' });
const manifest = {
  purpose: 'Focused explicit-focal contract check on reconstructed saved first-cycle evidence; not a four-version investigation or RCA-quality score',
  model: model.id, promptVersion: PROMPT_VERSION, sourceSha256: sha(bytes), sourceCheckpoint: failed.id, startedAt: new Date().toISOString(),
};
await save('manifest.json', manifest);
await save('input.json', { packet, prompt: promptFor('causal-analysis'), schema: z.toJSONSchema(causalAnalysisSchema, { target: 'draft-7' }) });
console.log(JSON.stringify({ directory: dir, ...manifest }));
let activeStage = 'model-check';
try {
  const response = await fetch('http://127.0.0.1:11434/api/tags', { signal: AbortSignal.timeout(10000) });
  if (!response.ok) throw new Error(`Ollama model listing returned ${response.status}.`);
  const installed = (await response.json()).models.find(m => m.name === model.name);
  const original = JSON.parse(await fs.readFile(new URL('manifest.json', parent))).installedModel;
  if (!installed || installed.digest !== original.digest) throw new Error('Exact original Qwen model digest is unavailable; no substitution permitted.');
  await save('installed-model.json', installed);
  activeStage = 'causal-analysis';
  const causal = await runCausalAnalysis(model, packet);
  await save('causal.json', { ...causal, keyToId: Object.fromEntries(causal.keyToId) });
  const causalSummary = { focalNodeId: causal.board.focalNodeId, nodes: causal.board.nodes.length, edges: causal.board.edges.length, attempts: causal.providerAttempts.length, validation: causal.trace.validation, durationMs: causal.trace.durationMs };
  console.log(JSON.stringify({ stage: activeStage, status: 'completed', ...causalSummary }));
  activeStage = 'causal-verification';
  const verificationPacket = { evidenceClaims: packet.evidenceClaims, conflicts: packet.conflicts, sourceAssessments: packet.sourceAssessments, adjudicationConflicts: packet.adjudicationConflicts };
  await save('verification-input.json', { packet: verificationPacket, board: causal.board, prompt: promptFor('causal-verification') });
  const verified = await runCausalVerification(model, verificationPacket, causal.board, causal.keyToId);
  await save('verification.json', verified);
  const problems = causalCommitProblems({ stageErrors: [], trace: [causal.trace, verified.trace], causalBoard: verified.board });
  if (problems.length) throw new Error(problems.join('; '));
  if (sha(await fs.readFile(source)) !== manifest.sourceSha256) throw new Error('Original saved snapshot changed.');
  const summary = {
    status: 'passed', completedAt: new Date().toISOString(), causal: causalSummary,
    verification: { attempts: verified.providerAttempts.length, validation: verified.trace.validation, durationMs: verified.trace.durationMs, verifiedNodes: verified.board.nodes.filter(n => n.verified).length, verifiedEdges: verified.board.edges.filter(e => e.verified).length, findings: verified.board.verificationFindings.length },
    commitContractProblems: problems, originalSnapshotUnchanged: true, incidentCreated: false,
  };
  await save('result.json', summary);
  console.log(JSON.stringify(summary));
} catch (error) {
  await save('failure.json', { status: 'failed', stage: activeStage, error: String(error), attempts: error.attempts, finishedAt: new Date().toISOString() });
  console.error(error); process.exitCode = 1;
}

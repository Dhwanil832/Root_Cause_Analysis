// Opt-in, local stage verification. Never calls app mutation routes or creates versions.
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { runCausalAnalysis } from '../src/stages/causal-analysis/run.ts';
import { runCausalVerification } from '../src/stages/causal-verification/run.ts';
import { runQuestionBroker } from '../src/stages/question-broker/run.ts';
import { causalCommitProblems } from '../src/orchestrator/commit-contract.ts';
import { PROMPT_VERSION, promptFor } from '../src/prompts/manifest.ts';
if (!process.argv.includes('--live')) throw new Error('Pass --live to authorize local Qwen stage calls. No app incident will be created.');
const model = { id: 'ollama:qwen3.5:latest', name: 'qwen3.5:latest', provider: 'ollama', available: true };
const records = new URL('../../R3 Benchmark Package/06_run_records/', import.meta.url);
const source = new URL('qwen-story-autonomous-N9Y0lS/latest-incident.json', records);
const bytes = await fs.readFile(source);
const sha = value => createHash('sha256').update(value).digest('hex');
const saved = JSON.parse(bytes);
const all = saved.incident.tracks[0].checkpoints;
const firstRun = all.find(c => c.stage === 'revision').runId;
const checkpoints = all.filter(c => c.runId === firstRun);
const previous = checkpoints.find(c => c.stage === 'revision').payload.uncommittedAnalysis;
const candidates = [...previous.baselineQuestions, ...checkpoints.flatMap(c => c.payload?.knowledgeBase ? c.payload.questions : [])];
const dir = await fs.mkdtemp(new URL('qwen-stage-recovery-', records));
const save = (name, data) => fs.writeFile(`${dir}/${name}`, JSON.stringify(data, null, 2), { flag: 'wx' });
const summary = { purpose: 'Focused live stage regression; not a four-version investigation or RCA-quality score', model: model.id, promptVersion: PROMPT_VERSION, startedAt: new Date().toISOString(), inputSha256: sha(bytes), candidateCount: candidates.length, status: 'running' };
console.log(JSON.stringify({ directory: dir, ...summary }));
await save('manifest.json', summary);
for (const stage of ['question-broker', 'causal-analysis', 'causal-verification']) await save(`prompt-${stage}.json`, { prompt: promptFor(stage), sha256: sha(promptFor(stage)) });
try {
  const tags = await (await fetch('http://127.0.0.1:11434/api/tags')).json();
  const installed = tags.models.find(m => m.name === 'qwen3.5:latest');
  if (!installed) throw new Error('Exact Qwen model not available; no substitution permitted.');
  await save('installed-model.json', installed);
  console.log('Running question broker on all saved initial candidates.');
  const broker = await runQuestionBroker(model, { structuredIncident: previous.structuredIncident }, candidates);
  await save('broker.json', broker);
  summary.broker = { retained: broker.questions.length, skipped: broker.skipped.length, batches: broker.batches.length, durationMs: broker.trace.durationMs, validation: broker.trace.validation };
  console.log(JSON.stringify({ broker: summary.broker }));
  const packet = {
    structuredIncident: previous.structuredIncident, specialistKnowledgeBases: previous.specialistKnowledgeBases,
    evidenceClaims: previous.evidenceClaims, conflicts: previous.conflicts,
    sourceAssessments: previous.sourceAssessments, adjudicationConflicts: previous.adjudicationConflicts,
    questions: broker.questions, previousBoard: null,
  };
  await save('causal-packet.json', packet);
  console.log('Running causal analysis with reference validation.');
  const causal = await runCausalAnalysis(model, packet);
  await save('causal.json', { ...causal, keyToId: Object.fromEntries(causal.keyToId) });
  summary.causal = { focalNodeId: causal.board.focalNodeId, nodes: causal.board.nodes.length, edges: causal.board.edges.length, validation: causal.trace.validation, durationMs: causal.trace.durationMs };
  console.log(JSON.stringify({ causal: summary.causal }));
  const verified = await runCausalVerification(model, {
    evidenceClaims: packet.evidenceClaims, conflicts: packet.conflicts,
    sourceAssessments: packet.sourceAssessments, adjudicationConflicts: packet.adjudicationConflicts,
  }, causal.board, causal.keyToId);
  await save('verification.json', verified);
  const problems = causalCommitProblems({ stageErrors: [], trace: [broker.trace, causal.trace, verified.trace], causalBoard: verified.board });
  if (problems.length) throw new Error(problems.join('; '));
  if (sha(await fs.readFile(source)) !== summary.inputSha256) throw new Error('Original saved run changed during verification.');
  await save('result.json', { ...summary, status: 'passed', completedAt: new Date().toISOString(), commitContractProblems: problems, incidentCreated: false, historicalSnapshotUnchanged: true });
  console.log(JSON.stringify({ status: 'passed', directory: dir, ...summary.broker, focalNodeId: causal.board.focalNodeId }));
} catch (error) {
  await save('failure.json', { ...summary, status: 'failed', error: String(error), attempts: error.attempts, brokerBatches: error.brokerBatches, finishedAt: new Date().toISOString() });
  console.error(error); process.exitCode = 1;
}

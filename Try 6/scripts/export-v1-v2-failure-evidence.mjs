// Read-only diagnostic export. Does not run inference or modify the application.
// Exports public structured outputs, not private model reasoning or credentials.
import { readFileSync, writeFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = new URL('../', import.meta.url);
const db = new DatabaseSync(fileURLToPath(new URL('.wrangler/state/v3/d1/miniflare-D1DatabaseObject/faaf2b0445ab934c3aac48ddf0cdfade8f9bac050be98993748742cdd2cb05fb.sqlite', root)), { readOnly: true });
function decode(raw) {
  const value = JSON.parse(raw);
  return value?.$artifact ? JSON.parse(db.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').all(value.$artifact).map(row => row.content).join('')) : value;
}
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const countBy = (values, key) => values.reduce((result, value) => { const k = key(value); result[k] = (result[k] || 0) + 1; return result; }, {});
const sourceLabels = (state, ids) => state.sources.filter(source => source.spans.some(span => ids.includes(span.id))).map(source => source.label);
function exportRun(id) {
  const row = db.prepare('SELECT * FROM engine_runs WHERE id=?').get(id);
  const input = decode(row.input_json), encoded = decode(row.state_json), snapshot = decode(row.snapshot_json);
  const state = encoded.$engineState ? Object.fromEntries(Object.entries(encoded.fields).map(([key, value]) => [key, decode(value)])) : encoded;
  const tasks = state.tasks.map(task => ({ id: task.id, kind: task.kind, status: task.status, targetIds: task.targetIds,
    traceId: task.traceId, durationMs: task.durationMs, inputTokens: task.inputTokens, outputTokens: task.outputTokens,
    contextBytes: task.contextBytes, error: task.error, partial: task.partial, engineVersion: task.engineVersion,
    evidenceLabels: sourceLabels(state, task.evidenceIds), omittedEvidenceCount: task.omittedEvidenceIds.length }));
  const calls = db.prepare('SELECT * FROM engine_calls WHERE run_id=? ORDER BY created_at').all(id).map(call => {
    const request = decode(call.request_json), result = decode(call.result_json);
    return { id: call.id, taskId: call.task_id, kind: request.kind, status: call.status, error: call.error,
      createdAt: call.created_at, updatedAt: call.updated_at, elapsedMs: Date.parse(call.updated_at) - Date.parse(call.created_at),
      usage: result.usage, thinkingEnabled: request.thinking, contextWindow: request.context, outputAllowance: request.outputTokens,
      generationPolicy: request.generationPolicy, packetChars: JSON.stringify(request.packet).length,
      notebookCount: request.packet?.notebook?.length, assignedQuestions: request.packet?.assignedQuestions,
      visibleQuestions: request.packet?.questions?.map(q => ({ref: q.ref, text: q.text})),
      selectedEvidence: request.selectedEvidence, omittedEvidence: request.omittedEvidence,
      evidenceCatalog: request.packet?.evidence?.map(e => ({ ref: e.ref, label: e.label })),
      publicOutput: request.kind === 'read' ? undefined : (result.output?.output ?? result.output),
    };
  });
  const stageTiming = {};
  for (const task of tasks) {
    const metric = stageTiming[task.kind] ||= { tasks: 0, durationMs: 0, inputTokens: 0, outputTokens: 0, maxContextBytes: 0 };
    metric.tasks++; metric.durationMs += task.durationMs; metric.inputTokens += task.inputTokens; metric.outputTokens += task.outputTokens;
    metric.maxContextBytes = Math.max(metric.maxContextBytes, task.contextBytes);
  }
  const activeRelationships = state.relationships.filter(edge => edge.proposedBy?.length);
  snapshot.engineProgress.status = row.status;
  snapshot.engineProgress.pauseReason = row.pause_reason || undefined;
  const versionHash = hash({id: row.id, number: row.number, trigger: row.trigger, createdAt: row.created_at, executionStatus: row.status, analysis: snapshot});
  return { id, version: row.number, status: row.status, createdAt: row.created_at, publishedAt: row.updated_at,
    elapsedMs: Date.parse(row.updated_at) - Date.parse(row.created_at), versionHash,
    model: {id: input.model.id, digest: input.model.digest, contextWindow: input.model.contextWindow},
    engineVersion: input.engineVersion, ready: state.investigation.ready,
    counts: {documents: input.documents.length, answers: input.answers.length, findings: state.findings.length,
      nodes: snapshot.causalBoard.nodes.length, edges: snapshot.causalBoard.edges.length,
      verifiedEdges: snapshot.causalBoard.edges.filter(edge => edge.verified).length,
      nodeStatuses: countBy(snapshot.causalBoard.nodes, node => node.status),
      storedEdgeStatuses: countBy(activeRelationships, edge => edge.status),
      displayedEdgeStatuses: countBy(snapshot.causalBoard.edges, edge => edge.status),
      questionsInState: state.questions.length, displayedQuestions: snapshot.questions.length,
      baselineQuestions: snapshot.baselineQuestions.length, quarantine: state.quarantine.length,
      tasks: countBy(tasks, task => `${task.kind}:${task.status}`),
      reviewedClaimStatuses: countBy(state.findings.filter(f => state.tasks.some(t => t.kind === 'review' && t.status === 'completed' && t.targetIds.includes(f.id))), f => f.status),
    }, stageTiming, sources: state.sources, findings: state.findings,
    position: state.investigation, summary: state.summary, board: snapshot.causalBoard,
    activeRelationships, questions: state.questions.map(question => ({...question,
      displayed: [...snapshot.questions, ...snapshot.baselineQuestions].some(shown => shown.id === question.id)})),
    tasks, calls, quarantine: state.quarantine,
  };
}
try {
  const runs = ['a20904da-8710-40df-8d58-fec78f451f2a', '3d44374c-888e-465a-8870-99d11eaa8c12'].map(exportRun);
  const before = JSON.parse(readFileSync(new URL('evals/ia16036-v2-controlled/before.json', root), 'utf8'));
  const round = db.prepare('SELECT * FROM story_rounds WHERE id=?').get('c5bdbc70-37bd-42f3-9acc-00912637f096');
  const jobs = db.prepare('SELECT * FROM story_jobs WHERE round_id=? ORDER BY created_at').all(round.id).map(job => ({id: job.id, questionId: job.question_id,
    status: job.status, attempts: job.attempts, createdAt: job.created_at, updatedAt: job.updated_at, error: job.error}));
  const review = JSON.parse(readFileSync(new URL('evals/ia16036-v2-controlled/story-review.json', root), 'utf8'));
  const output = { exportedAt: new Date().toISOString(), scope: 'Read-only diagnostic evidence; public outputs only.',
    incidentId: '9660f4f2-5fc0-4d0a-917e-8e48641956e3', trackId: 'a6647fe7-b418-4232-817f-b3c6d3a5325d',
    v1Unchanged: runs[0].versionHash === before.v1Sha256, runs,
    story: {roundId: round.id, status: round.status, resultVersion: round.result_version, jobs, review} };
  const destination = new URL('evals/ia16036-v2-controlled/failure-report-evidence.json', root);
  writeFileSync(destination, JSON.stringify(output, null, 2) + '\n');
  console.log(JSON.stringify({file: fileURLToPath(destination), v1Unchanged: output.v1Unchanged,
    runs: runs.map(({id, version, status, createdAt, publishedAt, elapsedMs, counts, stageTiming}) => ({id, version, status, createdAt, publishedAt, elapsedMs, counts, stageTiming}))}, null, 2));
} finally { db.close(); }
